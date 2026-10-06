"""SUU-295: 문서가 실제 자동 갱신(SUU-293·294·298·299·303)과 맞는지 검사한다.

실제 일정은 `.github/workflows/db-refresh.yml`(eCFR·FR 매일 03:17 UTC)과
`echo-refresh.yml`(ECHO 매주 화요일 05:17 UTC)이다. EPA는 ECHO를 일요일에 올린다 → 이틀 뒤.
"""
from pathlib import Path

DOCS = Path(__file__).parents[2] / "[1] docs"
FULL = DOCS / "1) project" / "1_full" / "1_Project_full.md"
SPEC = DOCS / "2) db" / "0_Data Specification_v1.md"


def _row(text: str, first_cell: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(f"| {first_cell} |"))


def test_spec_cadence_is_daily_weekly_not_manual():
    spec = SPEC.read_text(encoding="utf-8")
    collection = spec.split("### Collection", 1)[1].split("\n### ", 1)[0]

    assert "매일" in _row(collection, "eCFR")
    assert "매일" in _row(collection, "FR")
    assert "매주" in _row(collection, "ECHO")
    assert "수동" in _row(collection, "ADI + CAA")  # ADI 는 자동화 범위 밖
    for old in ("cron) **없음**", "사람이 돌림", "자동 갱신 없음"):
        assert old not in spec, old


def test_full_says_when_changed_rules_are_fetched_again():
    line = next(l for l in FULL.read_text(encoding="utf-8").splitlines() if "원문을 다시 받아" in l)

    assert "매일" in line, line


def test_full_echo_schedule_is_tuesday_not_next_day():
    full = FULL.read_text(encoding="utf-8")

    assert "정부 갱신 다음 날" not in full
    assert "화요일" in _row(full, "공장 점검·위반·벌금 기록")
