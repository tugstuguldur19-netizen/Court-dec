# Жишиг (Jishig): AI analysis of Mongolian court decisions

> *Jishig* (Жишиг) means "precedent / example".

shuukh.mn publishes Mongolian court decisions, but it is slow and search is weak. Jishig
mirrors that corpus, has AI read and structure every decision, and gives lawyers three
things they can't get today:

1. **"What happened to me?" matching.** Describe the facts in plain Mongolian and get
   the most similar past cases, how courts ruled on them, and *why*.
2. **Structured search.** Filter by court, judge, instance, dispute type, cited law
   article, outcome, amount and date. Search by meaning, not only by keywords.
3. **Analytics nobody has.** Judge tendencies, how courts interpret a law article,
   conflicting practice between courts, and trends over time.

The clickable UI prototype is in [`prototype/index.html`](prototype/index.html). It is
a single file with no build step, so you open it in a browser. All data in it is
fictional.

---

## 1. Screens

| Route | Screen | Purpose |
|---|---|---|
| `#/` | **Нүүр (Home)** | A large text box: describe your situation, or search by keyword, law article or case number. Example prompts, recent guiding rulings, trends for the month. |
| `#/match` | **Миний хэрэг (My case)**, the flagship screen | The AI shows what it understood (facts, parties, amount, dates, evidence you have or lack), then asks clarifying questions. Then: outcome distribution across similar cases, key numbers (share of the claim awarded, duration, appeal rate, court fee), a limitation-period **risk warning**, and 5 tabs (listed below). |
| `#/search` | **Хайлт (Search)** | Faceted filters with counts. The results page has a live outcome-distribution bar for the current query, AI summaries with highlighted key facts, and law-article chips. |
| `#/case/:id` | **Шийдвэр (Decision reader)** | The full text, colour-coded (facts, court reasoning, law applied). A side panel with a 30-second summary, claim versus award, the appeal chain (1st instance → appeal → supreme), **chat with the decision** (answers cite the paragraph they come from), and similar decisions. |
| `#/judge` | **Шүүгч (Judge profile)** | Volume, average duration, reversal rate on appeal, win rate by dispute type compared with the court average, AI-described tendencies, most-cited articles, recent decisions. |
| `#/law` | **Хууль (Law article explorer)** | Example: Civil Code 281.1. Citations per year, articles cited together with it, AI **interpretation clusters** (how courts actually read the article), and **conflicting practice** shown side by side. |
| `#/trends` | **Тойм (Trends)** | Case volume by type and year, a heatmap of dispute type × year, court workload, AI observations. |
| `#/folder` | **Хавтас (Case folder)** | A workspace: an AI-drafted claim (нэхэмжлэл) or memo built from the most successful similar cases, saved decisions, evidence files, deadline reminders. Export to DOCX. |

