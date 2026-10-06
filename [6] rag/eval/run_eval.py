"""SUU-81: 평가셋 32건으로 검색 정확도를 잰다 (파이썬 전수 코사인).

사용법 (레포 루트에서):
  python "[6] rag/eval/run_eval.py" --config vector   # 조합: vector / reranker / hybrid → results/<run_id>.jsonl + runs.jsonl 한 줄
  python "[6] rag/eval/run_eval.py" --eval-set v2   # 평가셋: v1 32건(기본) / v2 102건(SUU-120)
  python "[6] rag/eval/run_eval.py" --reranker bge  # 리랭커: kanon(기본, API) / bge / nemotron(로컬 GPU, $0, SUU-131) → run_id 끝에 _bge 등
  python "[6] rag/eval/run_eval.py" --embedder bge --no-context   # 임베더: kanon(기본, rag_chunk 임베딩) / bge(로컬 bge-m3, $0, SUU-133). --no-context면 청크 본문만 → baseline
  python "[6] rag/eval/run_eval.py" --config hybrid --no-rules   # 리랭크 후처리 규칙(SUU-134, 기본 켜짐) 끄기
  python "[6] rag/eval/run_eval.py" --config hybrid --llm gpt-5-mini   # 규칙 뒤 상위 20조문을 OpenAI로 다시 줄 세움(SUU-136) → run_id 끝에 _llm_<model>
  python "[6] rag/eval/run_eval.py" --run-id X      # run_id 직접 지정

규칙: `[1] docs/1) project/1_full/1_Project_full.md` "RAG 검색 품질 개선 과정" 절. 채점표(SUU-117): Hit@5, Hit@20, nDCG@10, Recall@20 (+MRR 비교용). 질문 임베딩은 rag_eval_query_embeddings[_v2].json에 캐시한다.
failure_code/failure_note는 실행 후 Claude가 손으로 채운다.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "[2] db/pipeline/5_rag")]

from ecfr_chunk_index import call_isaacus_rerank_api, call_kanon2_api  # noqa: E402
from ecfr_eval import (  # noqa: E402
    build_query_embedding_request, citation_section_key, gold_ranks, summarize,
)
from ecfr_embed_local import MODELS as LOCAL_EMBEDDERS, chunk_document_text  # noqa: E402
from ecfr_keyword import build_keyword_search  # noqa: E402
from ecfr_llm_rerank import call_openai_rerank_api  # noqa: E402
from ecfr_rerank_local import MODELS as LOCAL_RERANKERS  # noqa: E402
from ecfr_search import build_rerank_request, search_sections  # noqa: E402

HERE = Path(__file__).parent
EVAL_SETS = {
    "v1": (HERE / "rag_eval_case.jsonl", HERE / "rag_eval_query_embeddings.json"),
    "v2": (HERE / "rag_eval_case_v2.jsonl", HERE / "rag_eval_query_embeddings_v2.json"),
}
RUNS = HERE / "runs.jsonl"
RESULTS = HERE / "results"
CACHE = HERE / "cache"  # 로컬 임베딩 캐시(gitignore)
K_MAX = 20
CHUNK_TOP_K = 300  # 조문 20개를 채우기에 넉넉한 청크 수


def load_env():
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def fetch_chunks(client, release_id, *, include_text=False):
    rows, start, page = [], 0, 500
    columns = "chunk_key,node_key,embedding"
    if include_text:
        columns += ",context_text,chunk_text"
    while True:
        r = (client.table("rag_chunk").select(columns)
             .eq("release_id", release_id).eq("index_status", "embedded")
             .order("chunk_key").range(start, start + page - 1).execute())
        rows.extend(r.data)
        print(f"  chunks fetched {len(rows)}", flush=True)
        if len(r.data) < page:
            break
        start += page
    for row in rows:
        if isinstance(row["embedding"], str):
            row["embedding"] = json.loads(row["embedding"])
    return rows


def query_embeddings(cases, cache_path, embed_query=None):
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    latency = {}
    for c in cases:
        if c["case_id"] in cache and cache[c["case_id"]]["question"] == c["question"]:
            continue
        t0 = time.perf_counter()
        emb = embed_query(c["question"]) if embed_query else call_kanon2_api(build_query_embedding_request(c["question"]))
        latency[c["case_id"]] = (time.perf_counter() - t0) * 1000
        cache[c["case_id"]] = {"question": c["question"], "embedding": emb, "embed_ms": latency[c["case_id"]]}
        print(f"  embedded {c['case_id']}", flush=True)
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    return cache


def embed_model_of(embedder):
    return "kanon-2-embedder" if embedder == "kanon" else LOCAL_EMBEDDERS[embedder]


def local_chunk_embeddings(chunks, embedder, with_context, embed):
    """청크 5,625개를 로컬 모델로 임베딩(캐시: cache/chunks_<embedder>_<context|nocontext>.json)."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"chunks_{embedder}_{'context' if with_context else 'nocontext'}.json"
    keys = [c["chunk_key"] for c in chunks]
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached["chunk_keys"] == keys:
            return cached["embeddings"]
    t0 = time.perf_counter()
    vectors = embed([chunk_document_text(c, with_context=with_context) for c in chunks])
    print(f"  embedded {len(vectors)} chunks locally in {time.perf_counter() - t0:.0f}s", flush=True)
    path.write_text(json.dumps({"chunk_keys": keys, "embeddings": vectors}), encoding="utf-8")
    return vectors


