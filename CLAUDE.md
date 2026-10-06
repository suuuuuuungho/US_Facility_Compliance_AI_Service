# 0. 코드 작성에 관한 전반적인 규칙이다. 

1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them - don't pick silently.
If a simpler approach exists, say so. Push back when warranted.
If something is unclear, stop. Name what's confusing. Ask.

2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
No error handling for impossible scenarios.
If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:

Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:

Remove imports/variables/functions that YOUR changes made unused.
Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

"Add validation" → "Write tests for invalid inputs, then make them pass"
"Fix the bug" → "Write a test that reproduces it, then make it pass"
"Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.


# 항상 나에게 질문을 하거나 답변을 할 때, 5살도 듣고 이해할 수 있을만큼 쉽고 간결하게 말한다. 

# 애매모호 할 때, 스스로 판단하지 않고 나에게 묻고 진행한다. 

# 항상 이 파일을 읽고 시작한다. 이 프로젝트를 요약한 파일이다.  
`C:\Users\Admin\Desktop\US Factory Compliance Service\[1] docs\1) project\1_full\1_Project_full.md`

# 이 프로젝트는 항상 이 workflow 순서대로 진행한다.
`C:\Users\Admin\Desktop\US Factory Compliance Service\[1] docs\4) workflow\1_workflow.md`

# Linear 이슈, 브랜치, PR, 커밋을 만들기 전에 항상 이 규칙 파일을 읽고 그대로 지킨다.
`C:\Users\Admin\Desktop\US Factory Compliance Service\[1] docs\4) workflow\2_rules.md`

# 새 터미널을 열어 작업할 때는 무조건 worktree를 나눈다 (`claude --worktree <이름>`). 같은 폴더에서 터미널 두 개로 git을 만지지 않는다. 자세한 규칙은 위 `2_rules.md` 3절.
