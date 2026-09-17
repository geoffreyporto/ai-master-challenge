# Guide of Implementation and Analytical Arsenal — IT Support Redesign

# Implementation Guide and Analytical Arsenal for Challenge 002: Support Redesign (CRISP-DM)

This document consolidates the tools, techniques, and resources to solve **Challenge 002: Support Redesign**, structured under the **CRISP-DM** methodology (see `CRISP-DM-IT-Support-Challenge.md`). The focus is to answer the Director of Operations' three questions — *where are we losing time, what can AI automate, show me it runs* — with verifiable numbers, a measured human–AI automation boundary, and a prototype evaluated on real data.

**The central tension of this challenge:** the README promises "~30K real tickets with operational metrics", but the measured Dataset 1 is **synthetic** (8,469 rows, 100% template placeholders, uniform distributions, 49.3% impossible time intervals), while Dataset 2 is **real but heavily preprocessed** (47,837 rows, lowercased and stopword-stripped). A winning submission turns this into a strength: audit → honest diagnosis → reusable pipeline → classifier with a calibrated abstention boundary → running prototype.

---

## 1. Top 5 Sites for Data Science / NLP Challenges

For practice, similar datasets, and studying published solutions:

1. **Kaggle** (`kaggle.com`) — Both challenge datasets live here; the dataset "Code" tabs contain community notebooks for ticket classification and support EDA.
2. **Hugging Face** (`huggingface.co`) — Datasets, model cards (GLiNER2, GLiFormer, Model2Vec/Potion), and Spaces with runnable demos for text classification and NER.
3. **DrivenData** (`drivendata.org`) — Real-world problems with messy, imbalanced data and ethical constraints; good practice for honest evaluation.
4. **Zindi** (`zindi.africa`) — Business-oriented challenges with noisy data and strong emphasis on reproducible pipelines.
5. **AIcrowd** (`aicrowd.com`) — Corporate and research AI challenges, including NLP and applied ML benchmarks.

---

## 2. Top 5 Reference Implementations (High-Quality, Verifiable)

Instead of unverified notebook links, these are maintained repositories and official guides that directly implement the techniques recommended below:

1. **Community notebooks for Dataset 2**
   *URL:* `https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset/code`
   *Why study:* Existing baselines on the exact corpus — use them to position your macro-F1 honestly (and check they report macro-F1, not only accuracy).
2. **GLiNER2 (Fastino) — schema-driven classification + extraction**
   *URL:* `https://github.com/fastino-ai/GLiNER2`
   *Why study:* One encoder for classification, NER, structured extraction, and relations in a single forward pass — the heavy tier of the router.
3. **Pioneer — fine-tune a GLiNER text classification model**
   *URL:* `https://docs.pioneer.ai/guides/fine-tune-classification.md`
   *Why study:* Hosted LoRA fine-tuning on Dataset 2 (`text` + `label` rows), evaluation jobs, and multi-head inference schemas.
4. **cleanlab — confident learning for label noise**
   *URL:* `https://github.com/cleanlab/cleanlab`
   *Why study:* Finds likely mislabeled tickets in Dataset 2 (e.g. short ambiguous docs) — explains the accuracy ceiling and feeds the "human judgment required" argument.
5. **MAPIE — conformal prediction for scikit-learn models**
   *URL:* `https://github.com/scikit-learn-contrib/MAPIE`
   *Why study:* Prediction sets with statistical coverage guarantees; when the set contains more than one class, the ticket goes to a human. A principled automation boundary.

Supporting: **Model2Vec** (`https://github.com/MinishLab/model2vec`) for the local fast path; **SimPy** (`https://simpy.readthedocs.io`) for queue simulation.

---

## 3. The 3 Best Statistical Techniques (CRISP-DM Phases 2 and 3)

The challenge asks for concrete numbers about bottlenecks, satisfaction, and waste — but the operational dataset is synthetic. These techniques make the diagnosis rigorous either way.

