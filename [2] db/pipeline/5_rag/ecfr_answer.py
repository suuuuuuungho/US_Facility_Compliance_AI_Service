"""Turn the top retrieved sections into an applicability-criteria answer (SUU-147).

The LLM gets the factory's question plus the full text of the top sections and
returns the JSON defined in ``[1] docs/1) project/1_full/1_Project_full.md`` "RAG 답변 품질 개선 과정" 절:
candidate subparts, the criteria that decide applicability (each with citations
to the given sections only) and a checklist for the plant. No verdict.
"""

from __future__ import annotations

import copy
import json
import os
import re
from typing import Any

from ecfr_answer_score import normalize_subpart, score_citation_grounded, score_quote_match
from ecfr_eval import citation_section_key

ANSWER_MODEL = "gpt-5-mini"


def verify_answer(answer: dict, given: list[str], texts: dict[str, str]) -> dict:
    """Move gates failing the scorer's grounding or quote rules to missing."""
    out = copy.deepcopy(answer)
    if not any("gates" in cand for cand in out.get("candidates", [])):
        return out
    for cand in out["candidates"]:
        kept = []
        for gate in cand.get("gates", []):
            single = {"candidates": [{"subpart": cand["subpart"], "gates": [gate]}]}
            _, outside = score_citation_grounded(single, given)
            _, mismatched = score_quote_match(single, texts)
            if outside or mismatched:
                cand.setdefault("missing", []).append(f"{gate['type']}: {gate['question']}")
            else:
                kept.append(gate)
        cand["gates"] = kept
    types = {gate["type"] for cand in out["candidates"] for gate in cand["gates"]}
    out["checklist"] = [item for item in out.get("checklist", []) if item.get("gate") in types]
    return out


def drop_outside_citations(answer: dict, given_section_keys: list[str]) -> tuple[dict, list[str]]:
    """Remove criteria citations that do not belong to the supplied sections."""
    out = copy.deepcopy(answer)
    if any("gates" in cand for cand in out.get("candidates", [])):
        return out, []

    given = set(given_section_keys)
    dropped: list[str] = []
    kept_candidates = []
    for ci, candidate in enumerate(out.get("candidates", [])):
        kept_criteria = []
        for ki, criterion in enumerate(candidate.get("criteria", [])):
            where = f"candidates[{ci}].criteria[{ki}]"
            kept_citations = []
            for citation in criterion.get("citations", []):
                try:
                    key = citation_section_key(str(citation))
                except ValueError:
                    dropped.append(f"citation not a Part 63 section: {citation} at {where}")
                    continue
                if key not in given:
                    dropped.append(f"citation outside given sections: {key} ({citation}) at {where}")
                    continue
                kept_citations.append(citation)
            criterion["citations"] = kept_citations
            if kept_citations:
                kept_criteria.append(criterion)
            else:
                dropped.append(f"criterion dropped (no citation left): {where}")
        candidate["criteria"] = kept_criteria
        if kept_criteria:
            kept_candidates.append(candidate)
        else:
            dropped.append(
                f"candidate dropped (no criterion left): candidates[{ci}] {candidate.get('subpart', '')}"
            )
    out["candidates"] = kept_candidates
    return out, dropped


MAX_COMPLETION_TOKENS = 10000  # gpt-5 계열은 추론 토큰이 출력에 포함된다. 6000이면 102건 중 3건이 빈 답(SUU-147)

ANSWER_SYSTEM = """You are an expert on U.S. EPA air toxics rules (40 CFR Part 63, NESHAP).
A factory describes its situation and asks which rule applies. You get the full text of the most relevant sections.
Build an APPLICABILITY CRITERIA TABLE as JSON with exactly this schema:

{"candidates": [{"subpart": "PPPP", "title": "<subpart name>", "criteria": [{"criterion": "<one sentence>", "citations": ["40 CFR 63.xxxx(a)"]}]}], "checklist": ["<fact the plant must verify>"]}

Rules:
- candidates: list EVERY subpart that could apply to this plant (1 to 4), including the general provisions Subpart A when its sections were given. Only subparts that appear in the given sections.
- subpart: the subpart code only ("A", "M", "PPPP"). Never "Subpart M", never a section number like "40 CFR 63.460".
- criterion: one sentence of the form "if ... then subject" / "if ... then not subject". It is the test, not the result.
- citations: only sections you were given, formatted "40 CFR 63.xxxx" with the paragraph, e.g. "40 CFR 63.4481(a)". At least one per criterion.
- checklist: concrete facts the plant must check about its own operation to apply the criteria.
- Do NOT give a verdict or conclusion on whether the rule applies. The plant decides; you give the criteria and where to look.
- No other fields. Output the JSON only, no prose."""