def rerank_model(config, reranker):
    if config == "vector":
        return None
    return "kanon-2-reranker" if reranker == "kanon" else LOCAL_RERANKERS[reranker]


def run_id_for(day, config, eval_set, reranker, *, embedder="kanon", with_context=True):
    suffix = f"_{reranker}" if config != "vector" and reranker != "kanon" else ""
    if embedder != "kanon":
        suffix += f"_{embedder}"
    if not with_context:
        suffix += "_nocontext"
    return f"{day}_{config}_{eval_set}{suffix}"


def ranked_all_of(sections):
    """리랭크된 조문 순위 전체를 [section_key, subpart, score]로 (SUU-132 창·규칙 시뮬용)."""
    return [[s["section_key"], s["subpart"], round(s["score"], 4)] for s in sections]


def p(values, q):
    values = sorted(values)
    return round(values[min(len(values) - 1, int(round(q * (len(values) - 1))))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--config", choices=("vector", "reranker", "hybrid"), default="vector")
    ap.add_argument("--eval-set", choices=tuple(EVAL_SETS), default="v1")
    ap.add_argument("--reranker", choices=("kanon", *LOCAL_RERANKERS), default="kanon")
    ap.add_argument("--embedder", choices=("kanon", *LOCAL_EMBEDDERS), default="kanon")
    ap.add_argument("--no-context", action="store_true", help="청크 본문만 임베딩(baseline). --embedder bge 전용")
    ap.add_argument("--no-rules", action="store_true", help="리랭크 후처리 규칙(SUU-134) 끄기")
    ap.add_argument("--llm", help="규칙 뒤 상위 20조문을 이 OpenAI 모델로 다시 줄 세운다(SUU-136). 예: gpt-5-mini")
    args = ap.parse_args()
    if args.no_context and args.embedder == "kanon":
        ap.error("--no-context는 --embedder bge와 같이 쓴다 (rag_chunk 임베딩은 컨텍스트 포함)")
    with_context = not args.no_context
    uses_rerank = args.config in ("hybrid", "reranker")
    rules = uses_rerank and not args.no_rules
    load_env()
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    run_at = datetime.now(timezone.utc)
    run_id = args.run_id or run_id_for(f"{run_at:%Y-%m-%d}", args.config, args.eval_set, args.reranker, embedder=args.embedder, with_context=with_context)
    if args.llm and not args.run_id:
        run_id += f"_llm_{args.llm}"
    cases_path, cache_path = EVAL_SETS[args.eval_set]
    if args.embedder != "kanon":
        cache_path = cache_path.with_name(cache_path.stem + f"_{args.embedder}.json")

    cases = [json.loads(l) for l in cases_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"release {release_id}, cases {len(cases)}, commit {commit}")
    chunks = fetch_chunks(client, release_id, include_text=uses_rerank or args.embedder != "kanon")
    embed_query = None
    if args.embedder != "kanon":
        from ecfr_embed_local import build_local_embedder, load_encoder
        embed = build_local_embedder(load_encoder(args.embedder))
        embed_query = lambda q: embed([q])[0]  # noqa: E731
        for chunk, vector in zip(chunks, local_chunk_embeddings(chunks, args.embedder, with_context, embed)):
            chunk["embedding"] = vector
    cache = query_embeddings(cases, cache_path, embed_query)
    rerank_input_tokens = 0

    def rerank(question, ranked):
        nonlocal rerank_input_tokens
        response = call_isaacus_rerank_api(build_rerank_request(question, ranked))
        rerank_input_tokens += response["input_tokens"]
        return response["scores"]

    if uses_rerank and args.reranker != "kanon":
        from ecfr_rerank_local import BATCH_SIZE, build_local_reranker, load_scorer
        rerank = build_local_reranker(load_scorer(args.reranker), batch_size=BATCH_SIZE[args.reranker])

    keyword = build_keyword_search(chunks) if args.config == "hybrid" else None
    llm_tokens = {"prompt_tokens": 0, "completion_tokens": 0}

    def llm(prompt):
        response = call_openai_rerank_api(prompt, model=args.llm)
        llm_tokens["prompt_tokens"] += response["prompt_tokens"]
        llm_tokens["completion_tokens"] += response["completion_tokens"]
        return response["text"]

    lines = []
    for c in cases:
        t0 = time.perf_counter()
        sections_all = search_sections(
            c["question"],
            embed=lambda request: cache[c["case_id"]]["embedding"],
            chunks=chunks,
            keyword=keyword,
            rerank=rerank if uses_rerank else None,
            top_k=len(chunks),  # 조문 전부. 채점은 아래서 K_MAX로 자른다
            chunk_top_k=150 if uses_rerank else CHUNK_TOP_K,
            rules=rules,
            llm=llm if args.llm else None,
        )
        search_ms = (time.perf_counter() - t0) * 1000
        sections = sections_all[:K_MAX]
        ranks = gold_ranks(c["gold_citations"], sections)
        within = lambda k: [r is not None and r <= k for r in ranks.values()]  # noqa: E731
        first = min((r for r in ranks.values() if r is not None), default=None)
        lines.append({
            "run_id": run_id,
            "case_id": c["case_id"],
            "gold_sections": list(ranks),
            "gold_subparts": c["gold_subparts"],
            "returned_sections": [s["section_key"] for s in sections],
            "returned_chunk_keys": [s["chunk_key"] for s in sections],
            "returned_scores": [round(s["score"], 4) for s in sections],
            "returned_subparts": [s["subpart"] for s in sections],
            "first_gold_rank": first,
            "gold_ranks": ranks,
            "hit_loose_5": any(within(5)), "hit_strict_5": all(within(5)), "recall_5": sum(within(5)) / len(ranks),
            "hit_loose_20": any(within(20)), "hit_strict_20": all(within(20)), "recall_20": sum(within(20)) / len(ranks),
            "subpart_hit_primary_5": c["gold_subparts"][0] in [s["subpart"] for s in sections[:5]],
            "latency_ms": {"embed": round(cache[c["case_id"]]["embed_ms"]), "search": round(search_ms)},
            "failure_code": None,
            "failure_note": None,
            "ranked_all": ranked_all_of(sections_all),
        })

    metrics = summarize(lines, k_max=K_MAX)
    embed_ms = [l["latency_ms"]["embed"] for l in lines]
    search_ms = [l["latency_ms"]["search"] for l in lines]
    run = {
        "run_id": run_id,
        "run_at": run_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": args.config,
        "eval_set_version": args.eval_set,
        "n_cases": len(lines),
        "release_id": release_id,
        "embed_model": embed_model_of(args.embedder),
        "with_context": with_context,
        "rerank_model": rerank_model(args.config, args.reranker),
        "rules": rules,
        "llm_model": args.llm,
        "llm_tokens": llm_tokens if args.llm else None,
        "contextualizer_model": "gpt-4o-mini",
        "context_prompt_version": "ctx_prompt_v1",
        "chunk_rule_commit": commit,
        "k_max": K_MAX,
        "metrics": metrics,
        "latency_ms": {"embed_p50": p(embed_ms, 0.5), "embed_p95": p(embed_ms, 0.95),
                       "search_p50": p(search_ms, 0.5), "search_p95": p(search_ms, 0.95)},
        "cost_usd": (
            {"per_query": rerank_input_tokens * 0.35 / 1e6 / len(cases),
             "total": rerank_input_tokens * 0.35 / 1e6}
            if uses_rerank and args.reranker == "kanon"
            else {"per_query": 0.0, "total": 0.0} if uses_rerank
            else {"per_query": None, "total": None}
        ),
        "failure_counts": {f"F{i}": 0 for i in range(1, 8)},
        "notes": f"index coverage {len(chunks)} embedded chunks ({'local ' + embed_model_of(args.embedder) + (' no-context' if not with_context else '') + ' embeddings, ' if args.embedder != 'kanon' else ''}python full-scan cosine"
                 f"{' + BM25 RRF' if args.config == 'hybrid' else ''}"
                 f"{' + ' + rerank_model(args.config, args.reranker) + ' rerank' if uses_rerank else ''}"
                 f"{' + ' + args.llm + ' llm rerank' if args.llm else ''}, not HNSW)",
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{run_id}.jsonl").write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lines), encoding="utf-8")
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(run, ensure_ascii=False) + "\n")
    print(json.dumps(metrics, indent=1))
    print(f"scoreboard: Hit@5 {metrics['hit_loose']['5']:.3f}  Hit@20 {metrics['hit_loose']['20']:.3f}  "
          f"nDCG@10 {metrics['ndcg']['10']:.3f}  Recall@20 {metrics['recall']['20']:.3f}  (MRR {metrics['mrr_20']:.3f})")
    print("misses@20:", [l["case_id"] for l in lines if not l["hit_loose_20"]])


if __name__ == "__main__":
    main()