1. **Data Authenticity Audit (uniformity, independence, and consistency tests):**
    - **Application:** Regex scan for `{placeholders}`; χ² goodness-of-fit against uniform for every categorical; χ² independence for fields that must be related (`Ticket Subject` × `Ticket Type`); temporal consistency (`Time to Resolution` < `First Response Time`); uniqueness of resolution texts; email domain check.
    - **Measured result:** Dataset 1 fails every authenticity check (placeholders 100%, χ² uniform p = 0.11–0.72, Subject×Type p = 0.98, 49.3% negative intervals). Dataset 2 passes (0 placeholders, realistic class imbalance, 0 duplicates).
2. **Hypothesis Testing with Effect Sizes and Power Analysis:**
    - **Application:** Kruskal-Wallis for handling time and CSAT by channel/priority/type (with ε² effect size); ordinal logistic regression for CSAT drivers; permutation importance from gradient boosting; **minimum detectable effect** to prove null results are not due to small samples.
    - **Measured result:** all p = 0.28–0.92; Spearman(hours, CSAT) ρ = 0.02; with ≥ 674 closed tickets per channel and SD 1.41, the minimum detectable CSAT difference is **≈ 0.21 points** → "no detectable driver" is defensible.
3. **Queueing Model / Discrete-Event Simulation (Erlang C or SimPy):**
    - **Application:** Because the file's times cannot quantify waste, model the operation from the README scenario (~30,000 tickets/year ≈ 2,500/month) with explicit parameters (arrival rate by channel, handling time distribution, agents, SLA). Simulate "as-is" vs "with AI triage" (triage time removed for auto-routed tickets, fewer misroute re-queues) to estimate **waiting hours, SLA breaches, and agent hours saved**.
    - **Why it wins:** turns "how much are we wasting?" into a transparent, adjustable scenario the Director can feed with real numbers — instead of inventing figures from synthetic timestamps.

---

## 4. The 5 Best Machine Learning Techniques (CRISP-DM Phase 4)

The challenge warns: generic "use NLP" is weak; "8 classes at X% with embeddings + zero-shot" is specific. And accuracy alone is misleading on imbalanced classes.

1. **TF-IDF (1–2 grams) + Logistic Regression — the honest baseline:**
    - **Application:** Stratified 80/20 split, `class_weight="balanced"`, macro-F1 + per-class F1. Every other model must beat it.
    - **Measured result:** accuracy **0.866**, macro-F1 **0.868** (weakest: Administrative rights F1 0.786; strongest: Purchase 0.920).
2. **GLiNER2 LoRA Fine-Tuning on Pioneer (multi-head):**
    - **Application:** Upload Dataset 2 train split (`text`, `label`), train `fastino/gliner2-base-v1` with LoRA, evaluate on the hold-out, and serve with a multi-head schema: `topic_group` classification + `urgency` classification + `entities` (component, software, error symptom) in one call.
    - **Why:** zero-shot may underperform on stopword-stripped text; fine-tuning recovers accuracy while adding extraction that TF-IDF cannot provide.
3. **Model2Vec Static Embeddings + Linear Head (two-tier cascade):**
    - **Application:** Train a linear head on Potion embeddings; serve in Rust (`model2vec-rs`) as the fast path. Only tickets below threshold go to Pioneer GLiNER2.
    - **Why:** sub-millisecond, offline, near-zero cost for the confident majority; the same embeddings power similar-ticket retrieval and duplicate detection.
4. **Probability Calibration + Conformal Prediction (selective classification):**
    - **Application:** Isotonic calibration on the validation split; MAPIE prediction sets at a chosen coverage (e.g. 95%). Singleton set + high calibrated score → auto-route; multi-class set → human. Report Expected Calibration Error and the **risk–coverage curve**.
    - **Why:** converts "confidence" into a statistically grounded automation boundary — the direct answer to "automating 100% is a red flag".
5. **Confident Learning for Label Noise (cleanlab):**
    - **Application:** Use out-of-fold predicted probabilities from B0/B1 to rank likely mislabeled tickets; inspect the top 50; retrain with noisy rows removed or down-weighted; compare macro-F1.
    - **Why:** explains the accuracy ceiling, improves training data, and provides concrete examples of tickets that genuinely require human judgment.

---