ANSWER_SYSTEM_GATES = """You are an expert on U.S. EPA air toxics rules (40 CFR Part 63, NESHAP).
A factory describes its situation and asks which rule applies. You get the full text of the most relevant sections.
Build applicability gates as JSON with exactly this schema:

{"candidates": [{"subpart": "PPPP", "title": "<subpart name>", "gates": [{"type": "affected_source", "question": "<one question>", "test": "<yes/no branches>", "citations": ["40 CFR 63.xxxx(a)"], "quote": "<verbatim excerpt>"}], "missing": ["<needed fact absent from given sections>"]}], "checklist": [{"item": "<fact to verify>", "gate": "affected_source"}]}

Rules:
- candidates: list 1 to 4 subparts that appear in the given sections. Include every subpart that could apply, including Subpart A when given.
- subpart: the code only ("A", "M", "PPPP"), never a section number or "Subpart PPPP".
- gates[].type: one of source_category, affected_source, major_or_area, threshold, exemption, compliance_date, in that applicability order (industry, equipment, major/area, threshold, exception, timing).
- gates[].question: one sentence the factory can answer. gates[].test: state which way a yes answer points and which way a no answer points; this is a test, not a result.
- gates[].citations: only given sections, down to the paragraph, e.g. "40 CFR 63.4490(a)".
- gates[].quote: copy 20 to 40 words verbatim from the cited section. Do not paraphrase. If the given text has no supporting excerpt, omit that gate entirely.
- missing: facts needed for the decision but absent from the given sections; use an empty list when there are none.
- checklist[].gate: the gate type for which the checklist item supplies a fact.
- Do NOT give an applies, verdict, or conclusion about this factory. The factory decides.
- No other fields. Output JSON only, no prose."""

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)
_SUBPART_CODE_RE = re.compile(r"[A-Z]{1,7}")
_TOP_KEYS = {"candidates", "checklist"}
_CANDIDATE_KEYS = {"subpart", "title", "criteria"}
_CRITERION_KEYS = {"criterion", "citations"}
_GATE_CANDIDATE_KEYS = {"subpart", "title", "gates", "missing"}
_GATE_KEYS = {"type", "question", "test", "citations", "quote"}
_GATE_CHECKLIST_KEYS = {"item", "gate"}


def build_answer_request(
    question: str, sections: list[dict[str, Any]], *, model: str = ANSWER_MODEL, shape: str = "criteria",
    max_completion_tokens: int = MAX_COMPLETION_TOKENS
) -> dict[str, Any]:
    """Chat-completions request: question + full text of each ``{section_key, subpart, text}``."""
    if shape not in {"criteria", "gates"}:
        raise ValueError(f"unknown answer shape: {shape}")
    parts = [f"QUESTION:\n{question}\n", f"SECTIONS ({len(sections)}):"]
    for i, s in enumerate(sections, 1):
        parts.append(f"\n[{i}] {s['section_key']} (Subpart {s['subpart']})\n{s['text']}")
    return {
        "model": model,
        "max_completion_tokens": max_completion_tokens,
        "messages": [{"role": "system", "content": ANSWER_SYSTEM if shape == "criteria" else ANSWER_SYSTEM_GATES}, {"role": "user", "content": "\n".join(parts)}],
    }


def _nonempty_list(obj: dict, key: str, where: str) -> list:
    value = obj.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{where}: '{key}' must be a non-empty list")
    return value


def _keep(obj: dict, allowed: set[str], where: str, issues: list[str]) -> dict:
    for key in list(obj):
        if key not in allowed:
            issues.append(f"unknown field: {where}.{key}")
    return {k: v for k, v in obj.items() if k in allowed}


