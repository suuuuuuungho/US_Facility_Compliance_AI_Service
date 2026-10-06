# Data Specification v1 (US Factory Compliance Data Card)

> 실제로 Supabase에 넣어 둔 데이터를 설명하는 문서.
> 양식: Google PAIR [Data Cards Playbook](https://github.com/PAIR-code/datacardsplaybook) `templates/DataCardsExtendedTemplate.md`.
> 처음 온 사람도 이 문서 하나만 읽으면 "무슨 데이터가, 어디에, 얼마나 있고, 뭘 조심해야 하는지" 알 수 있도록 작성.

**요약**

미국 제조업 공장의 대기 규제(40 CFR **Part 63**)를 찾아 주는 AI 서비스용 데이터.
미국 정부가 공개한 자료 4가지를 받아서 Supabase 표 43개에 넣음.

- **eCFR**: 지금 시행 중인 규정집 원문 → 답변의 근거 조문
- **Federal Register**: 규정이 언제, 어떻게 바뀌었는지 → 시행일 확인
- **ECHO**: 공장들의 점검·위반·벌금 기록 → 비슷한 공장 사례
- **ADI + CAA Dashboard**: "이 규정 적용되나요?"에 EPA가 답한 편지 → 선례

이 원본을 잘라서 AI 검색용 조각(`rag_*`)을 만들고, 받은 기록은 운영 표(`common_*`)에 남김.
법률 자문용이 아님. 담당자가 **확인할 후보와 근거를 찾는 용도**.

Dataset Link:  Supabase `public` 스키마 (프로젝트 `husqnrcuoaogdkbpjnep`) |
Data Card Author: Park Seong Ho
기준일: 2026-09-24 
조사 범위: `public` 표 43개 전부
기계용 명세: `[2] db/contracts/*.odcs.yaml` (6개 파일, [부록 A](#부록-a-yaml-데이터-계약-odcs))
티켓: SUU-268

**신입이 먼저 읽을 곳**

1. [1. Dataset Overview](#1-dataset-overview-데이터-한눈에) — 무엇이 얼마나 있나
2. [5. 꼭 알아야 할 규칙 3가지](#5-꼭-알아야-할-규칙-3가지) — 쿼리 짜기 전 필수
3. [7. 조심할 점](#7-limitations-조심할-점) — 틀리기 쉬운 곳

---

## 0. Authorship (누가 만들었나)

| 항목 | 내용 |
|---|---|
| Publishing Organization | US Factory Compliance Service 프로젝트 |
| Industry Type | 기업 (환경 규제 컴플라이언스 SaaS) |
| Dataset Owner | 박성호 |
| Contact | GitHub `suuuuuuungho/US-Factory-Compliance-Service` 이슈, Linear `SUU` 팀 |
| 원본 발행처 | 미국 정부 (eCFR·FR: 연방 관보청 OFR/GPO, ECHO·ADI: EPA) |

---

## 1. Dataset Overview (데이터 한눈에)

### Data Subject(s)

- Data about places and objects — 공장(시설), 규정 조문
- Data about systems or products and their behaviors — 점검·위반·처분 기록
- Non-Sensitive Data about people — 편지 서명자 이름 (공개 문서, [1-3](#sensitivity-of-data-민감-정보))

### Dataset Snapshot

| 항목 | 값 |
|---|---|
| 전체 크기 | 3,142 MB (표 + 색인) |
| 표 수 | 43 |
| 전체 행 수 | 9,593,649 |
| 컬럼 수 | 430 |
| 외래키(FK) 수 | 69 |
| 라벨 | 없음 (사람이 라벨 붙인 데이터 아님) |

### Content Description

표 이름 앞부분(접두사)로 묶음을 구분함.

| 묶음 | 표 이름 | 쉬운 말로 | 원본 기준일 | 표 수 | 행 수 |
|---|---|---|---|---:|---:|
| eCFR | `ecfr_*` | 지금 시행 중인 **규정집 원문** | 2026-09-11 | 6 | 75,471 |
| Federal Register | `fr_*` | 규정이 **언제, 어떻게 바뀌었는지** 알리는 관보 | 2026-09-21 | 4 | 6,069 |
| ECHO | `echo_*` | 공장들이 **점검받고, 어기고, 벌금 낸 기록** | 2026-09-17 | 14 | 9,478,231 |
| ADI + CAA | `adi_*` | EPA가 "이 규정이 적용되나요?"에 **직접 답한 편지** | 2026-09-22 | 9 | 17,830 |
| RAG | `rag_*` | 위 자료를 AI가 **검색하기 좋게 자른 조각**과 답변 기록 | - | 2 | 6,206 |
| Common | `common_*` | **언제, 어디서 받았는지** 적어 둔 운영 기록 | - | 8 | 9,842 |
| **합계** | | | | **43** | **9,593,649** |

### Sensitivity of Data (민감 정보)

| 항목 | 내용 |
|---|---|
| Sensitivity Type | 거의 없음. 원본이 모두 **미국 정부 공개 자료** |
| 민감할 수 있는 칸 | `echo_facility` 시설 이름·주소 (회사 정보, 공개됨) · `adi_block` 서명 조각 617개 (EPA 담당자·회사 사람 이름) · `rag_answer_log.question` (서비스 사용자가 입력한 공장 설명) |
| 보호 방법 | 표 43개 **모두 RLS(행 잠금) 켜짐, 정책 0개** → 공개 키(anon)로는 못 읽음. 서버의 `service_role` 키로만 읽음 |
| 위험과 대책 | 사용자 질문이 쌓이면 회사 내부 정보가 들어갈 수 있음 → `rag_answer_log`는 밖으로 내보내지 않음 |

### Dataset Version and Maintenance (버전과 관리)

| 항목 | 내용 |
|---|---|
| Maintenance Status | **Regularly Updated** — 새로 받을 때마다 새 release. 단, 자동 일정 없음 (사람이 파이프라인을 돌림) |
| Current Version | 자료마다 release 1개씩 (4개 모두 `published`) |
| Last Updated | 2026-09-24 (ECHO 가짜 날짜 정리) |
| Versioning | 새로 받으면 새 `release_id`. 공개한 release는 **고치지 않음** |
| Errors | 적재 오류는 `common_ingest_error`, 읽기 실패 행은 `echo_source_row`에 남김 (지금 둘 다 0건) |
| Next Planned Update | SUU-269: CI에서 "DB = YAML 계약" 자동 검사 · SUU-270: ECHO 적재 코드에서 가짜 날짜 거르기 |

---

## 2. Example of Data Points (데이터 예시)

### Primary Data Modality

- **Text Data** (규정·편지 원문) + **Tabular Data** (ECHO 기록)

### Data Fields (묶음별 표)

#### 2-1. eCFR — 지금 시행 중인 규정집

| | |
|---|---|
| 한 줄 설명 | 미국 연방 규정 40 CFR **Part 63**(유해 대기오염물질 규정) 원문 |
| 서비스에서 쓰임 | 답변에 붙는 **근거 조문**이 모두 여기서 나옴 |
| 계약 파일 | `[2] db/contracts/ecfr.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `ecfr_node` | 3,771 | 목차의 한 칸 (Part 1 · Subpart 158 · 조문 2,473 · 부록 647 · 소제목 492) |
| `ecfr_block` | 71,700 | 조문을 자른 조각 (문단 65,188 · 인용 1,910 · 발췌 1,108 · 그림 1,026 · 제목 996 · 표 784 · 수식 481 · 기타 207) |
| `ecfr_asset` | 0 | 본문 속 그림 파일 — **아직 비어 있음** |
| `ecfr_reference` | 0 | 조문 안의 다른 조문 인용 — **아직 비어 있음** |
| `ecfr_history` | 0 | 개정 이력 — **아직 비어 있음** |
| `ecfr_correction` | 0 | 정정 기록 — **아직 비어 있음** |

| 칸 | 뜻 | 예 |
|---|---|---|
| `node_key` | 항목 주소. 표끼리 잇는 열쇠 | `40/63/subpart-A/section-63.1` |
| `node_type` | 항목 종류 | `part` / `subpart` / `section` / `appendix` / `subject_group` |
| `heading` | 제목 | `§ 63.1 Applicability.` |
| `reserved` | 빈 자리(예약) 항목인지 | `true` / `false` |
| `ecfr_block.kind` | 조각 종류 | `paragraph`, `table`, `formula` … |

#### 2-2. Federal Register — 규정 변경 소식

| | |
|---|---|
| 한 줄 설명 | Part 63을 바꾸는 관보(Federal Register) 문서 목록 |
| 서비스에서 쓰임 | "이 규정이 **언제부터** 바뀌었나?"에 답할 때 |
| 계약 파일 | `[2] db/contracts/fr.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `fr_document` | 1,532 | FR 문서 1건 (Rule 733 · Proposed Rule 720 · Uncategorized 51 · Correction 28) |
| `fr_identifier` | 1,453 | 문서에 붙은 번호 (RIN 1,144 · Docket 309) |
| `fr_cfr_reference` | 2,422 | 문서가 건드리는 CFR 위치 (지금은 모두 `affects`) |
| `fr_date_event` | 662 | 문서의 날짜 (지금은 모두 `effective` 시행일) |

| 칸 | 뜻 | 예 |
|---|---|---|
| `document_key` | 문서 열쇠 = `발행일/문서번호` | `2026-02-24/2026-03638` |
| `type_raw` | 문서 종류 | `Rule`, `Proposed Rule` |
| `publication_date` | 발행일 | `2026-02-24` |
| `effective_on` | API가 준 시행일 | `2026-04-27` |
| `body_status` | 본문 상태 | `xml` 1,185 · `pdf_only` 301 · `missing` 46 |

#### 2-3. ECHO — 점검·위반·벌금 기록

| | |
|---|---|
| 한 줄 설명 | EPA 대기(ICIS-Air) 전국 시설 자료 + 점검→위반→처분 연결표(CAA Pipeline) |
| 서비스에서 쓰임 | "비슷한 공장이 **무엇을 어겨서 얼마를 냈나**?" |
| 계약 파일 | `[2] db/contracts/echo.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `echo_facility` | 280,071 | 시설 1곳 (55개 주·지역. 가동 중 183,937 · 영구 폐쇄 77,832) |
| `echo_facility_identifier` | 279,995 | 시설 번호 ↔ EPA 통합 번호(FRS) 연결 |
| `echo_industry` | 536,235 | 시설의 산업 코드 (NAICS / SIC) |
| `echo_program` | 458,109 | 시설에 걸린 규제 프로그램 (MACT, NSPS, Title V …) |
| `echo_program_subpart` | 191,226 | 시설에 걸린 Subpart (CFR로 변환 성공 155,395 · 실패 35,831) |
| `echo_code_map` | 306 | ECHO 코드 → CFR Subpart 변환표 (ok 299 · 충돌 7) |
| `echo_pollutant` | 864,562 | 시설이 다루는 오염물질 |
| `echo_activity` | 3,242,036 | 활동 1건 (점검 1,818,484 · 굴뚝시험 655,094 · Title V 인증 490,810 · 비공식처분 173,992 · 공식처분 103,656) |
| `echo_activity_facility` | 3,246,696 | 활동 ↔ 시설 연결 |
| `echo_penalty` | 106,520 | 공식처분의 벌금 금액 |
| `echo_violation` | 102,676 | 위반 1건 (HPV·FRV) |
| `echo_violation_facility` | 102,676 | 위반 ↔ 시설 연결 |
| `echo_pipeline_link` | 67,123 | 점검 → 위반 → 처분을 잇는 한 줄 (연결 성공 58,676 · 실패 8,447) |
| `echo_source_row` | 0 | 읽기 실패한 원본 행 — **비어 있음 = 실패 없음** |

| 칸 | 뜻 | 예 |
|---|---|---|
| `pgm_sys_id` | ECHO 시설 번호. ECHO 표끼리 잇는 열쇠 | `0100000009003E0010` |
| `registry_id` | EPA 통합 시설 번호(FRS) | `110070834547` |
| `activity_kind` | 활동 종류 | `inspection` / `stack_test` / `titlev` / `formal` / `informal` |
| `activity_id` | 활동 번호 | (`activity_kind`와 같이 써야 1건) |
| `amount` | 벌금 (달러) | `657412` |

#### 2-4. ADI + CAA Dashboard — EPA 판정 회신

| | |
|---|---|
| 한 줄 설명 | 공장이 "이 규정 우리한테 적용돼요?"라고 물으면 EPA가 답한 편지 모음 |
| 서비스에서 쓰임 | 비슷한 질문의 **선례**로 보여줌 |
| 계약 파일 | `[2] db/contracts/adi.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `adi_source_entry` | 4,061 | 목록의 한 행 (Part 63 후보: ADI 995 + Dashboard 132 = 1,127 · 범위 밖 2,934) |
| `adi_document` | 701 | 회신 문서 1건 (같은 파일은 하나로 합침) |
| `adi_document_version` | 701 | 회신 파일과 뽑은 글자 (ok 683 · 일부 8 · 글자 없음 10) |
| `adi_entry_document` | 701 | 목록 행 ↔ 회신 파일 연결 |
| `adi_page` | 2,333 | PDF 1쪽의 글자 (ok 2,292 · 빈 쪽 41) |
| `adi_block` | 1,960 | 회신을 나눈 조각 (본문 692 · 서명 617 · 질문 237 · 답변 234 · 머리 171 · 조건 9) |
| `adi_cfr_reference` | 7,342 | 회신 안의 CFR 인용 (지금은 모두 `mention` 단순 언급) |
| `adi_facility_candidate` | 31 | 회신 ↔ ECHO 시설 연결 **후보** |
| `adi_document_relation` | 0 | 회신끼리의 관계 (개정·철회) — **아직 비어 있음** |

#### 2-5. RAG — 검색 조각과 답변 기록

| | |
|---|---|
| 한 줄 설명 | AI가 검색하는 조각(임베딩)과, 서비스가 실제로 답한 기록 |
| 만드는 곳 | `[2] db/pipeline/5_rag/`, `[2] db/pipeline/4_ADI+CAA/letter_chunk.py` |
| 계약 파일 | `[2] db/contracts/rag.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `rag_chunk` | 6,157 | 검색 조각 1개 (eCFR 5,625 · ADI 532). 모두 `kanon-2-embedder` 1792차원, `embedded` |
| `rag_answer_log` | 49 | 질문 1개와 답 (2026-09-21 ~ 09-23, 비용 합계 약 $1.01) |

#### 2-6. Common — 운영 기록

| | |
|---|---|
| 한 줄 설명 | 모든 묶음이 같이 쓰는 "언제, 어디서, 무엇을 받았나" 장부 |
| 계약 파일 | `[2] db/contracts/common.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `common_ingest_run` | 4 | 적재 실행 1번 (4묶음 모두 `succeeded`) |
| `common_raw_object` | 4,915 | 받은 원본 파일 1개 (PDF 2,192 · JSON 1,533 · XML 1,186 · 기타 4) |
| `common_dataset_release` | 4 | release 1개 (eCFR·FR·ECHO·ADI 각 1개, 모두 `published`) |
| `common_dataset_current` | 4 | 묶음마다 "지금 쓰는 release" 가리킴 |
| `common_release_object` | 4,915 | release ↔ 원본 파일 연결 |
| `common_change_log` | 0 | release 사이 변경 기록 — **아직 비어 있음** |
| `common_ingest_checkpoint` | 0 | 나눠 받기 진행 위치 — **아직 비어 있음** |
| `common_ingest_error` | 0 | 적재 오류 — **비어 있음 = 오류 없음** |

### Typical Data Point (보통 데이터)

eCFR 조문 1개. 목차 주소·종류·제목이 다 차 있음.

```json
{"node_key": "40/63/subpart-A/section-63.1",
 "node_type": "section",
 "heading": "§ 63.1 Applicability.",
 "reserved": false}
```

### Atypical Data Point (이상한 데이터)

ECHO 점검 1건. 원본 날짜가 `1010년`이라 가짜로 보고 **빈값으로 바꿈**. 원래 글자는 `raw_date`에 남김.

```json
{"activity_kind": "inspection",
 "activity_id": "3400591413",
 "activity_date": null,
 "raw_date": "01-15-1010"}
```

---

## 3. Motivations & Intentions (왜 만들었나)

| 항목 | 내용 |
|---|---|
| Purpose | **Production** — 실제 서비스 답변에 씀 |
| Domain | `Environmental Compliance`, `Clean Air Act`, `40 CFR Part 63`, `Title V`, `RAG` |
| Motivating Factor | Title V 공장 담당자는 법률 전문가가 아님. 크고 자주 바뀌는 규정집에서 "우리 공장에 적용되는 조항"을 직접 찾다가 빠뜨리기 쉬움 |

### Suitable Use Case (이렇게 쓰세요)

- 공장 설명을 받아 **적용될 수 있는 Part 63 조항 후보** 찾기
- 답변에 **근거 조문**(eCFR)과 **시행일**(FR) 붙이기
- 비슷한 질문의 **EPA 회신 선례**(ADI) 보여주기
- 비슷한 공장의 **점검·위반·벌금 사례**(ECHO) 보여주기

### Unsuitable Use Case (이렇게 쓰면 안 돼요)

- ❌ **"이 조항이 적용된다"고 확정**하기 — 후보일 뿐. 최종 판단은 담당자·EPA
- ❌ `Proposed Rule`을 시행 중인 규정처럼 쓰기
- ❌ ADI 회신을 **지금도 유효한 판정**처럼 쓰기 (`legal_status` 모두 `unknown`)
- ❌ Part 63 **밖** 규정(Part 60, 70 등) 답변 — eCFR은 Part 63만 들어 있음
- ❌ 특정 회사 평판 평가 — ECHO는 전국 자료지만 서비스 목적과 다름

---

## 4. Access, Retention & Wipeout (접근·보관·삭제)

| 항목 | 내용 |
|---|---|
| Access Type | 내부 전용 (서버만 읽음) |
| 원본 라이선스 | 미국 연방정부 저작물 → 공개 자료 (Public Domain) |
| 접근 방법 | `.env`의 `SUPABASE_URL` + `service_role` 키. 공개 키(anon)로는 RLS 때문에 0행 |
| Documentation | 이 문서 + `[2] db/contracts/*.odcs.yaml` + `[1] docs/2) db/db 구축 계획/` |
| Retention | **원본은 버리지 않음.** 받은 파일은 `common_raw_object`에 기록. 표로 못 뽑은 값은 `raw_metadata`, `attributes`, `raw_date(s)` 같은 칸에 그대로 남김 |
| Wipeout | 정해진 삭제 규칙 **없음** (확인 필요) |

---

## 5. 꼭 알아야 할 규칙 3가지

### ① release = "한 번에 적재한 묶음"

- 자료를 새로 받을 때마다 새 `release_id`가 생김.
- 한 번 공개(`published`)한 release는 **고치지 않음**. 바뀌면 새 release를 만듦.
- 그래서 거의 모든 표의 열쇠(PK)에 `release_id`가 들어 있음.

### ② 최신 데이터는 `common_dataset_current`에서 찾음

```sql
-- 지금 서비스가 쓰는 eCFR 조문만 보기
select n.*
from ecfr_node n
join common_dataset_current c
  on c.release_id = n.release_id and c.dataset = 'ecfr';
```

지금은 자료마다 release가 1개씩만 있음. 그래도 **항상 이렇게 걸러 쓰는 습관**을 들임.

### ③ 원본은 절대 버리지 않음

- 헷갈리면 `common_raw_object`에서 원본 파일을 다시 봄.

---

## 6. Provenance (어디서 어떻게 받았나)

### Collection (수집)

| 묶음 | Method | 어디서 | Cadence |
|---|---|---|---|
| eCFR | API 호출 | [eCFR API](https://www.ecfr.gov/developers/documentation/api/v1) `full/{date}/title-40.xml?part=63` | 매일 03:17 UTC (자동) |
| FR | API 호출 | [FR API](https://www.federalregister.gov/developers/documentation/api/v1) `conditions[cfr][title]=40&conditions[cfr][part]=63` (발행일 1994-01-11 ~ 2026-07-06) | 매일 03:17 UTC (자동) |
| ECHO | 파일 다운로드 | [ECHO 다운로드](https://echo.epa.gov/tools/data-downloads) `ICIS-AIR_downloads.zip`, `pipeline_caa_downloads.zip` | 매주 화요일 05:17 UTC (자동) |
| ADI + CAA | 목록 수집 + PDF 다운로드 | EPA ADI(Applicability Determination Index) 목록 + CAA Dashboard 목록, 회신 PDF | 수동 |

- 파이프라인 코드: `[2] db/pipeline/<번호>_<자료>/` (`*_fetch` 받기 → `*_parse` 읽기 → `*_load` 넣기 → `*_release` 공개)
- 자동 일정: eCFR·FR은 `.github/workflows/db-refresh.yml`, ECHO는 `.github/workflows/echo-refresh.yml`.
- RAG 색인 재생성은 사람이 실행.

### Data Integration (데이터가 흘러가는 길)

```
 인터넷 원본 (eCFR · FR · ECHO · ADI)
        │  내려받기
        ▼
 common_raw_object      ← 받은 파일 1개 = 1행 (지문 sha256 포함)
        │  읽어서 표로 만들기
        ▼
 ecfr_* · fr_* · echo_* · adi_*     ← 모든 행에 release_id 가 붙음
        │  잘라서 임베딩
        ▼
 rag_chunk              ← AI가 검색하는 곳
        │
        ▼
 서비스 답변 → rag_answer_log
```

### 표끼리 어떻게 이어지나

```
common_dataset_release ─┬─ ecfr_node ── ecfr_block
                        ├─ fr_document ─┬─ fr_identifier
                        │               ├─ fr_date_event
                        │               └─ fr_cfr_reference ──▶ ecfr_node
                        ├─ echo_facility ─┬─ echo_program ── echo_program_subpart
                        │   (pgm_sys_id)  ├─ echo_pollutant / echo_industry
                        │                 ├─ echo_activity_facility ── echo_activity ── echo_penalty
                        │                 └─ echo_violation_facility ── echo_violation
                        └─ adi_source_entry ── adi_entry_document ── adi_document_version
                                                                       ├─ adi_page
                                                                       ├─ adi_block
                                                                       └─ adi_cfr_reference ──▶ ecfr_node
```

- 묶음을 넘는 다리는 두 개: **FR·ADI → eCFR** (`*_node_key`), **ADI → ECHO** (`adi_facility_candidate`).
- 외래키(FK) 69개 전체는 각 YAML의 `relationships`에 있음.

### Collection Criteria (무엇을 넣고 뺐나)

| 묶음 | Inclusion (넣음) | Exclusion (뺌) |
|---|---|---|
| eCFR | 40 CFR Part 63 전체 | Part 63 밖 |
| FR | Part 63을 건드리는 문서 전부 (Proposed Rule 포함) | - |
| ECHO | **Part 63만 고르지 않고** 전국 대기 시설 전부 (280,071곳 = 원본 CSV 행 수) | - |
| ADI | 목록 4,061행은 모두 넣고, Part 63 후보 1,127행만 회신 PDF를 받음 | 범위 밖 2,934행은 PDF 안 받음 |

---

## 7. Limitations (조심할 점)

### eCFR

- `XXXXXX`는 **진짜 Subpart 이름**. 빈칸 표시가 아님. (예전에 이걸 빈칸으로 착각해서 없는 Subpart를 지어낸 적이 있음)
- `node_type = appendix`에는 `Table 1 to Subpart A` 같은 **표도 들어 있음**. 647개가 다 "부록"은 아님.
- 본문은 `paragraph`만 있는 게 아님. 표·수식·그림을 빼면 내용이 빠짐.

### Federal Register

- **문서번호만으로는 1건이 정해지지 않음.** `03-5521` 하나가 Rule과 Correction 두 행에 쓰임. 열쇠는 `document_key`.
- `Proposed Rule`(제안)은 **아직 시행 중인 규정이 아님**.
- 시행일은 조항마다 다를 수 있음. `effective_on` 하나만 믿지 말고 `fr_date_event`도 봄.

### ECHO

- **벌금을 `echo_pipeline_link`에서 더하면 부풂.** 같은 처분이 여러 줄에 나옴. 합계는 `echo_penalty`에서 처분 1건당 한 번만 더함.
- `activity_id`만으로는 1건이 안 정해짐. **항상 `activity_kind`와 같이** 씀.
- `echo_program_subpart`에서 변환 실패(`unresolved`) 35,831행은 `cfr_subpart`가 비어 있음. **짐작해서 채우지 않음.**

### ADI + CAA

- `adi_document_version.signed_on`(서명 날짜)은 **지금 701건 모두 비어 있음.** 날짜가 필요하면 `adi_source_entry.letter_date_raw`(원본 글자)를 봄.
- `legal_status`는 모두 `unknown`. 이 회신이 **지금도 유효한지는 아직 모름.**
- Dashboard의 `link_text`는 날짜처럼 보여도 **날짜가 아님.**
- `adi_facility_candidate`는 "후보". 확정된 연결이 아님.

### RAG

- 검색할 때는 `common_dataset_current`가 가리키는 release의 조각만 씀.
- `rag_chunk`를 만드는 `create table` 파일이 `[2] db/migrations/`에 **없음**. (아래 10절)

---

## 8. Transformations (원본을 어떻게 바꿨나)

| 무엇 | 어떻게 | 원본은? |
|---|---|---|
| ECHO 중복 합치기 | 같은 번호가 여러 줄 → 한 줄 (열쇠: `activity_kind + activity_id`, 오염물질은 `pgm_sys_id + pollutant_key`) | 원본 행 버린 것 0. 11개 파일 모두 `read = ok`, 실패(`held`) 0건 |
| ECHO 가짜 날짜 정리 | 1900년 전·2100년 후 날짜 106개를 빈값으로 (예: `0001-01-01`, `8888-01-01`, 오타 `0215-11-02`). 2026-09-24 | `raw_date` / `raw_dates`에 그대로. 지금 `activity_date` 빈값은 6,321건 |
| ECHO 코드 → CFR 변환 | `echo_code_map` 306개로 Subpart 변환 (ok 299 · 충돌 7) | 원래 코드 유지 |
| ADI 파일 합치기 | 같은 PDF는 하나로 (`adi_document` 701건) | `adi_source_entry`에 목록 원본 |
| 잘라서 임베딩 | eCFR·ADI 글 → `rag_chunk` 6,157개, `kanon-2-embedder` 1792차원 | 원래 조각(`ecfr_block`, `adi_block`) 유지 |

### ECHO 원본 CSV보다 표의 행이 적은 이유 (확인 완료)

줄어든 이유는 **같은 번호가 여러 줄에 나와서 한 줄로 합쳤기 때문**.

| 원본 CSV | 원본 행 | 번호 중복 | 표 행 (= 원본 − 중복) |
|---|---:|---:|---:|
| Title V 인증 | 2,583,180 | 2,092,370 | 490,810 |
| 비공식처분 | 339,879 | 165,887 | 173,992 |
| 오염물질 | 977,624 | 113,062 | 864,562 |

- 근거: `[2] db/3) ECHO/parsed/2026-09-17/report.json`의 `files`, `identifiers`, `duplicates`
- ⚠️ 번호는 같은데 내용이 다른 활동이 50,869건 있음(`conflicts.echo_activity`). 합칠 때 첫 줄만 남음.

### Residual Risk (남은 위험)

- 가짜 날짜는 다시 적재하면 또 들어옴. 적재 코드는 SUU-270에서 고침.

---

## 9. Validation (어떻게 확인했나)

| 방법 | 결과 |
|---|---|
| 행 수 직접 세기 (`count(*)`) | 이 문서 숫자와 일치 (2026-09-24). SQL은 아래 |
| YAML 6개 ODCS v3.1.0 JSON Schema 검사 | 오류 0개 (표 43 · 칸 430) |
| 적재 리포트 (`report.json`) | ECHO 11개 파일 `read = ok`, 실패 0 |

숫자가 이상하면 다시 돌려 봄:

```sql
select table_name,
       (xpath('/row/c/text()',
              query_to_xml(format('select count(*) as c from public.%I', table_name), false, true, '')))[1]::text::bigint as rows
from information_schema.tables
where table_schema = 'public' and table_type = 'BASE TABLE'
order by 1;
```

---

## 10. Reflections on Data (지금 알고 있는 문제, 확인 필요)

| # | 무엇 | 왜 문제 |
|---|---|---|
| 1 | `fr_diff` 표가 DB에 **없음** | `[2] db/migrations/SUU-230_fr_diff.sql` 파일은 있는데 적용이 안 됨 |
| 2 | `rag_chunk`의 `create table` 파일이 **없음** | DB에는 있음. 새로 만들 때 똑같이 재현하기 어려움 |
| 3 | 빈 표 9개 | `ecfr_asset`, `ecfr_reference`, `ecfr_history`, `ecfr_correction`, `adi_document_relation`, `common_change_log`, `common_ingest_checkpoint`는 아직 안 채움. `echo_source_row`, `common_ingest_error`는 비어 있는 게 정상 |
| 5 | 삭제 규칙 없음 | `rag_answer_log`에 사용자 질문이 계속 쌓임 |

---

## 11. Terms of Art (용어 사전)

| 용어 | 쉬운 뜻 |
|---|---|
| CFR | 미국 연방 규정집. Title 40 = 환경 |
| Part 63 | 유해 대기오염물질(HAP) 규정. 업종별로 Subpart가 나뉨 |
| Subpart | Part 안의 업종별 장(章). 예: Subpart DDDDD = 보일러 |
| eCFR | CFR의 온라인판. 매일 갱신 |
| Federal Register (FR) | 미국 정부 관보. 규정이 바뀌면 여기에 먼저 나옴 |
| Rule / Proposed Rule | 확정 규칙 / 제안(아직 시행 전) |
| Docket, RIN | 규칙 제정 서류철 번호, 규칙 고유 번호 |
| ECHO | EPA의 점검·위반·처분 공개 시스템 |
| ICIS-Air | ECHO 안의 대기 분야 자료 |
| HPV / FRV | 중대 위반 / 연방 보고 대상 위반 |
| Title V | 큰 공장이 받아야 하는 대기 운영 허가 |
| ADI | EPA 적용 판정 회신 모음 |
| release | 한 번에 적재한 데이터 묶음. 공개 후 고치지 않음 |
| PK / FK | 열쇠 칸 / 다른 표를 가리키는 칸 |
| RLS | 행 잠금. 켜져 있고 정책이 없으면 서버 키로만 읽음 |
| 임베딩 | 글을 숫자 벡터로 바꾼 것. 뜻이 비슷한 글을 찾을 때 씀 |
| Data Contract | "이 데이터는 이런 모양이다"라는 기계용 약속서 |
| Data Card | 데이터를 사람에게 설명하는 표준 설명서 (Google PAIR) |

---

## 부록 A. YAML 데이터 계약 (ODCS)

### 무엇인가요?

- **사람용 설명서**는 이 문서(Data Card). **기계용 약속서**는 YAML.
- YAML에는 "이 표에는 이런 칸이 있고, 이 칸은 비면 안 되고, 이 표로 이어진다"가 적혀 있음.
- 양식은 세계 공통 양식인 **ODCS v3.1.0**(Open Data Contract Standard). PayPal이 만들어 공개했고, 지금은 Linux Foundation이 관리. → [bitol-io/open-data-contract-standard](https://github.com/bitol-io/open-data-contract-standard)

### 파일

| 파일 | 표 수 | 칸 수 |
|---|---:|---:|
| `[2] db/contracts/ecfr.odcs.yaml` | 6 | 63 |
| `[2] db/contracts/fr.odcs.yaml` | 4 | 56 |
| `[2] db/contracts/echo.odcs.yaml` | 14 | 133 |
| `[2] db/contracts/adi.odcs.yaml` | 9 | 82 |
| `[2] db/contracts/rag.odcs.yaml` | 2 | 33 |
| `[2] db/contracts/common.odcs.yaml` | 8 | 63 |

### YAML 읽는 법 (예시 하나)

```yaml
- name: activity_id          # 칸 이름
  logicalType: string        # 뜻으로 본 타입 (글자)
  physicalType: text         # DB 실제 타입
  description: ECHO 활동 번호. activity_kind 와 함께 써야 하나로 정해진다
  required: true             # 비면 안 됨
  primaryKey: true           # 열쇠(PK)의 일부
```

- `quality`: 지켜야 할 규칙. `library`는 기계가 검사하는 규칙(예: 표가 비면 안 됨), `text`는 사람이 읽는 주의 문장.
- `customProperties.rowCount`: 기준일(2026-09-24)의 실제 행 수.

### 버전 규칙 (Git으로 관리)

| 바뀐 것 | 버전 올리기 | 예 |
|---|---|---|
| 설명 글자만 고침 | 끝자리 | 1.0.0 → 1.0.1 |
| 칸·표 **추가** | 가운데 | 1.0.0 → 1.1.0 |
| 칸·표 **삭제**, 칸 **뜻이 바뀜** | 앞자리 | 1.0.0 → 2.0.0 |

- 표를 바꾸는 migration PR에는 **YAML 수정도 같이** 넣음.
- 다음 단계(SUU-269): CI에서 `datacontract test`로 "DB가 YAML과 같은지" 자동 검사.

-
