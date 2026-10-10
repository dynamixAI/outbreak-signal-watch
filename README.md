# Outbreak Signal Watch

> **Status: In progress.** Pipeline, scoring and first finding complete; regional scan and dashboard next.

A Python pipeline that scans **every disease in the UKHSA public data dashboard API**, works out what is normal for each one at this time of year, and ranks them by how unusual they are right now. The aim is to surface signals that **haven't been publicly flagged**, not to repeat what is already in the news.

## Why this exists

Large surveillance systems watch headline numbers closely. Signals tend to slip through in quieter places: a slow rise that never looks alarming month to month, a region hidden inside a national average, or a disease with too little public data to judge. This project looks in those places.

It started from the 2026 national *Salmonella* Enteritidis outbreak ([LSHTM](https://www.lshtm.ac.uk/newsevents/news/2026/rapid-reaction-uk-declares-national-outbreak-salmonella-enteritidis)). One early finding: **Salmonella is not in the public UKHSA API at all**, so a tool built on this data could not have detected it. That gap is part of the story.

## First finding: rising macrolide resistance in pneumococcal bloodstream infections

| Period | Macrolide / erythromycin resistance | Source |
|---|---|---|
| 2014–19 (pre-pandemic) | 5.9% | BSAC Resistance Surveillance Project, Table 2 ([paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12556646/)) |
| 2022 | 5.6% | UKHSA API |
| 2023 | 6.5% | UKHSA API |
| 2024 | 7.5% | UKHSA API |
| 2025 | 8.9% | UKHSA API |
| **2026 (Jan–Jul)** | **10.1%** | UKHSA API |

Resistance has risen every year since 2022 and is now about **1.7 times the pre-pandemic level**. Testing volumes were stable from 2024 to 2026, so the rise is not explained by more testing. It is **not mentioned in the summary of UKHSA's latest ESPAUR report** (2024–25), checked by full-text search (`scripts/verify_sources.py`).

**Caveats:** BSAC is a sample of UK and Ireland labs and tested erythromycin; UKHSA covers almost all English labs and counts erythromycin, azithromycin or clarithromycin. UKHSA values are three-month rolling averages. The data shows *that* resistance is rising, not *why*. Penicillin resistance is not compared, because the two sources define resistance differently.

## How it works

| Step | Script | What it does |
|---|---|---|
| 1. Catalogue | `scripts/build_inventory.py` | Walks the API's links to list all 139 England-level metrics across 37 diseases |
| 2. Download | `scripts/download_ukhsa.py` | Downloads 105 metrics (excluding COVID-19 and yearly data), following pagination (365 rows max per page) and checking row counts against the API's total |
| 3. Profile | `scripts/profile_raw.py` | Works out frequency, years of history, and how each measure is split into groups |
| 4. Audit | `scripts/audit_duplicates.py` | Checks every raw row for duplicate dates |
| 5. Clean | `scripts/clean_ukhsa.py` | Picks the correct "total" row for each measure, attaches UKHSA baselines, and resolves duplicates with a logged rule |
| 6. Score | `scripts/score_signals.py` | Scores the latest value of every series against what is normal |
| 7. Verify | `scripts/verify_sources.py` | Checks outside claims against the original documents |

### Scoring method

| Group | Series | Method |
|---|---|---|
| **A** (4+ years of history) | 42 | z-score against the same time of year in previous years (±2 weeks or ±1 month), excluding 2020–21, needing at least 3 past years. **SIGNAL** if the last two points are both 2+ standard deviations above normal. |
| **B** (UKHSA publishes a baseline) | 9 | Ratio to UKHSA's own expected level. **SIGNAL** if 1.5× or more for two weeks running. |
| **C** (short history, no baseline) | 11 | Ratio to the same period last year. **Watch** only, never SIGNAL. |

### Data quality findings

| Issue | Handling |
|---|---|
| Salmonella absent from the public API | Documented as a limitation |
| 18 measures labelled without "year" are actually yearly | Detected from date gaps; excluded from early warning |
| 54 measures split by age, sex, onset type or antibiotic | Correct total chosen per type; **rates and percentages never summed** |
| Inconsistent labels ("healthcare associated" / "healthcare-associated", "0-4" / "00-04") | Avoided by using total rows |
| One conflicting duplicate (flu ICU admissions, 1 Jan 2018) | Averaged and logged in `data/clean/cleaning_log.txt` |
| UKHSA flags reporting delays for measles only | Delayed rows excluded from scoring |

## Validation

| Check | Result |
|---|---|
| Early flu season | Flagged independently (test positivity 2.7× normal; flu-like A&E visits 3.4× UKHSA baseline), matching [UKHSA's 8 October 2026 blog](https://ukhsa.blog.gov.uk/2026/10/08/are-we-seeing-an-early-flu-season-what-we-know-so-far-about-this-years-strains/) |
| Two methods agree | Scarlet fever below normal by both the seasonal method (0.71×) and UKHSA's baseline (0.66×) |
| Near-miss list | *E. coli* third-generation cephalosporin resistance scored just under the alarm line; ESPAUR reports it as increasing |

## Limitations

- England-level data only so far; regional data is available but not yet scanned
- "Not publicly flagged" means not found in public reports; UKHSA may know more internally
- Short-history diseases (group C) can only be compared with last year
- A national count cannot detect an outbreak spread thinly across the country

## Reproduce it

```bash
python3 scripts/build_inventory.py
python3 scripts/download_ukhsa.py
python3 scripts/profile_raw.py
python3 scripts/clean_ukhsa.py
python3 scripts/score_signals.py
python3 scripts/verify_sources.py
```

Requires Python 3 with `requests`, `pandas` and `beautifulsoup4`.

## Data and licence

UKHSA data from the [UKHSA data dashboard API](https://ukhsa-dashboard.data.gov.uk/). Contains public sector information licensed under the Open Government Licence v3.0.

## Next steps

- [x] Catalogue, download, clean and score every public UKHSA measure
- [x] First finding, verified against original sources
- [ ] Regional scan: signals hidden inside national averages
- [ ] Check sudden drops for possible reporting problems
- [ ] Live dashboard

---
*Independent research by Pius Ajamma.*
