# CRISP-DM Applied to Challenge 002 — IT Support Redesign

## 1. Context

A technology company handles **~30,000 support tickets per year** across email, chat, phone, and social media. The team is overloaded, resolution time has increased, and customer satisfaction has dropped. The Director of Operations asked for three things: **where we are losing time, what can be automated with AI, and proof that it works** ("I don't want just a PowerPoint — I want to see something running").

The challenge tests three skills at once: analytical capability (diagnosis), process thinking (what to automate and what not), and build capability (a working prototype on real data).

**Data available:**

| Dataset | File | Rows (measured) | Content |
|---|---|---|---|
| Dataset 1 — Customer Support Tickets | `customer_support_tickets.csv` | 8,469 (README says ~30,000) | Operational metrics + description/resolution text |
| Dataset 2 — IT Service Ticket Classification | `all_tickets_processed_improved_v3.csv` | 47,837 | Ticket text + 8-class `Topic_group` label |

This document maps the challenge onto the six CRISP-DM phases so the work is structured, defensible, and reproducible — and so that every claim to the Director answers "how do you know?" with a number.

**Companion documents:**
- `Guide of impementation and Analytic - IT Support.md` — techniques, tools, and step-by-step execution.
- `Multi-Model Classifier (GLiNER2 - GLiFormer) - Technical Stack for Challenge 002 Support Redesign.md` — languages, tooling, Pioneer API, and prototype architecture.

---

## 2. Phase 1 — Business Understanding

| Task | Applied to this challenge |
|---|---|
| Determine Business Objectives | (1) Locate where support time is lost; (2) decide what to automate with AI and what must stay human; (3) demonstrate a working automation with measurable ROI (hours/month, cost) |
| Assess Situation | Two public datasets with different roles: Dataset 1 (operations) and Dataset 2 (labeled text). 4–6 h budget. Access to local compute (Mac Studio, 32 GB) and the Pioneer API (GLiNER2 inference + fine-tuning). Risk: data may not reflect a real operation — must be verified, not assumed |
| Determine Data Mining Goals | (a) Quantify bottlenecks by channel × priority × type; (b) identify drivers of `Customer Satisfaction Rating`; (c) estimate recoverable hours/cost; (d) train an 8-class ticket classifier with calibrated confidence; (e) define the confidence threshold that separates auto-routing from human triage |
| Produce Project Plan | Data-quality audit → diagnosis → classifier benchmark → threshold/automation boundary → prototype (Rust router + Pioneer GLiNER2) → evaluation on full hold-out → ROI → report + process log |

**Business success criteria:** the Director can read the report and answer: *where is time lost, what gets automated, what stays human, how many hours/month are saved, and is it running?*

**Technical success criteria:**
- Diagnosis backed by statistical tests and effect sizes, not narrative.
- Classifier evaluated on the **full stratified hold-out** (~9.6K tickets) with macro-F1 and calibration — no cherry-picked examples.
- Automation boundary expressed as a measured **coverage vs. precision** trade-off (automating 100% is a red flag).
- Both datasets used, with an explicit cross between them.

---

## 3. Phase 2 — Data Understanding

| Task | Applied to this challenge |
|---|---|
| Collect Initial Data | Load both CSVs; convert to Parquet; confirm schemas (`Ticket ID` unique in Dataset 1; `Document`/`Topic_group` in Dataset 2) |
| Describe Data | Row counts, column types, missingness per `Ticket Status`, class distribution of `Topic_group`, text length distributions |
| Explore Data | First cuts: resolution interval and CSAT by channel/priority/type; status mix (backlog); Dataset 2 vocabulary, top tokens per class, short/ambiguous documents |
| Verify Data Quality | Template placeholders, uniformity (χ²), independence between fields (χ²), temporal consistency (resolution before first response), resolution-text authenticity, duplicate/conflicting labels, label noise |

**Critical check for this challenge — is the operational data real?** It must be tested here, before any diagnosis is written. Measured results on the actual files:

