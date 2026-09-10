# Green Talk, Brown Silence
### What 199 Chinese annual reports reveal about the structure of environmental disclosure

**洪嘉伟 (Jiawei Hong) · 2026-09-10 · Working paper**

---

## Abstract

Chinese listed companies face growing pressure to disclose environmental information, yet the
content of that disclosure remains largely voluntary in practice. This paper asks a simple
question: **when firms talk about the environment, do they talk about it in the same way?**

Using a purpose-built text pipeline, I collected **199 annual reports** filed on the official
CNINFO disclosure platform (巨潮资讯网) during the FY2025 reporting season, extracted the full
text of each filing, and scored every report on three dimensions — *hard* carbon terms,
*action* terms, and *soft* rhetorical language.

Three findings emerge:

1. **Disclosure is sparse.** 49% of firms never mention carbon at all, and only **2% (4 firms)**
   provide a quantified emissions figure. The modal Chinese annual report contains no
   environmental data whatsoever.
2. **Disclosure is stratified, not uniformly greenwashed.** The interesting variation is
   *between* industries, not within them. Energy & Utilities firms mention carbon **8.2 times**
   on average; Healthcare & Pharma firms mention it **0.5 times**. Agriculture is silent
   in 100% of sampled reports.
3. **Rhetoric fills the space where data is missing.** 49% of firms use green vocabulary
   while providing zero carbon data. For Consumer and Healthcare firms, soft language
   outnumbers hard disclosure by roughly 20 to 1.

The implication is that the common framing of "greenwashing" — firms exaggerating real
performance — misdescribes the Chinese case. Most firms are not overstating: they are
**silent**, and where they do speak, they speak in the register of aspiration rather than
measurement.

---

## 1. Motivation

Climate disclosure regimes are tightening worldwide — the EU's CSRD, the UK FCA's
anti-greenwashing rule, and the ISSB-aligned requirements now being phased in by the
Hong Kong Exchange. Each of these regimes assumes that firms possess the underlying
data and that the regulatory task is to make them reveal it truthfully.

That assumption deserves testing. Before asking whether disclosure is *truthful*, we should
ask whether it is *substantive* — whether there is anything to be truthful about. This paper
measures the baseline: how much quantitative environmental information actually appears in
Chinese corporate filings.

## 2. Data

| | |
|---|---|
| **Source** | CNINFO (巨潮资讯网), the designated disclosure platform for Chinese listed firms |
| **Sample** | 199 annual reports, FY2025 reporting season (April 2026 filing window) |
| **Access** | Public regulatory filings, retrieved via the platform's announcement API |
| **Text extracted** | Full document, parsed with `pdfplumber` |
| **Industry labels** | Official Eastmoney industry classification (`f127`), retrieved for 191/199 firms (96%) |

The sample is the complete set of annual reports filed in the April 2026 window after
removing duplicate, summary, English-language, and corrected filings. Raw PDFs are **not**
redistributed — the pipeline re-downloads them from the official source, keeping the work
reproducible without re-hosting copyrighted filings.

## 3. Method

Each report's full text is scanned for three keyword families:

| Category | Terms | Interpretation |
|---|---|---|
| **Hard disclosure** | 碳排放, 碳达峰, 碳中和, 温室气体, 碳强度, 碳配额, 碳足迹 | Concrete carbon measurement / commitment |
| **Action terms** | 减排, 节能, 环保投入, 污染治理, 清洁生产, 循环经济 | Operational environmental activity |
| **Soft rhetoric** | 绿色发展, 可持续发展, 生态文明, 绿水青山, 低碳生活, 环保理念 | Aspirational language |

Counts are aggregated per firm and summarised by industry. A separate regular expression
pass attempts to extract *quantified* emissions figures
(`碳排放量约 X 吨`, `减排量 X 吨`) to distinguish reports that state numbers from those
that only use words.