## 5. The 3 Best Human–AI Decision Techniques (The Hackathon Differentiator)

The Director does not need "a model"; he needs to know **which tickets can safely skip a human** and what that is worth. These techniques define the boundary.

1. **Cost-Sensitive Per-Class Thresholds (Bayes decision rule):**
    - **Application:** Define a misroute cost matrix (e.g. misrouting *Administrative rights* or *Access* = security/authorization risk, high cost; misrouting *Purchase* = low cost; sending to human = fixed triage cost). For each class, choose the threshold that minimizes expected cost on the validation split. High-risk classes may end with threshold = "never auto-route".
    - **Output:** `thresholds.json` consumed by the Rust router; a table "class → auto-route %, precision, expected cost".
2. **Domain-Shift Detection (Dataset 2 → Dataset 1 cross):**
    - **Application:** Score Dataset 1 descriptions (placeholders removed, same normalization) with the Dataset 2 classifier; compare confidence and margin distributions against the Dataset 2 hold-out (Kolmogorov–Smirnov test); optionally a domain classifier (two-sample test) distinguishing the two corpora.
    - **Why:** proves the router **knows when it doesn't know** — consumer-electronics tickets should fall to low confidence / human queue. This is the most meaningful cross between the datasets.
3. **Human-in-the-Loop Active Learning (uncertainty sampling + feedback loop):**
    - **Application:** Tickets in the human queue are the most informative; agents' corrected labels are sent to Pioneer's feedback API (`POST /inferences/:id/feedback`) and periodically used for retraining. Simulate it offline: retrain with the 500 most uncertain hold-out-excluded tickets vs 500 random ones and compare macro-F1 gain.
    - **Why:** shows the automation improves over time **because** humans stay in the loop — not despite them.

---

## 6. Execution Plan: CRISP-DM Mapping (Step by Step)

Technical roadmap to deliver the solution within the 4–6 hour budget.

### Phase 1: Business Understanding

- **Objective:** Answer the Director's three questions with numbers and a running system.
- **Action:** Define success not as *accuracy* but as **auto-routed coverage at target precision** and **net agent hours saved per month** (after API cost). The report's first table answers: "Where do we lose time, what do we automate, how much do we save?"
- **Action:** Smoke-test Pioneer (catalog + one inference) and record available model IDs; confirm whether GLiFormer is available in the workspace.

### Phase 2: Data Understanding

- **Action 1 (Authenticity Audit):** Run the §3.1 checks on both datasets; write the verdict table first.
- **Action 2 (Diagnosis Tests):**
    - Handling interval and CSAT by `Ticket Channel × Ticket Priority × Ticket Type` (heatmap + Kruskal-Wallis + ε²).
    - Ordinal logistic regression and permutation importance for CSAT.
    - Power analysis (minimum detectable effect).
    - Hypothesis to validate: *if no segment differs beyond the detectable effect, the file carries no real bottleneck signal* → report it.
- **Action 3 (Text Understanding):** Dataset 2 class distribution, text length per class, top tokens per class, short-document share.

### Phase 3: Data Preparation

- **Dataset 1:** parse timestamps, `handling_hours`, `negative_interval_flag`, strip `{placeholders}`, segment key.
- **Dataset 2:** normalized labels, stratified train/val/test (70/10/20, seed 42), Pioneer upload files.
- **Shared normalization function** (lowercase, remove digits/punctuation) used by training, evaluation, and the Rust router.
- **Scenario inputs:** `assumptions.yaml` (monthly volume from README scenario, channel mix, handling-time distribution, triage minutes, loaded cost/hour, SLA).
- **Label noise:** cleanlab pass on out-of-fold probabilities.

### Phase 4: Modeling

- **Benchmark (Dataset 2):** B0 TF-IDF+LR, B1 Model2Vec+head, B2/B3 GLiNER2 zero-shot (Pioneer, `store:false`), B4 GLiNER2 LoRA fine-tuned (Pioneer), B5 GLiFormer (if available), B6 classification-as-NER.
- **Decision layer:** isotonic calibration, MAPIE prediction sets, cost-sensitive per-class thresholds.
- **Operational model:** SimPy/Erlang C scenario "as-is" vs "with AI triage" using measured coverage and misroute rates.