| Finding | Dataset 1 | Dataset 2 |
|---|---|---|
| Template placeholders | `{product_purchased}` in **100%** of descriptions; 156 distinct placeholders | 0 |
| Distributions | Type, status, priority, channel, product, age, CSAT all ≈ uniform (χ² p = 0.11–0.72) | Realistic imbalance (Hardware 28.5% → Administrative rights 3.7%) |
| Field independence | `Ticket Subject` × `Ticket Type` χ² p = 0.98 | — |
| Time fields | Timestamps in a ~27-hour window, not durations; **49.3%** of closed tickets resolved *before* first response | No time fields |
| Resolution text | 100% unique random sentences | — |
| Text form | Templated English | Lowercased, no digits/punctuation, stopword-stripped |
| Verdict | **Synthetic** | **Real, heavily preprocessed** |
| Learnability | Bottleneck/CSAT tests all non-significant (p = 0.28–0.92) | TF-IDF + LR baseline: accuracy **0.866**, macro-F1 **0.868** |

**Power check (so null results are credible):** closed tickets per channel ≥ 674 and CSAT SD ≈ 1.41, so the analysis can detect a between-channel CSAT difference of **≈ 0.21 points** (α = 0.05, power = 0.80). Observed channel means differ by at most 0.13 and are not significant → "no detectable driver" is a defensible conclusion, not a lack of data.

---

## 4. Phase 3 — Data Preparation

| Task | Applied to this challenge |
|---|---|
| Select Data | Dataset 1: closed tickets for time/CSAT tests, all tickets for status mix and routing demo. Dataset 2: all rows for classification |
| Clean Data | Dataset 1: parse timestamps; compute `handling_hours = Time to Resolution − First Response Time`; flag negative intervals; strip `{placeholders}` before scoring text. Dataset 2: verify no duplicates; flag very short documents (< 5 words) as low-information |
| Construct Data | Dataset 1: `is_closed`, `has_rating`, `negative_interval_flag`, channel × priority × type segment key. Dataset 2: normalized label names (`"administrative rights"`), `doc_length`, stratified **train / validation / test** split (70/10/20, fixed seed); label-noise candidates (cleanlab) |
| Integrate Data | **The cross:** apply the Dataset 2 classifier to Dataset 1 descriptions → `predicted_topic`, `confidence`, `margin` joined to each Dataset 1 ticket |
| Format Data | Parquet tables: `d1_tickets_clean`, `d1_segments`, `d2_train`, `d2_val`, `d2_test`, `d1_scored`; Pioneer upload files (`text`, `label`); `assumptions.yaml` for the ROI scenario |

**Train/serve consistency is mandatory:** any text sent to the router must receive the same normalization as Dataset 2 (lowercase, remove digits/punctuation). Otherwise measured accuracy will not hold in the prototype.

**This is the highest-leverage phase for the cross-dataset requirement** — without a shared normalization and a scored Dataset 1 table, "using both datasets" stays superficial.

---

## 5. Phase 4 — Modeling

| Task | Applied to this challenge |
|---|---|
| Select Modeling Technique | **Descriptive:** segment statistics with Kruskal-Wallis, ordinal logistic regression, permutation importance. **Predictive:** benchmark matrix — TF-IDF + LR (B0), Model2Vec + linear head (B1), GLiNER2 zero-shot base/large on Pioneer (B2/B3), GLiNER2 LoRA fine-tuned on Pioneer (B4), GLiFormer if available (B5), classification-as-NER (B6). **Decision:** calibration + selective classification (abstain below threshold) |
| Generate Test Design | Stratified hold-out never touched during training; validation split for calibration and thresholds; macro-F1 (imbalanced classes), per-class F1, Expected Calibration Error, risk–coverage curve, latency p50/p95, token cost |
| Build Model | Train B0/B1 locally; launch Pioneer LoRA job for B4; calibrate scores (isotonic); select per-class thresholds for target precision (e.g. ≥ 0.95); build two-tier cascade (fast local → Pioneer heavy tier → human) |
| Assess Model | Does any model beat B0? Is confidence calibrated? What share of tickets can be auto-routed at the target precision? Which classes never reach it (→ always human)? How does confidence drop on Dataset 1 text (domain shift)? |

**Value weighting reminder:** a misrouted "Administrative rights" or access ticket (security/authorization risk) costs more than a misrouted "Purchase" ticket. Thresholds are **per class and cost-sensitive**, not one global number.

---

## 6. Phase 5 — Evaluation