This is deliberately a **transparent, reproducible proxy**, not a semantic measure.
Keyword frequency cannot distinguish a firm that discusses emissions in depth from one that
repeats a boilerplate phrase. The virtue of the approach is that any reader can re-run it and
inspect every count.

## 4. Results

### 4.1 The baseline: silence, not exaggeration

| Measure | Result |
|---|---|
| Firms with **zero** carbon mentions | 97 / 199 (**48.7%**) |
| Median carbon term count | **1** |
| Firms stating a **quantified** emissions figure | 4 / 199 (**2.0%**) |
| Firms using green language with **zero** carbon data | 97 / 199 (**48.7%**) |

*See `figures/fig3_coverage.png`.*

### 4.2 Stratification by industry

| Industry | N | Carbon terms (mean) | Soft rhetoric (mean) | Zero-carbon rate |
|---|---|---|---|---|
| Energy & Utilities | 22 | **8.2** | 14.5 | 14% |
| Financials | 6 | 6.3 | 15.0 | 50% |
| Steel & Materials | 4 | 3.8 | 7.8 | 25% |
| Real Estate & Construction | 13 | 3.4 | 10.2 | 54% |
| Chemicals | 20 | 2.9 | 12.4 | 35% |
| Industrials | 18 | 2.4 | 9.6 | 50% |
| TMT & Electronics | 37 | 1.7 | 10.0 | 51% |
| Consumer | 26 | 0.8 | 9.7 | 65% |
| Healthcare & Pharma | 19 | 0.5 | 9.8 | 68% |
| Agriculture | 3 | 0.0 | 5.7 | 100% |

*See `figures/fig1_industry.png`.*

The spread between the top and bottom sector is a factor of **more than sixteen**. Disclosure
intensity tracks a firm's direct exposure to carbon regulation and physical transition risk —
the sectors that are *regulated* disclose; the sectors that are *not* stay silent.

### 4.3 Rhetoric versus evidence

*See `figures/fig2_gap.png`.* Plotting soft rhetoric against hard disclosure shows a dense
cluster of firms near the origin — low on both axes — and a wide shaded region above the
45° line where green language substantially exceeds carbon data. The firms furthest above
the line are not the heavy emitters; they are consumer-facing and healthcare firms with
little direct carbon exposure but strong reputational incentives to appear green.

## 5. Discussion

Two readings of these results are possible.

The **optimistic** reading is that the system is working as intended: firms with material
carbon exposure disclose, and firms without it do not, which is exactly what a
materiality-based disclosure regime should produce.

The **sceptical** reading is that the firms with the strongest incentive to burnish their
image — consumer brands selling to environmentally conscious customers — are precisely the
ones whose green language most exceeds their green data. Disclosure here may function as
marketing rather than accountability.

Both readings are consistent with the data, and distinguishing them requires matching
disclosure to actual emissions — which the 2% quantification rate makes difficult. That
constraint is itself the central finding: **the binding problem in Chinese environmental
disclosure is not dishonesty but absence.** Regulation that presumes the existence of
reportable data will underperform until measurement is mandatory.

## 6. Limitations

- Keyword frequency is a **proxy**, not a semantic measure of disclosure quality.
- 31 firms (16%) could not be assigned an official industry label and are reported as `Other`.
- The sample covers one filing season; no time-series or causal claims are made.
- Reading the first *N* pages versus the full document changes measured disclosure
  materially — a 25-page scan reported 66% zero-carbon, while the full-text scan reported
  49%. All headline figures in this paper use **full-text** extraction.
- The four quantified emissions figures are too few for statistical analysis and are
  reported as a count only.

## 7. Reproducing this work

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/01_harvest.py 14      # harvest ~199 annual-report records
python src/02b_extract_full.py   # download + full-text score  (~10 min)
python src/04_industry.py        # attach official industry labels
python src/03_analyze.py         # aggregate + generate figures
```

Total runtime: approximately **12 minutes** on a single machine.