def parse_answer(
    text: str, given_section_keys: list[str], *, shape: str = "criteria"
) -> tuple[dict[str, Any], list[str]]:
    """Parse the LLM reply into the answer schema.

    Missing required parts raise ``ValueError``. Unknown fields are dropped and
    noted in ``issues``; citations outside the given sections are kept (the
    groundedness score catches them) but noted too.
    """
    if shape not in {"criteria", "gates"}:
        raise ValueError(f"unknown answer shape: {shape}")
    try:
        raw = json.loads(_FENCE_RE.sub("", text.strip()))
    except json.JSONDecodeError as e:
        raise ValueError(f"answer is not JSON: {e}") from e
    if not isinstance(raw, dict):
        raise ValueError("answer must be a JSON object")
    issues: list[str] = []
    given = set(given_section_keys)

    answer = _keep(raw, _TOP_KEYS, "answer", issues)
    candidates = _nonempty_list(answer, "candidates", "answer")
    checklist = _nonempty_list(answer, "checklist", "answer")
    if shape == "gates":
        answer["checklist"] = []
        for ki, item in enumerate(checklist):
            where = f"checklist[{ki}]"
            if not isinstance(item, dict) or any(
                not isinstance(item.get(key), str) or not item[key].strip()
                for key in _GATE_CHECKLIST_KEYS
            ):
                raise ValueError(f"{where}: 'item' and 'gate' must be non-empty strings")
            answer["checklist"].append(_keep(item, _GATE_CHECKLIST_KEYS, where, issues))
    answer["candidates"] = []
    for ci, cand in enumerate(candidates):
        if not isinstance(cand, dict) or not isinstance(cand.get("subpart"), str):
            raise ValueError(f"candidates[{ci}]: 'subpart' must be a string")
        cand = _keep(cand, _CANDIDATE_KEYS if shape == "criteria" else _GATE_CANDIDATE_KEYS, f"candidates[{ci}]", issues)
        code = normalize_subpart(cand["subpart"])
        if _SUBPART_CODE_RE.fullmatch(code):
            cand["subpart"] = code
        else:
            issues.append(f"candidates[{ci}].subpart is not a code: {cand['subpart']}")
        if shape == "gates":
            gates = _nonempty_list(cand, "gates", f"candidates[{ci}]")
            cand.setdefault("missing", [])
            if not isinstance(cand["missing"], list) or any(not isinstance(x, str) for x in cand["missing"]):
                raise ValueError(f"candidates[{ci}]: 'missing' must be a list of strings")
            cand["gates"] = []
            for gi, gate in enumerate(gates):
                where = f"candidates[{ci}].gates[{gi}]"
                if not isinstance(gate, dict):
                    issues.append(f"{where}: gate must be an object")
                    continue
                missing = next((key for key in ("type", "question", "test", "quote")
                                if not isinstance(gate.get(key), str) or not gate[key].strip()), None)
                if missing is None and (not isinstance(gate.get("citations"), list) or not gate["citations"]):
                    missing = "citations"
                if missing is not None:
                    issues.append(f"{where}: missing '{missing}'")
                    continue
                gate = _keep(gate, _GATE_KEYS, where, issues)
                for citation in gate["citations"]:
                    try:
                        key = citation_section_key(str(citation))
                    except ValueError:
                        issues.append(f"citation not a Part 63 section: {citation}")
                        continue
                    if key not in given:
                        issues.append(f"citation outside given sections: {key} ({citation})")
                cand["gates"].append(gate)
            if not cand["gates"]:
                raise ValueError(f"candidates[{ci}]: no valid gates")
            answer["candidates"].append(cand)
            continue
        criteria = _nonempty_list(cand, "criteria", f"candidates[{ci}]")
        cand["criteria"] = []
        for ki, crit in enumerate(criteria):
            where = f"candidates[{ci}].criteria[{ki}]"
            if not isinstance(crit, dict) or not isinstance(crit.get("criterion"), str):
                raise ValueError(f"{where}: 'criterion' must be a string")
            crit = _keep(crit, _CRITERION_KEYS, where, issues)
            for citation in _nonempty_list(crit, "citations", where):
                try:
                    key = citation_section_key(str(citation))
                except ValueError:
                    issues.append(f"citation not a Part 63 section: {citation}")
                    continue
                if key not in given:
                    issues.append(f"citation outside given sections: {key} ({citation})")
            cand["criteria"].append(crit)
        answer["candidates"].append(cand)
    return answer, issues


def call_openai_chat(request: dict[str, Any], *, client: Any = None) -> dict[str, Any]:
    """Send a chat-completions request built here or by ``ecfr_answer_score``. Returns ``text`` and token counts."""
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(**request)
    return {
        "text": response.choices[0].message.content or "",
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }


__all__ = ["ANSWER_MODEL", "ANSWER_SYSTEM", "ANSWER_SYSTEM_GATES", "MAX_COMPLETION_TOKENS", "build_answer_request", "call_openai_chat", "drop_outside_citations", "parse_answer"]
