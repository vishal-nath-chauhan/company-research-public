#!/usr/bin/env python3
"""Add or replace a company-and-role brief and rebuild the searchable index."""

import argparse
from datetime import date
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
CATALOG = ROOT / "catalog.json"
NOINDEX = '<meta name="robots" content="noindex">'
KEY = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*")


class ReportData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_payload = False
        self.payloads = []

    def handle_starttag(self, tag, attributes):
        if tag == "script" and dict(attributes).get("id") == "company-report-data":
            self.in_payload = True
            self.payloads.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_payload = False

    def handle_data(self, data):
        if self.in_payload:
            self.payloads[-1] += data


def slug(label):
    text = unicodedata.normalize("NFKD", label.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", text.replace("&", " and ")).strip("-")


def index_html(entries):
    rows = "\n".join(
        f'<li><a href="reports/{key}/index.html"> <strong>{escape(entry["company"])}</strong>'
        f'<span>{escape(entry["role"])}</span></a><time>{escape(entry["updated"])}</time></li>'
        for key, entry in entries
    )
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{NOINDEX}
<title>Company Research Reports</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f6f5f0;color:#202b28;font:16px/1.5 system-ui,sans-serif}}
header{{background:#13342c;color:white;padding:44px 22px}}
main,.wrap{{max-width:800px;margin:auto}}
main{{padding:26px 22px 64px}}
h1{{margin:0;font:clamp(36px,7vw,60px)/1.05 Georgia,serif}}
label{{display:block;margin-bottom:6px;font-weight:650}}
input{{width:100%;padding:12px;border:1px solid #9caea4;border-radius:8px;font:inherit}}
ul{{list-style:none;padding:0}}
li{{display:flex;justify-content:space-between;align-items:center;gap:12px;background:white;
padding:14px 18px;margin:8px 0;border:1px solid #dedfd6;border-radius:10px}}
li[hidden]{{display:none}}
a{{color:#14634f;text-decoration:none}}
a:hover{{text-decoration:underline}}
a span{{display:block;color:#202b28}}
time{{color:#52655e;white-space:nowrap;font-size:14px}}
</style>
<header><div class="wrap"><h1>Company Research Reports</h1></div></header>
<main>
<label for="search">Search by company or role</label>
<input id="search" type="search">
<p id="count" role="status">{len(entries)} reports</p>
<ul id="reports">
{rows}
</ul>
</main>
<script>
const search = document.querySelector('#search');
const rows = Array.from(document.querySelectorAll('#reports li'));
const count = document.querySelector('#count');
function filterReports() {{
  const terms = search.value.trim().toLowerCase().split(/\\s+/);
  let matches = 0;
  for (const row of rows) {{
    row.hidden = !terms.every(term => row.textContent.toLowerCase().includes(term));
    if (!row.hidden) matches++;
  }}
  count.textContent = matches + (matches === 1 ? ' report' : ' reports');
}}
search.addEventListener('input', filterReports);
filterReports();
</script>
</html>
"""


def write_if_changed(path, content):
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--company", required=True, help="Canonical hiring employer name")
    parser.add_argument("--role", required=True, help="Canonical role title")
    parser.add_argument("--date", required=True, type=date.fromisoformat, help="Research date (YYYY-MM-DD)")
    parser.add_argument("--existing-key", help="Reuse this catalog key for a verified alias or rename")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {}
    key = args.existing_key or f"{slug(args.company)}/{slug(args.role)}"
    if not KEY.fullmatch(key):
        parser.error("Expected a company/role key made of lowercase ASCII slugs")
    if args.existing_key and key not in catalog:
        parser.error("The existing key was not found in the catalog")

    html = args.report.read_text(encoding="utf-8")
    data = ReportData()
    data.feed(html)
    if len(data.payloads) != 1:
        parser.error("Expected one embedded company-report-data payload")
    payload = json.loads(data.payloads[0])
    if not isinstance(payload, dict) or payload.get("version") != 1 or not all(
        isinstance(payload.get(field), str) and payload[field].strip()
        for field in ("company", "role")
    ):
        parser.error("Expected a populated v1 interview brief")

    if NOINDEX not in html:
        html, inserted = re.subn(
            r"<head\b[^>]*>", lambda match: match[0] + NOINDEX, html, count=1, flags=re.I
        )
        if not inserted:
            parser.error("Expected an HTML head for the noindex directive")

    catalog[key] = dict(company=args.company, role=args.role, updated=args.date.isoformat())
    page = Path("reports") / key / "index.html"
    entries = sorted(catalog.items(), key=lambda item: (item[1]["company"].casefold(), item[1]["role"].casefold()))
    write_if_changed(DOCS / page, html)
    write_if_changed(CATALOG, json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_if_changed(DOCS / "index.html", index_html(entries))
    print(f"docs/{page.as_posix()}")


if __name__ == "__main__":
    main()
