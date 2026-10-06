"""SUU-156: 서버가 켜질 때 청크(본문) + BM25 검색 함수를 한 번만 메모리에 올린다.
SUU-166: 임베딩(143MB)은 안 내려받는다. 벡터 검색은 Supabase RPC match_rag_chunk(pgvector)가 하고,
Index.vector가 그 결과(chunk_key·score)를 메모리 청크에 붙여 돌려준다.

같은 release_id로 다시 부르면 Supabase를 안 가고 캐시된 Index를 그대로 돌려준다.
fetch_chunks는 [6] rag/eval/run_eval.py의 것을 베낀 것(eval 폴더는 pythonpath에 없다).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ecfr_keyword import build_keyword_search


@dataclass
class Index:
    release_id: str
    chunks: list[dict]
    keyword: Callable[[str, int], list[dict]]
    vector: Callable[[list[float], int], list[dict]] | None = None


_CACHE: dict[str, Index] = {}


def indexed_release_id(client) -> str:
    """Return the newest published eCFR release with embedded chunks."""
    releases = (
        client.table("common_dataset_release")
        .select("release_id")
        .eq("dataset", "ecfr")
        .eq("status", "published")
        .order("published_at", desc=True)
        .execute()
        .data
    )
    for release in releases:
        result = (
            client.table("rag_chunk")
            .select("chunk_key", count="exact")
            .eq("release_id", release["release_id"])
            .eq("index_status", "embedded")
            .limit(1)
            .execute()
        )
        if result.count:
            return release["release_id"]
    raise RuntimeError("no published eCFR release has embedded chunks")


def fetch_chunks(client, release_id: str) -> list[dict]:
    rows, start, page = [], 0, 500
    columns = "chunk_key,node_key,context_text,chunk_text"
    while True:
        r = (client.table("rag_chunk").select(columns)
             .eq("release_id", release_id).eq("index_status", "embedded")
             .order("chunk_key").range(start, start + page - 1).execute())
        rows.extend(r.data)
        if len(r.data) < page:
            break
        start += page
    return rows


def load_index(client, release_id: str) -> Index:
    if release_id not in _CACHE:
        chunks = fetch_chunks(client, release_id)
        by_key = {c["chunk_key"]: c for c in chunks}

        def vector(query_embedding: list[float], k: int) -> list[dict]:
            rows = client.rpc("match_rag_chunk", {"query_embedding": query_embedding, "p_release_id": release_id, "k": k}).execute().data
            return [{**by_key[r["chunk_key"]], "score": r["score"]} for r in rows if r["chunk_key"] in by_key]

        _CACHE[release_id] = Index(release_id, chunks, build_keyword_search(chunks), vector)
    return _CACHE[release_id]