### The 5 tabs on "My case"
1. **Similar cases.** Ranked by semantic similarity (%). Each case shows *why* it is similar ("no written contract, bank transfer, acknowledged by SMS").
2. **What made the difference.** Diverging bars: how much each factor moved the win rate, in percentage points. Each factor is marked ✓ (you have it), ✕ (you don't) or ? (unknown). Includes a **conflicting-practice alert**: some courts treat this situation as a loan (Civil Code 281) and others as unjust enrichment (Civil Code 492), so the tool suggests pleading both.
3. **Court arguments.** Quoted reasoning that won, and the counter-arguments that beat plaintiffs, with the number of decisions where each appears.
4. **Courts and timing.** Win rate by court against the average, a histogram of time to decision, and how cases moved through the appeal levels.
5. **Next steps.** A checklist (get the bank statement, notarize the messages, send a written demand) and a "draft the claim" button.

### Design principles
- **Evidence over oracle.** The tool never says "you will win". It says "76% of 147 similar decisions…" and always links to the decisions behind the number.
- **Every AI claim is cited.** Summaries, chat answers and tendencies link to the paragraph or decisions they came from.
- **Show uncertainty.** Confidence on each extracted fact, and clarifying questions instead of silent guesses.
- **Fast.** Instant filtering, pre-computed analytics. This is the main complaint about shuukh.mn.
- **Built for lawyers.** Serif type for legal text, monospace for citations, dense but calm layouts. Light and dark mode. Works at phone width.

---

## 2. System architecture

```
 shuukh.mn ──► Crawler ──► Raw store ──► AI extraction pipeline ──► Postgres (structured)
 (polite,     (incremental,  (HTML/PDF,     │                          │
  daily)       dedupe)        versioned)    ├─► Embeddings ─► Vector index (pgvector / Qdrant)
                                            └─► Citation graph ─► (case ↔ case ↔ article)
                                                                   │
                         Analytics jobs (nightly) ◄───────────────┘
                         judge stats, article clusters, conflicts, trends
                                   │
                  API (FastAPI / Node) ──► Web app (Next.js) ──► Lawyer
                                   │
                  LLM layer: matching, Q&A, drafting (RAG over decisions)
```

### 2.1 Ingestion
- Crawl shuukh.mn incrementally: back-fill the archive once, then run a daily delta. Rate-limit requests, cache responses, and respect robots.txt and the terms of use.
- Keep the original HTML/PDF and re-parse whenever the extractor improves.
- Normalize court names (the courts have been reorganized over the years) and judge names, and resolve duplicates.

### 2.2 AI extraction: one structured record per decision
An LLM with a strict JSON schema, checked against rules:

| Field | Examples |
|---|---|
| Metadata | case no., date, court, instance, judge(s), case type |
| Parties | role, individual or company, representation |
| Dispute | category taxonomy (about 150 leaf types, e.g. *Зээл → хувь хүн хооронд → бичгээр бус*) |
| Claims | each claim with its amount, and the outcome **per claim** (principal granted, interest rejected, and so on) |
| Facts | key facts as normalized tags (`written_contract=false`, `bank_transfer=true`, `acknowledged_by_message=true`) |
| Law applied | article-level citations (`ИХ 281.1`), and whether each is relied on or rejected |
| Reasoning | the holdings, quoted verbatim, plus the argument types that won or lost |
| Outcome | full, partial or dismissed at first instance; upheld, modified or reversed on appeal |
| Timing | filing date, decision date, duration |
| Links | the appeal chain: the same case at a higher instance |

Accuracy work: a gold set of about 1,000 decisions labelled by lawyers; field-level
precision and recall are tracked on every model or prompt change. Low-confidence fields
go to a human review queue.

### 2.3 "My case" matching
1. The LLM turns the user's story into the **same schema** (category, fact tags, amount, dates, evidence).
2. **Hybrid retrieval:** hard filters (category, case type), then vector similarity on facts and reasoning, then BM25 on keywords, then a re-ranker.
3. **Statistics** over the top N matches (with the sample size always shown): outcome shares, share of the claim awarded, duration, appeal results.
4. **Factor effects:** compare outcomes with and without each fact tag inside the matched set. Later, a logistic model with confidence intervals. Hide any factor with too few cases.
5. **Explanations:** the LLM writes "why similar" and the argument summaries **only** from the retrieved decisions (RAG with citations).
6. **Rule checks:** limitation periods, jurisdiction and court-fee estimate come from deterministic code, not the LLM.

### 2.4 Analytics jobs (nightly)
- **Judges:** volume, duration, outcome by category compared with the court baseline, reversal rate on appeal.
- **Law articles:** citation counts, co-citation, and **interpretation clusters** (embed the reasoning paragraphs that cite the article, cluster them, and have the LLM label each cluster).
- **Conflict detector:** same issue cluster + similar facts + opposite outcome or legal basis = flag it, with priority to conflicts the Supreme Court hasn't resolved.
- **Trends:** volumes and growth by category, court and region.

### 2.5 Suggested stack
- **Frontend:** Next.js + TypeScript and a custom design system (tokens as in the prototype). Server-side rendering keeps it fast.
- **Backend:** Python (FastAPI) for the pipelines, Postgres + pgvector, OpenSearch for full-text and facets, Redis for caching.
- **LLM:** a Claude model for extraction, matching explanations, chat and drafting. Plus a multilingual embedding model that handles Mongolian Cyrillic well, evaluated on our own retrieval set.
- **Jobs:** a queue (Celery or Temporal) for crawling and extraction, and a nightly analytics DAG.

---

## 3. Trust, ethics, legal
- Clear disclaimer: statistics, **not legal advice** and not a prediction for an individual case.
- Judge analytics are descriptive, shown against the court baseline, and always with the sample size. No "rankings".
- Personal data: shuukh.mn already anonymizes party names, and we run an extra de-identification pass. User case descriptions are private per account and are never used to train models without consent.
- Always link back to the original decision on shuukh.mn.

## 4. Roadmap
1. **MVP (civil cases):** crawler, extraction for civil decisions, search with filters, decision reader with summary.
2. **Matching:** "My case" with outcome stats and similar cases.
3. **Analytics:** judge profiles, law articles, trends.
4. **Workspace:** case folders, claim and memo drafting, team sharing.
5. **Criminal and administrative** schemas, sentencing analytics (for example, sentence ranges by article and circumstances).
6. **Alerts:** "notify me when a new decision cites 281.1 on this issue" or "when this judge rules on X".
