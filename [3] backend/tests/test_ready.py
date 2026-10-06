"""SUU-167: 포트를 먼저 열고 색인은 뒤에서 올린다. 준비 전엔 /health·/ask가 503. Supabase·색인은 전부 가짜."""
import importlib
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.index import Index


@pytest.fixture
def main(monkeypatch):
    import app.main as main
    importlib.reload(main)
    main.STATE["index"] = None
    main.STATE["client"] = None
    monkeypatch.setattr(main, "answer_question", lambda *a, **k: pytest.fail("answer_question must not run before ready"))
    return main


def test_not_ready_gives_503_on_health_and_ask(main):
    c = TestClient(main.app)  # with 없이 → lifespan 안 돎 → 색인 None
    r = c.get("/health")
    assert r.status_code == 503 and r.json() == {"ready": False}
    assert c.post("/ask", json={"question": "solvent welding"}).status_code == 503


class FakeSupabase:
    """lifespan이 쓰는 common_dataset_current 조회만 흉내낸다."""

    def table(self, name):
        assert name == "common_dataset_current"
        return self

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def execute(self):
        return SimpleNamespace(data=[{"release_id": "rel-7"}])


def test_lifespan_opens_port_before_index_is_loaded(main, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://fake")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "fake")
    monkeypatch.setattr("supabase.create_client", lambda url, key: FakeSupabase())
    # SUU-9001: release 고르기는 test_indexed_release.py가 본다. 여기서는 포트·스레드 순서만
    monkeypatch.setattr(main, "indexed_release_id", lambda client: "rel-7")
    gate, loaded = threading.Event(), threading.Event()

    def slow_load_index(client, release_id):
        gate.wait(timeout=5)  # 색인이 느린 척
        loaded.set()
        return Index(release_id, [], lambda q, k: [])

    monkeypatch.setattr(main, "load_index", slow_load_index)

    with TestClient(main.app) as c:  # with → lifespan(startup) 실행
        # 색인이 아직 안 올라왔는데도 요청을 받는다
        assert c.get("/health").status_code == 503
        gate.set()
        assert loaded.wait(timeout=5)
        for _ in range(50):  # 스레드가 STATE에 넣을 때까지 잠깐
            r = c.get("/health")
            if r.status_code == 200:
                break
        assert r.json() == {"release_id": "rel-7"}
        assert main.STATE["client"] is not None