### Phase 5: Evaluation

- **Technical evaluation:** macro-F1, per-class F1, ECE, risk–coverage curve, latency p50/p95, token cost — all on the untouched hold-out, **through the running router**.
- **Business evaluation (Director gate):**
    - Coverage at target precision and human-queue share.
    - Net hours/month and cost saved (with assumptions shown).
    - Domain-shift result on Dataset 1.
    - Validate: does each claim cite a metric and the dataset/split it came from? If not, *loop back to Phase 3*.

### Phase 6: Deployment (Final Report and Prototype)

- **Deliverable 1 — Diagnosis report (Markdown):**
    - **Data verdict:** "Dataset 1 is synthetic; here is the evidence; here is the pipeline ready for real data."
    - **Where time is lost (scenario):** triage and misroute re-queues quantified via simulation with explicit assumptions.
- **Deliverable 2 — Automation proposal:** automate / do not automate (with real ticket examples) / operational flow diagram / thresholds table.
- **Deliverable 3 — Prototype:** Rust router (Model2Vec fast path + Pioneer GLiNER2 heavy tier + human queue fallback), similar-ticket suggestions, dashboard with coverage–precision and live routing.
- **Deliverable 4 — Process log (AI usage):** prompts and transcripts, decisions with evidence, experiment log, Pioneer job IDs, and AI mistakes caught (e.g. assuming the README's "30K real tickets" without checking).

---

*Golden tip for the hackathon:* launch the **Pioneer LoRA training job in the first 45 minutes**. It runs in the background while you do the authenticity audit and diagnosis, so the fine-tuned model is ready when you reach threshold selection and the prototype.

---

## 7. Challenge Type

| **Description** | **Prediction** | **Decision (Automation Boundary)** |
| --- | --- | --- |
| Data authenticity audit; proportions and aggregates by channel/priority/type; distributions of CSAT and handling time; visualizations | Mapping ticket text (X) to topic, urgency, and extracted fields (y) with calibrated confidence | Using calibrated uncertainty and misroute costs to decide, per ticket, whether AI acts or a human decides — and estimating the operational value of that policy |

## 8. Challenge Examples

| **Description** | **Prediction** | **Decision (Automation Boundary)** |
| --- | --- | --- |
| What share of tickets are Critical, and do Critical tickets take longer to resolve by channel? | What is the probability that a new ticket belongs to "Access" vs "Administrative rights"? | Should this ticket be auto-routed, or does its uncertainty or risk class require a human — and how many agent hours per month does that policy save? |

## 9. Selective Classification Procedure (Automation Boundary)

| **1) Train and calibrate** | **2) Measure risk vs coverage** | **3) Final routing policy** |
| --- | --- | --- |
| Train the classifier on the train split. Calibrate scores (isotonic) and fit conformal prediction sets on the validation split. | For each class, sweep thresholds and compute precision (risk) against the share of tickets auto-routed (coverage), weighting errors by the misroute cost matrix. | Auto-route only singleton, high-confidence, low-risk predictions; send the rest to humans. Verify the chosen policy once on the untouched hold-out and report coverage, precision, and human-queue share. |

## 10. Quality Criteria Compliance (README "Critérios de qualidade")

| # | Criterion | Techniques in this guide that satisfy it |
|---|---|---|
| 1 | Used both datasets (cross)? | §5.2 domain-shift cross; Dataset 2 model scores Dataset 1 |
| 2 | Diagnosis with concrete numbers? | §3.1 audit, §3.2 tests + power analysis, §3.3 simulation with explicit assumptions |
| 3 | Realistic automation (not 100%)? | §4.4 conformal/calibration, §5.1 cost-sensitive thresholds, §9 procedure |
| 4 | Knows where humans are irreplaceable? | §4.5 label-noise examples, §5.1 high-risk classes, §5.3 human-in-the-loop |
| 5 | Prototype on real data, not cherry-picked? | Phase 5: full hold-out and all Dataset 1 tickets through the running router |
