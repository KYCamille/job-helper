#!/usr/bin/env python3
"""求職小幫手 — 自動檢查腳本（AGENTS.md 第 9 節「完成標準」）

用法：在專案根目錄執行  python3 scripts/check.py
全部通過會印出 ALL CHECKS PASSED，否則列出每個錯誤並以 exit code 1 結束。
只使用 Python 標準函式庫，不需要安裝任何套件。
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 每種頁面必備的 section id（對應 AGENTS.md 第 4 節）。新增頁面類型時在這裡加一行。
PAGE_RULES = {
    "job": ["summary", "requirements", "keywords", "match", "gaps", "interview", "sources"],
    "resume": ["target", "headline", "skills", "experience", "projects", "education", "changes"],
}
SLUG_RE = re.compile(r"^\d{4}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)+$")
LEVELS = [(80, "badge-high"), (60, "badge-mid"), (0, "badge-low")]

# 公開檔案不可出現的個資格式（AGENTS.md 第 11 節）
PII_PATTERNS = {
    "Email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "手機號碼": re.compile(r"09\d{2}[-\s]?\d{3}[-\s]?\d{3}"),
    "身分證字號": re.compile(r"\b[A-Z][12]\d{8}\b"),
}

errors: list[str] = []


def err(path: Path | str, msg: str) -> None:
    errors.append(f"[{Path(path).relative_to(ROOT) if isinstance(path, Path) else path}] {msg}")


class Page(HTMLParser):
    """收集頁面中的 meta、section id、連結、class、inline style 與各區塊文字。"""

    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.ids: list[str] = []
        self.links: list[str] = []
        self.classes: list[str] = []
        self.inline_styles = 0
        self.section_text: dict[str, list[str]] = {}
        self._section_stack: list[str | None] = []
        self.data_total: list[str] = []
        self._in_total = False
        self.card_slugs: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and "name" in a:
            self.meta[a["name"]] = a.get("content", "")
        if "id" in a:
            self.ids.append(a["id"])
        if "style" in a:
            self.inline_styles += 1
        if "class" in a:
            self.classes.extend(a["class"].split())
        if "data-slug" in a:
            self.card_slugs.append(a["data-slug"])
        if tag in ("a", "link") and a.get("href"):
            self.links.append(a["href"])
        if tag == "section":
            self._section_stack.append(a.get("id"))
        if "data-total" in a:
            self._in_total = True

    def handle_endtag(self, tag):
        if tag == "section" and self._section_stack:
            self._section_stack.pop()
        if tag == "td":
            self._in_total = False

    def handle_data(self, data):
        if self._section_stack and self._section_stack[-1]:
            self.section_text.setdefault(self._section_stack[-1], []).append(data)
        if self._in_total:
            self.data_total.append(data)


def parse(path: Path) -> Page:
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    return p


def check_links(path: Path, page: Page) -> None:
    for href in page.links:
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = (path.parent / href.split("#")[0]).resolve()
        if not target.exists():
            err(path, f"連結失效：{href}")


def check_common(path: Path, page: Page, text: str) -> None:
    if "{{" in text:
        err(path, "還有沒替換的 {{佔位符}}")
    if page.inline_styles:
        err(path, f"有 {page.inline_styles} 個 inline style（AGENTS.md 第 7 節禁止）")
    if re.search(r"#[0-9a-fA-F]{3,6}\b(?![^<]*>)", re.sub(r"<[^>]+>", "", text)) and "<style" in text:
        err(path, "HTML 內寫死色碼")
    if "<style" in text:
        err(path, "HTML 內不可有 <style>，樣式請寫在 assets/style.css")
    if 'href="../assets/style.css"' not in text and 'href="assets/style.css"' not in text:
        err(path, "沒有引用 assets/style.css")
    check_links(path, page)


def numbers_in(s: str) -> set[str]:
    """取出「數字＋單位」，例如 12%、1.5小時、300萬，避免 15% 因為別處有 15 而漏抓。"""
    s = re.sub(r"[ \t]+", "", s.replace(",", ""))
    return set(re.findall(r"\d+(?:\.\d+)?(?:%|小時|萬|間|週|位|個|筆|人|年|倍|元|份|篇)?", s))


def check_job(path: Path, page: Page, slug: str) -> int | None:
    for sid in PAGE_RULES["job"]:
        if sid not in page.ids:
            err(path, f"缺少必備區塊 id=\"{sid}\"")
    if not (ROOT / "raw" / "jobs" / f"{slug}.md").exists():
        err(path, f"找不到職缺原文 raw/jobs/{slug}.md")

    # 四個面向分數加總 = 總分
    match_text = "".join(page.section_text.get("match", []))
    scores = [int(x) for x in re.findall(r"(\d+)\s*/\s*(?:40|30|15)(?!\d)", match_text)]
    total_m = re.search(r"(\d+)\s*/\s*100", "".join(page.data_total))
    if len(scores) != 4:
        err(path, f"適配度應有 4 個面向分數，找到 {len(scores)} 個")
        return None
    if not total_m:
        err(path, "找不到總分（data-total 的「n / 100」）")
        return None
    total = int(total_m.group(1))
    if sum(scores) != total:
        err(path, f"分數加總 {sum(scores)} ≠ 總分 {total}")
    for limit, s in zip((40, 30, 15, 15), scores):
        if not 0 <= s <= limit:
            err(path, f"分數 {s} 超出配分範圍 0–{limit}")

    expected = next(cls for floor, cls in LEVELS if total >= floor)
    badges = [c for c in page.classes if c.startswith("badge-")]
    if expected not in badges:
        err(path, f"總分 {total} 應使用 {expected}，頁面上是 {badges or '無'}")

    has_resume = (ROOT / "resumes" / f"{slug}.html").exists()
    links_resume = f"../resumes/{slug}.html" in page.links
    if total >= 60 and not (has_resume and links_resume):
        err(path, "總分 ≥ 60 必須產出並連結 resumes/<slug>.html")
    if total < 60 and has_resume:
        err(path, "總分 < 60 不應產出客製化履歷（AGENTS.md 第 8 節 ④）")
    return total


def check_resume(path: Path, page: Page, slug: str, profile_numbers: set[str]) -> None:
    for sid in PAGE_RULES["resume"]:
        if sid not in page.ids:
            err(path, f"缺少必備區塊 id=\"{sid}\"")
    if not (ROOT / "jobs" / f"{slug}.html").exists():
        err(path, f"找不到對應的職缺頁 jobs/{slug}.html")
    # 誠實原則：履歷內文出現的數字都必須在 profile.md 找得到（changes 區塊除外）
    for sid in ("headline", "skills", "experience", "projects", "education"):
        text = "".join(page.section_text.get(sid, []))
        for n in sorted(numbers_in(text) - profile_numbers):
            err(path, f"區塊 {sid} 出現 profile.md 沒有的數字「{n}」（可能是捏造或灌水）")


def check_index(job_scores: dict[str, int | None]) -> None:
    path = ROOT / "index.html"
    page = parse(path)
    check_common(path, page, path.read_text(encoding="utf-8"))
    for slug in job_scores:
        if slug not in page.card_slugs:
            err(path, f"首頁缺少職缺卡片 data-slug=\"{slug}\"")
    for slug in page.card_slugs:
        if slug not in job_scores:
            err(path, f"首頁卡片 {slug} 沒有對應的 jobs/{slug}.html")
    # 卡片依 slug 新到舊排列（新卡片在最上方）
    if page.card_slugs != sorted(page.card_slugs, reverse=True) and len({s[:7] for s in page.card_slugs}) > 1:
        err(path, "職缺卡片應依月份由新到舊排列")


def check_pii() -> None:
    public = [p for p in ROOT.rglob("*") if p.is_file()
              and p.suffix in {".html", ".md", ".css", ".json"}
              and not {"private", ".git"} & set(p.relative_to(ROOT).parts)]
    for p in public:
        text = p.read_text(encoding="utf-8", errors="ignore")
        for label, rx in PII_PATTERNS.items():
            for m in rx.findall(text):
                if label == "Email" and m.endswith(("@anthropic.com", "@example.com")):
                    continue
                err(p, f"疑似{label}：{m}（公開檔案不可放個資）")


def main() -> int:
    profile_numbers = numbers_in((ROOT / "profile" / "profile.md").read_text(encoding="utf-8"))
    job_scores: dict[str, int | None] = {}

    for kind, folder in (("job", "jobs"), ("resume", "resumes")):
        for path in sorted((ROOT / folder).glob("*.html")):
            slug = path.stem
            text = path.read_text(encoding="utf-8")
            page = parse(path)
            if not SLUG_RE.match(slug):
                err(path, "檔名不符合 YYYY-MM-company-role 格式")
            if page.meta.get("page-type") != kind:
                err(path, f"meta page-type 應為 {kind}")
            if page.meta.get("slug") != slug:
                err(path, f"meta slug「{page.meta.get('slug')}」與檔名不一致")
            check_common(path, page, text)
            if kind == "job":
                job_scores[slug] = check_job(path, page, slug)
            else:
                check_resume(path, page, slug, profile_numbers)

    for raw in sorted((ROOT / "raw" / "jobs").glob("*.md")):
        if not (ROOT / "jobs" / f"{raw.stem}.html").exists():
            err(raw, "有職缺原文但還沒有解析頁（流程停在 ① 收件）")

    guide = ROOT / "guide.html"
    check_common(guide, parse(guide), guide.read_text(encoding="utf-8"))
    check_index(job_scores)
    check_pii()

    n_jobs = len(job_scores)
    n_res = len(list((ROOT / "resumes").glob("*.html")))
    print(f"檢查範圍：{n_jobs} 個職缺解析頁、{n_res} 個客製化履歷頁、首頁、說明頁")
    if errors:
        print(f"\n❌ 發現 {len(errors)} 個問題：")
        for e in errors:
            print("  -", e)
        return 1
    print("✅ ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
