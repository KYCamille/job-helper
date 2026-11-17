@AGENTS.md

# Claude Code 專屬補充

- 本專案的所有規則都在上方引入的 AGENTS.md，這裡只放 Claude Code 才用得到的設定。
- 可用 Skills（位於 `.claude/skills/`）：
  - `analyze-job`：工作流程 ②③，產出 `jobs/<slug>.html`
  - `tailor-resume`：工作流程 ④，產出 `resumes/<slug>.html`
- 完成標準一律以 `python3 scripts/check.py` 的輸出為準；不要只說「我檢查過了」。
- 工作流程 ⑥「審查」請用 subagent 或新對話執行，只給它 `profile/profile.md`、raw JD 與產出頁，不要讓寫的人審自己的作品。
- 未經使用者同意，不要 `git push`。
