"""SUU-158: FastAPI. 켜질 때 색인 한 번(SUU-156), POST /ask → answer_question(SUU-157), GET /health → release_id.
SUU-159: /ask 한 번마다 rag_answer_log 한 줄.
SUU-167: 포트를 먼저 열고 색인은 스레드가 뒤에서 올린다. 준비 전엔 /health·/ask 503.
SUU-161: GET /section/{key} → 메모리 청크를 이어 붙인 조문 전문.
SUU-178: POST /ask/stream → 같은 답을 SSE로. stage(search/found/answer) ×3 → result | error.
SUU-257: POST /letters/similar → 공장 설명과 비슷한 판정서한 상위 5건. 서한 색인은 eCFR 색인 뒤에 따로 올린다."""
from __future__ import annotations

import json
import os
import queue
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, field_validator

from ecfr_answer import call_openai_chat
from ecfr_chunk_index import call_isaacus_rerank_api, call_kanon2_api
from ecfr_eval import _subpart_of_chunk, section_key_of_chunk
from ecfr_llm_rerank import call_openai_rerank_api
from ecfr_search import build_rerank_request

from app.answer import answer_question, section_text
from app.index import indexed_release_id, load_index
from app.letters import LETTER_RELEASE_ID, load_letter_meta, similar_letters
from app.log import answer_log_row, save_answer_log

# 쉼표로 여러 개. 테스트는 이 모듈을 reload 해서 다시 읽는다
ORIGINS = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000").split(",") if o.strip()]
STATE: dict = {"index": None, "client": None, "letters": None, "letter_meta": None}


def _load():
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    release_id = indexed_release_id(client)
    STATE["client"] = client
    STATE["index"] = load_index(client, release_id)  # 마지막에 넣는다. index가 차면 "준비됨"
    # SUU-257: 서한 색인은 /ask 준비를 늦추지 않게 그 뒤에
    STATE["letter_meta"] = load_letter_meta()
    STATE["letters"] = load_index(client, LETTER_RELEASE_ID)


@asynccontextmanager
async def lifespan(app):
    # Render는 포트가 열릴 때까지만 기다린다. 색인은 스레드에 맡기고 바로 연다
    threading.Thread(target=_load, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])


class Ask(BaseModel):
    question: str


@app.post("/ask")
def ask(body: Ask) -> dict:
    if STATE["index"] is None:
        raise HTTPException(503, "index not ready")
    if not body.question.strip():
        raise HTTPException(400, "question is empty")
    result = answer_question(
        body.question,
        index=STATE["index"],
        embed=call_kanon2_api,
        rerank=lambda q, chunks: call_isaacus_rerank_api(build_rerank_request(q, chunks))["scores"],
        llm=call_openai_rerank_api,
        chat=call_openai_chat,
    )
    if STATE.get("client"):  # 테스트(test_main.py)는 client가 없다 → 저장 건너뜀
        save_answer_log(STATE["client"], answer_log_row(body.question, result, STATE["index"].release_id))
    return result


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/ask/stream")
def ask_stream(body: Ask):
    if STATE["index"] is None:
        raise HTTPException(503, "index not ready")
    if not body.question.strip():
        raise HTTPException(400, "question is empty")
    index = STATE["index"]
    q: queue.Queue = queue.Queue()

    # answer_question은 동기라 스레드에서 돌리고, on_event가 큐에 넣은 것을 제너레이터가 흘려보낸다
    def run():
        try:
            result = answer_question(
                body.question,
                index=index,
                embed=call_kanon2_api,
                rerank=lambda q, chunks: call_isaacus_rerank_api(build_rerank_request(q, chunks))["scores"],
                llm=call_openai_rerank_api,
                chat=call_openai_chat,
                on_event=lambda e: q.put(("stage", e)),
            )
            if STATE.get("client"):
                save_answer_log(STATE["client"], answer_log_row(body.question, result, index.release_id))
            q.put(("result", result))
        except Exception as e:  # 헤더는 이미 나갔다. 에러도 이벤트로 보낸다
            q.put(("error", {"detail": str(e)}))
        q.put(None)

    threading.Thread(target=run, daemon=True).start()

    def gen():
        while (item := q.get()) is not None:
            yield _sse(*item)

    return StreamingResponse(gen(), media_type="text/event-stream")


class Describe(BaseModel):
    description: str

    @field_validator("description")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description is empty")  # → 422
        return v


@app.post("/letters/similar")
def letters_similar(body: Describe) -> dict:
    if STATE["letters"] is None:
        raise HTTPException(503, "letter index not ready")
    letters = similar_letters(
        body.description,
        index=STATE["letters"],
        embed=call_kanon2_api,
        rerank=lambda q, chunks: call_isaacus_rerank_api(build_rerank_request(q, chunks))["scores"],
        meta=STATE["letter_meta"],
    )
    return {"letters": letters}


@app.get("/section/{section_key}")
def section(section_key: str) -> dict:
    if STATE["index"] is None:
        raise HTTPException(503, "index not ready")
    index = STATE["index"]
    rows = [c for c in index.chunks if section_key_of_chunk(c) == section_key]  # 5,700개 선형 검색, ms 단위
    if not rows:
        raise HTTPException(404, "section not found")
    return {"section_key": section_key, "subpart": _subpart_of_chunk(rows[0]),
            "text": section_text(index, {"chunk_key": rows[0]["chunk_key"]})}


@app.get("/health")
def health():
    if STATE["index"] is None:
        return JSONResponse({"ready": False}, status_code=503)
    return {"release_id": STATE["index"].release_id}
