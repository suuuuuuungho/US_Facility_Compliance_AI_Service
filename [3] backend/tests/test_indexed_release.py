"""SUU-9001: 서버는 임베딩된 청크가 있는 가장 최근 eCFR release로 색인을 올린다.
매일 수집이 새 release를 공개해도 색인 재생성은 사람이 하므로, 그 사이에는 그 전 release로 계속 답한다.
Supabase는 전부 가짜."""
import importlib
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.index import Index, indexed_release_id


class FakeDB:
    """client.table(name).select(...).eq(col, val).order(col, desc=).limit(n).execute() 흉내.
    execute()는 걸러진 행(data)과 limit 전 개수(count)를 같이 돌려준다."""

    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Query(self.tables.get(name, []))


class _Query:
    def __init__(self, rows):
        self.rows, self._limit = list(rows), None

    def select(self, *_, **__):
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def order(self, col, desc=False):
        self.rows.sort(key=lambda r: r[col], reverse=desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, start, end):
        self.rows = self.rows[start:end + 1]
        return self

    def execute(self):
        data = self.rows if self._limit is None else self.rows[:self._limit]
        return SimpleNamespace(data=data, count=len(self.rows))


def release(release_id, dataset, published_at):
    return {"release_id": release_id, "dataset": dataset, "scope_key": "40/63",
            "status": "published", "published_at": published_at}


def chunks(release_id, n, status="embedded"):
    return [{"chunk_key": f"{release_id}/{i}", "release_id": release_id, "index_status": status} for i in range(n)]


# 순서를 섞어 둔다. 가장 최근 것은 eCFR가 아닌 판정서한(adi) release다
RELEASES = [
    release("ecfr-0916", "ecfr", "2026-09-16T05:42:16+00:00"),
    release("adi-letters", "adi", "2026-09-30T00:00:00+00:00"),
    release("ecfr-0929", "ecfr", "2026-09-29T05:18:26+00:00"),
    release("ecfr-0901", "ecfr", "2026-09-01T00:00:00+00:00"),
]


def db(newest_ecfr_chunks):
    return FakeDB({
        "common_dataset_current": [{"dataset": "ecfr", "release_id": "ecfr-0929"}],
        "common_dataset_release": RELEASES,
        "rag_chunk": newest_ecfr_chunks + chunks("ecfr-0916", 3) + chunks("ecfr-0901", 3) + chunks("adi-letters", 3),
    })


def test_indexed_release_id_skips_newest_release_without_embedded_chunks():
    # 9/29 release는 청크가 없거나, 있어도 아직 임베딩 전이다 → 9/16으로
    assert indexed_release_id(db([])) == "ecfr-0916"
    assert indexed_release_id(db(chunks("ecfr-0929", 2, status="pending"))) == "ecfr-0916"


def test_indexed_release_id_picks_newest_release_when_it_has_embedded_chunks():
    assert indexed_release_id(db(chunks("ecfr-0929", 3))) == "ecfr-0929"


@pytest.fixture
def main():
    import app.main as main
    importlib.reload(main)
    main.STATE["index"] = None
    main.STATE["client"] = None
    return main


def test_health_serves_older_release_when_newest_has_no_embedded_chunks(main, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://fake")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "fake")
    monkeypatch.setattr("supabase.create_client", lambda url, key: db([]))
    monkeypatch.setattr(main, "load_index", lambda client, release_id: Index(release_id, [], lambda q, k: []))

    with TestClient(main.app) as c:  # with → lifespan(startup) → 색인 스레드
        for _ in range(100):
            r = c.get("/health")
            if r.status_code == 200:
                break
            time.sleep(0.05)
        assert r.status_code == 200
        assert r.json() == {"release_id": "ecfr-0916"}