| Task | Applied to this challenge |
|---|---|
| Evaluate Results | Does the output answer the Director's three questions? (1) Where time is lost — with an honest data-quality verdict and a reusable pipeline; (2) what to automate / not automate — backed by coverage–precision numbers and real ticket examples; (3) is it running — prototype metrics on the full hold-out |
| Review Process | Correlation vs. causation flagged; null results supported by power analysis; no accuracy claim without a hold-out; no ROI figure without explicit assumptions |
| Determine Next Steps | Core report and prototype vs. nice-to-haves (dashboard polish, extra GLiNER2 variants, duplicate detection, suggested replies). List what real data the company must provide to replace the synthetic diagnosis |

**Gate before writing the report:** every insight must answer "how do you know?" with (a) a test statistic or metric and (b) the dataset and split it came from.

---

## 7. Phase 6 — Deployment

| Task | Applied to this challenge |
|---|---|
| Plan Deployment | Rust router (axum) with Model2Vec fast path, Pioneer GLiNER2 heavy tier, human queue fallback; dashboard (marimo/Streamlit) for the Director; report in Markdown |
| Plan Monitoring & Maintenance | Track weekly: auto-route coverage, precision on audited samples, human-queue share, confidence drift, per-class misroutes; feed agent corrections to Pioneer feedback API for retraining; recalibrate thresholds monthly |
| Produce Final Report | Data-quality verdict → diagnosis → automation proposal (automate / don't / flow) → prototype evidence → ROI (hours/month, net of API cost) → risks and next steps |
| Review Project | Process log: prompts and AI transcripts, decisions with evidence, experiment log, Pioneer job IDs, AI mistakes caught |

---

## 8. Non-Linear Reminders for This Project

- If Data Understanding (Phase 2) shows Dataset 1 is synthetic, **loop back to Business Understanding**: reframe Deliverable 1 as an audit + reusable diagnosis pipeline + scenario model, and state it explicitly to the Director rather than presenting noise as insight.
- If Modeling (Phase 4) shows zero-shot GLiNER2 underperforms TF-IDF on preprocessed text, **loop back to Data Preparation**: test label wording, normalization, and fine-tuning instead of forcing zero-shot into the prototype.
- If Evaluation (Phase 5) finds the auto-routing coverage too low at the target precision, **loop back to Modeling**: revisit per-class thresholds, the cascade, or label noise — do not lower the precision target silently.
- If the Dataset 1 cross produces mostly low-confidence predictions, **treat it as a finding** (domain shift) that justifies human review and domain-specific retraining — not as a failure to hide.

---

## 9. Deliverable Checklist Mapped to Challenge Requirements

| Challenge requirement | CRISP-DM phase it comes from |
|---|---|
| 1. Operational diagnosis — bottlenecks, satisfaction drivers, waste in hours/cost | Data Understanding (audit) + Modeling (descriptive) + Evaluation |
| 2. AI automation proposal — what to automate, what not, operational flow | Modeling (benchmark + thresholds) → Evaluation |
| 3. Functional prototype (differential) | Modeling → Deployment |
| 4. Process log of AI usage | Deployment → Review Project |

---

## 10. Quality Criteria Compliance Matrix (README "Critérios de qualidade")

| # | Quality criterion | How this plan satisfies it | Evidence artifact |
|---|---|---|---|
| 1 | **Used both datasets?** (metrics + text; the power is in the cross) | Dataset 2 trains/calibrates the classifier; Dataset 1 is audited, diagnosed, and scored by the classifier (`d1_scored`), revealing domain shift and routing mix | `d1_scored.parquet`, confidence histogram, cross section of report |
| 2 | **Does the diagnosis have concrete numbers?** | χ² and Kruskal-Wallis p-values, effect sizes, power analysis (MDE ≈ 0.21 CSAT points), 49.3% impossible intervals, scenario hours/cost from `assumptions.yaml` | `reports/diagnosis.md`, notebooks |
| 3 | **Is the automation proposal realistic?** (100% is a red flag) | Per-class thresholds from coverage–precision curves; explicit human queue share; high-risk classes always human | `thresholds.json`, risk–coverage plot |
| 4 | **Distinguishes where AI helps vs. where humans are irreplaceable?** | "Do not automate" list justified with real ticket examples (ambiguous/short docs, Miscellaneous, Administrative rights, Critical priority, billing disputes, outbound replies) | `reports/proposal.md` |
| 5 | **Prototype works on real data, not 3 cherry-picked examples?** | Full ~9.6K hold-out and all 8,469 Dataset 1 descriptions processed through the running API; latency, coverage, precision, cost reported | Router logs, evaluation JSON, dashboard |
