# Green Talk, Brown Silence

### Measuring the structure of environmental disclosure in 199 Chinese annual reports

**English** | **[中文](README.md)**

> **TL;DR** — I scraped and text-mined **199 annual reports** from the official CNINFO
> disclosure platform. Half of Chinese listed firms never mention carbon; only **2%** publish
> a number. Environmental disclosure is not uniformly greenwashed — it is **sharply
> stratified by industry**, and the sectors that stay quietest are the ones with the most to
> gain from appearing green.

**[📄 Read the working paper →](report/working_paper.md)**　·　**[🔧 Technical manual →](report/technical_manual.md)**

---

## Key findings

| Finding | Number |
|---|---|
| Firms that **never mention carbon** | **97 / 199 (49%)** |
| Firms publishing a **quantified** emissions figure | **4 / 199 (2%)** |
| Firms using green language with **zero** carbon data | **97 / 199 (49%)** |
| Carbon mentions — Energy & Utilities (mean) | **8.2** |
| Carbon mentions — Healthcare & Pharma (mean) | **0.5** |
| Carbon mentions — Agriculture (mean) | **0.0** |

### Fig 1 — Disclosure is stratified, not uniform
![industry](figures/fig1_industry.png)

### Fig 2 — Rhetoric vs evidence
![gap](figures/fig2_gap.png)

### Fig 3 — Coverage and silence
![coverage](figures/fig3_coverage.png)

---

## Why this matters

Climate disclosure rules are tightening worldwide — the EU's CSRD, the UK FCA
anti-greenwashing rule, the ISSB-aligned requirements being phased in by the Hong Kong
Exchange. All of them assume firms *have* environmental data and that regulation's job is
to make them reveal it truthfully.

This project tests that assumption. The answer: **the binding constraint is not dishonesty
but absence.** Most Chinese annual reports contain no environmental data at all — so the
common "greenwashing" framing misdescribes the problem.

---

## Pipeline

| Step | Script | What it does | Runtime |
|---|---|---|---|
| 1 | `src/01_harvest.py` | Harvest the annual-report index from the CNINFO API | ~15 s |
| 2 | `src/02b_extract_full.py` | Download PDFs in parallel, extract full text, score disclosure | ~10 min |
| 3 | `src/04_industry.py` | Attach official industry labels (Eastmoney `f127`) | ~30 s |
| 4 | `src/03_analyze.py` | Aggregate by industry, generate figures + summary JSON | ~5 s |

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/01_harvest.py 14      # 14 pages -> 199 firms
python src/02b_extract_full.py   # parallel download + scoring
python src/04_industry.py        # official industry labels
python src/03_analyze.py         # figures + summary
```

**Total runtime ≈ 12 minutes.** Requires Python 3.9+ and a network connection to
`cninfo.com.cn` (the Eastmoney industry endpoint is reached via `push2delay`).

---

## Method

Each report's **full text** is scored on three keyword families:

| Category | Terms | Interpretation |
|---|---|---|
| **Hard disclosure** | 碳排放, 碳达峰, 碳中和, 温室气体, 碳强度, 碳配额 | Concrete carbon measurement |
| **Action** | 减排, 节能, 污染治理, 清洁生产, 循环经济 | Operational activity |
| **Soft rhetoric** | 绿色发展, 生态文明, 绿水青山, 低碳生活 | Aspirational language |

A regex pass additionally extracts **quantified** figures (`碳排放量约 X 吨`) to separate
reports that state numbers from those that only use words.

### Text scope matters

Scanning only the first 25 pages of each report reported **66%** zero-carbon; full-text
extraction reported **49%**. All headline figures use full-text extraction. This gap is
itself a methodological finding worth noting for anyone doing similar work.

---

## Repository layout

```
greenwash-disclosure/
├── src/
│   ├── 01_harvest.py           # CNINFO disclosure index
│   ├── 02b_extract_full.py     # parallel PDF download + full-text scoring
│   ├── 03_analyze.py           # industry aggregation + figures
│   └── 04_industry.py          # official industry labels
├── data/
│   ├── raw/                    # harvested index
│   └── processed/              # per-firm scores, industry labels, summary
├── figures/                    # output charts
├── report/
│   ├── working_paper.md        # the write-up
│   └── technical_manual.md     # implementation documentation
├── README.md                   # Chinese (default)
├── README.en.md                # this file
├── LICENSE                     # MIT
└── requirements.txt
```

## Data source & ethics

All data is **public regulatory disclosure** from CNINFO (`www.cninfo.com.cn`), the
designated disclosure platform for Chinese listed companies. No personal data is collected.
Raw PDFs are **not redistributed** — `02b_extract_full.py` re-downloads them from the
official source, keeping the work reproducible without re-hosting copyrighted filings.
The harvester paces its requests (0.3 s between index pages) out of courtesy to the public
endpoint.

## Limitations

- Keyword frequency is a **proxy**, not a semantic measure of disclosure quality.
- 31 firms (16%) could not be assigned an official industry label (`Other`).
- One filing season is covered; no time-series or causal claims are made.
- Only 4 firms state quantified emissions — too few for statistical inference.

## License

MIT — see [LICENSE](LICENSE).

---

**Author: Jiawei Hong (洪嘉伟)** · 2026-09-10
