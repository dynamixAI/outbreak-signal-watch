#!/usr/bin/env python3
"""
verify_sources.py - check outside claims against the original documents, not summaries.

1. BSAC study (PMC12556646): print table rows mentioning erythromycin / penicillin.
2. ESPAUR 2024-25 extended summary: find every mention of Streptococcus pneumoniae.
Saves copies of both originals in sources/.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PROJECT = Path(__file__).resolve().parent.parent
SOURCES = PROJECT / "sources"
SOURCES.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (independent research)"}


def cell_text(el):
    return " ".join("".join(el.itertext()).split())


# ---------- 1. The BSAC research paper ----------
print("=" * 70)
print("1. BSAC study: tables mentioning erythromycin or penicillin")
print("=" * 70)
urls = ["https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12556646/fullTextXML",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=12556646"]
xml = None
for url in urls:
    r = requests.get(url, headers=HEADERS, timeout=60)
    if r.ok and "<table" in r.text:
        xml, source_url = r.text, url
        break
    print(f"  (no tables from {url}, status {r.status_code})")

if xml:
    (SOURCES / "bsac_pmc12556646.xml").write_text(xml)
    print(f"  Source: {source_url}\n  Saved: sources/bsac_pmc12556646.xml\n")
    root = ET.fromstring(xml)
    for wrap in root.iter("table-wrap"):
        label = cell_text(wrap.find("label")) if wrap.find("label") is not None else "Table"
        caption = cell_text(wrap.find("caption")) if wrap.find("caption") is not None else ""
        rows = [[cell_text(c) for c in tr if c.tag in ("td", "th")] for tr in wrap.iter("tr")]
        hits = [r for r in rows if re.search(r"erythro|penicillin|macrolide", " ".join(r), re.I)]
        if not hits:
            continue
        print(f"--- {label}: {caption[:150]}")
        print("  HEADER:", " | ".join(rows[0]))
        for r in hits:
            print("  ", " | ".join(r))
        print()
else:
    print("  Could not download the paper's tables. Open it in a browser instead.")

# ---------- 2. The ESPAUR summary ----------
print("=" * 70)
print("2. ESPAUR 2024-25 extended summary: mentions of Streptococcus pneumoniae")
print("=" * 70)
url = ("https://www.gov.uk/government/publications/english-surveillance-programme-for-antimicrobial-"
       "utilisation-and-resistance-espaur-2024-to-2025-report/espaur-report-2024-to-2025-extended-summary")
r = requests.get(url, headers=HEADERS, timeout=60)
r.raise_for_status()
(SOURCES / "espaur_2024_25_extended_summary.html").write_text(r.text)
text = " ".join(BeautifulSoup(r.text, "html.parser").get_text(" ").split())
print(f"  Source: {url}\n  Saved: sources/espaur_2024_25_extended_summary.html")
print(f"  Document length: {len(text):,} characters\n")

# "Klebsiella pneumoniae" also contains "pneumoniae", so search for the pneumococcus specifically
patterns = [r"Streptococcus pneumoniae", r"S\. ?pneumoniae", r"pneumococc\w*"]
found = False
for p in patterns:
    for m in re.finditer(p, text, re.I):
        found = True
        start, end = max(0, m.start() - 120), min(len(text), m.end() + 120)
        print(f"  [{p}] ...{text[start:end]}...\n")
if not found:
    print("  No mentions of Streptococcus pneumoniae, S. pneumoniae or pneumococcal found.")
print(f"  (For comparison, mentions of 'Klebsiella pneumoniae': {len(re.findall(r'Klebsiella pneumoniae|K\\. ?pneumoniae', text))})")
