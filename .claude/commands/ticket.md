---
description: 기능 아이디어를 Linear 티켓으로 쪼개서 발행한다
argument-hint: "만들고 싶은 기능 한두 줄"
---

만들고 싶은 기능: $ARGUMENTS

## 먼저 읽기

- `[1] docs/1) project/1_full/1_Project_full.md` — 이 서비스가 무엇인지
- `[1] docs/4) workflow/2_rules.md` — 제목 규칙(1번), 티켓 크기(2번), 설계 파일 위치(12번)

## 순서

1. 애매한 점이 있으면 질문 1~2개만 하고 답을 기다린다. 없으면 바로 2번.
2. 기능을 티켓 여러 개로 쪼갠다. **티켓 하나 = 테스트 하나로 "됐다/안 됐다" 확인 가능한 크기.**
3. 아래 형식으로 초안을 터미널에 보여주고 "이대로 발행할까요?"를 묻는다. **아직 발행하지 않는다.**
4. 사람이 OK 하면 Linear MCP `save_issue`로 발행한다.
   - team: `Suuuuuuungho`, project: `US Factory Compliance Service`, state: `Todo`, assignee: `me`
   - 순서가 있으면 `blockedBy`로 연결한다
5. 발행된 이슈 번호·제목·링크·설계 파일 위치를 표로 보여준다. 설계 파일 위치는 제목의 `종류(영역)`으로 정한다 (2_rules.md 12번). 예: `feat(db)` → `[5] tickets/1)DB/1_feat/SUU-번호.md`

## 티켓 형식

제목: `종류(영역): 결과가 보이는 한 문장` (2_rules.md 1번. 40자 이내)

설명(description)은 이 네 칸만:

```
## 무엇을
이 티켓이 끝나면 무엇이 되는지. 5살도 이해할 만큼 쉬운 말로 딱 한 문장.

## 배경
왜 필요한가. 2~3줄.

## 범위
건드릴 폴더/파일. 안 하는 것.

## 완료 기준
- [ ] 테스트로 확인 가능한 문장 1~3개
```
