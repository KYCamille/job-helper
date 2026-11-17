# 求職小幫手 Job Helper

一個用 **AGENTS.md 規則驅動** 的求職網站：貼上一則職缺，AI 就依同一套流程產出「職缺解析」與「客製化履歷」兩個頁面。

- 🌐 網站：見 GitHub Pages 連結（repo 右側 About）
- 📘 AI 規則：[`AGENTS.md`](AGENTS.md)（Claude Code 透過 [`CLAUDE.md`](CLAUDE.md) 引入）
- ✅ 自動檢查：`python3 scripts/check.py`

## 新增一則職缺

1. 把職缺原文存成 `raw/jobs/YYYY-MM-company-role.md`
2. 對 AI 說：「請先讀 AGENTS.md，解析新職缺 `<slug>`」
3. AI 依流程產出 `jobs/<slug>.html`、`resumes/<slug>.html`，更新首頁卡片
4. `python3 scripts/check.py` 全部通過 → commit → push

> 網站上的求職者「林小安」與三間公司皆為**虛構範例**，用來示範流程。真實履歷請放在 `private/`（不會上傳）。
