---
description: 프로젝트 md를 규칙대로 검사하고 Word·PDF 보고서로 만든다
argument-hint: "(비우면 summary·full·항목 5개) 또는 md 경로"
---

대상: $ARGUMENTS

비어 있으면 아래 7개 파일이다.

- `[1] docs/1) project/0_summary/0_Project_summary.md`
- `[1] docs/1) project/1_full/1_Project_full.md`
- `[1] docs/1) project/2_프로젝트 개요/2_프로젝트 개요.md`
- `[1] docs/1) project/3_문제 정의 및 해결/3_문제 정의 및 해결.md`
- `[1] docs/1) project/4_데이터 파이프라인 구축/4_데이터 파이프라인 구축.md`
- `[1] docs/1) project/5_RAG 품질 개선/5_RAG 품질 개선.md`
- `[1] docs/1) project/6_TDD 개발 자동화/6_TDD 개발 자동화.md`

## 먼저 읽기

- `[1] docs/4) workflow/3_doc_rules.md` — md 작성 규칙과 검사 항목(6절)

## 순서

1. 레포 루트에서 실행한다. 먼저 full에서 항목 md 5개를 다시 만든다. 오류가 나면 메시지를 보여 주고 멈춘다.

```
python "[1] docs/4) workflow/report/md_split.py"
```

2. PDF는 로컬 Word로 만들어서 30초쯤 걸린다.

```
python "[1] docs/4) workflow/report/md_to_docx.py" "[1] docs/1) project/0_summary/0_Project_summary.md" "[1] docs/1) project/1_full/1_Project_full.md" "[1] docs/1) project/2_프로젝트 개요/2_프로젝트 개요.md" "[1] docs/1) project/3_문제 정의 및 해결/3_문제 정의 및 해결.md" "[1] docs/1) project/4_데이터 파이프라인 구축/4_데이터 파이프라인 구축.md" "[1] docs/1) project/5_RAG 품질 개선/5_RAG 품질 개선.md" "[1] docs/1) project/6_TDD 개발 자동화/6_TDD 개발 자동화.md"
```

3. 출력을 쉬운 한국어로 정리해 보여 준다.
   - `자동으로 고쳤습니다`: md를 직접 고쳤다. `git diff`로 무엇이 바뀌었는지 한 줄씩 알려 준다.
   - `파일:줄: 메시지`: 사람이 고쳐야 하는 문제다. 줄 번호와 무엇을 고치면 되는지 알려 준다.
   - 문제가 하나라도 있으면 그 파일은 Word를 만들지 않았다고 말하고 멈춘다. md를 대신 고치지 않는다.
4. 성공하면 만든 파일 경로(.docx, .pdf)를 알려 준다. 결과물은 md 옆에 같은 이름으로 생긴다.
5. `[1] docs/1) project/README.md`를 갱신한다.
   - 폴더의 파일 목록(`ls`)과 README 표를 비교한다. 새 파일은 한 줄 설명을 넣고, 없어진 파일은 뺀다.
   - summary·full의 `##` 장 목록이 바뀌었으면 설명 속 장 이름도 맞춘다. 설명은 한 줄로 쓴다.
   - 바뀐 게 없으면 README를 건드리지 않는다. 바꿨으면 무엇을 바꿨는지 한 줄로 알려 준다.

## 참고

- Word가 없는 컴퓨터에서는 `--no-pdf`를 붙여 .docx만 만든다.
- Word 모양(글꼴·색·번호)을 바꾸려면 `md_to_docx.py`를 고친다. 설계는 `[5] tickets/5)CI/1_feat/SUU-297.md`.
