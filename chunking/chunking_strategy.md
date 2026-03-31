# ClaimMate Chunking Strategy (Week 1, source-specific draft)

## 1. Purpose

ClaimMate’s RAG is not a generic document search tool. It must answer questions by grounding responses in both user policy text and California / U.S. insurance guidance, and it must support citation transparency in the UI. Therefore, chunking must preserve legal meaning, policy clause boundaries, and user-facing topic structure.

## 2. What the source files actually look like

### 2.1 Regulation files are legal-structure documents
The California regulation files are short, section-based documents with explicit subsection nesting such as `(a)`, `(b)`, `(1)`, `(A)`. For example, §2695.5 is organized into lettered duties, and §2695.7 and §2695.8 contain deeper nested structures for claims handling and automobile-insurance-specific standards.

### 2.2 Policy files are hierarchical contract documents
The policy PDFs are organized by major Parts / Coverage sections and then by repeated subheadings like `Definitions`, `Insuring Agreement`, `Exclusions`, `Limit`, `Duties`, `Proof of Loss`, `Payment of Loss`, `Appraisal`, and `General Provisions`. This is visible in the State Farm booklet and the California National General policy.

### 2.3 Guide files are topic / workflow documents
The California accident guide is organized as a practical workflow plus FAQ blocks and rights sections; the mediation guide is organized by eligibility, issue types, and a numbered process; the NAIC guide is a broad educational guide organized by insurance topics. These are not legal clauses, so they should be chunked by user-facing topic blocks rather than by token count alone.

### 2.4 Some files contain wrapper or layout noise
The regulation PDFs include wrapper material such as Westlaw page headers, “Home Table of Contents,” `Credits`, `History`, and `END OF DOCUMENT`, which should not become chunks. The non-California National General file also shows layout noise / duplicated TOC-style material and printer artifacts such as `GMAC Spreads.qxd`, so it needs extra cleanup before chunking.

---

## 3. Pre-chunk cleaning rules

Before chunking, apply these rules to every file:

### Keep
- section titles
- coverage titles
- numbered / lettered clause text
- bullet lists that carry legal or procedural meaning
- claimant rights, duties, deadlines, payment rules, repair rules, valuation rules

### Remove
- website headers / URLs
- repeated page headers and footers
- copyright-only lines
- “Back to Top”
- contact-only footer blocks
- `Credits`
- `History`
- `END OF DOCUMENT`
- duplicated table-of-contents pages
- printer / OCR artifact strings such as `GMAC Spreads.qxd`

These removals are necessary because several of your files clearly contain wrapper text or duplicated layout content that would otherwise pollute retrieval.

---

## 4. Primary chunking rule by document type

## 4.1 Regulations: subsection-first chunking

### Rule
For regulation files, the default chunk unit is the **smallest legally meaningful subsection**.

### Use these units
- `2695.2(a)`
- `2695.2(c)`
- `2695.5(e)(1)`
- `2695.7(b)(1)`
- `2695.8(b)(2)`
- `2695.85(c)-Right-1` style consumer-right item chunks

### Why
These sections are written as legally distinct duties, definitions, deadlines, settlement standards, and rights. Mixing multiple subsections into one chunk would weaken citation clarity and make answers less precise. For example, §2695.5 separates acknowledgment, assistance, and investigation duties into different numbered items, and §2695.7 separates denial timing, continued notice, investigation quality, unreasonable offers, and payment obligations into separate duties.

### Special handling by regulation
- **§2695.2 Definitions**: chunk by lettered definition, and if a single definition contains numbered children, keep them in the same chunk unless it becomes too long.
- **§2695.3 File and Record Documentation**: chunk by subsection because each subsection states a separate recordkeeping obligation.
- **§2695.4 Representation of Policy Provisions and Benefits**: chunk by subsection `(a)` through `(g)` because each rule governs a distinct prohibited or required practice.
- **§2695.5 Duties upon Receipt of Communications**: chunk by `(a)` to `(f)`, but split `(e)` into child chunks `(e)(1)`, `(e)(2)`, `(e)(3)` because those are separately useful for retrieval.
- **§2695.7 Prompt, Fair and Equitable Settlements**: use parent-child chunking. Keep one parent chunk for the main subsection topic, but store child chunks for numbered items like `(b)(1)`, `(c)(1)`, `(g)(1)-(7)`, `(h)`.
- **§2695.8 Additional Standards Applicable to Automobile Insurance**: also use parent-child chunking because total-loss and repair standards are deeply nested and claim questions may target a very specific rule.
- **§2695.85 Auto Body Repair Consumer Bill of Rights**: chunk one parent intro chunk plus one chunk per numbered right, because users may ask very specific repair-right questions.

### Fallback
If one legal subsection is too long, split **within the same subsection only**, by paragraph or numbered child item. Never merge text from different lettered subsections into one chunk.

---

## 4.2 Policy PDFs: heading-first chunking

### Rule
For policy files, the default chunk unit is **heading or subheading + its full clause text**.

### Preferred chunk examples
- `LIABILITY COVERAGE > Insuring Agreement`
- `LIABILITY COVERAGE > Exclusions`
- `PHYSICAL DAMAGE COVERAGES > Limit and Loss Settlement`
- `PART E DUTIES AFTER AN ACCIDENT OR LOSS > General Duties`
- `PART D COVERAGE FOR DAMAGE TO YOUR AUTO > Appraisal`
- `GENERAL TERMS > Cancellation`

This matches the actual structure in the State Farm and National General policies, which are built around repeated contractual headings rather than statute-style letters.

### Definitions rule
Do **not** put the entire policy definitions section into one giant chunk.

Instead:
- chunk by term group when short, about 3–6 related definitions
- or by single definition when the term is especially retrieval-important, such as:
  - `newly acquired auto / car`
  - `your covered auto`
  - `insured`
  - `non-owned car`
  - `temporary substitute car`

This matters because your source policies define these terms separately and later coverage clauses depend on them.

### Exclusions rule
For long exclusion sections:
- keep the heading as the parent context
- split by numbered exclusion item when needed
- preserve the numbering in metadata

Example:
- `Liability Coverage > Exclusions > Item 1–4`
- `Liability Coverage > Exclusions > Item 5–8`

Do not split mid-item.

### Claims and duties rule
Claims-related sections are especially important for ClaimMate, so always keep them as high-quality standalone chunks:
- `Notice to Us of an Accident or Loss`
- `Notice to Us of a Claim or Lawsuit`
- `General Duties`
- `Additional Duties for Coverage for Damage to Your Auto`
- `Proof of Loss`
- `Payment of Loss`
- `Appraisal`
- `Legal Action Against Us`
- `Concealment / Misrepresentation / Fraud`

These sections appear directly in the policy sources and are likely to be queried in post-accident situations.

### Multi-page continuation rule
If a clause starts on one page and ends on the next page, merge it before chunking. Page boundaries are not legal boundaries.

### Noisy file rule
For `policy_sample_03_national_general_personal_auto_policy.pdf`, deduplicate repeated TOC-style content and layout artifacts before chunking. Do not embed duplicate copies of the same policy headings.

---

## 4.3 Consumer guides: topic-block chunking

### Rule
For guide files, chunk by **user task, FAQ pair, step block, rights block, or glossary block**.

### Accident guide
Use these chunk units:
- `What to do at the scene of an accident`
- one FAQ pair per chunk
- `Your rights under the Fair Claims Settlement Practices Regulations`
- `Auto Body Repair Shops`
- `Auto Replacement Parts`

The accident guide is structured as a practical help document, with checklists and Q/A blocks rather than formal clauses.

### Mediation guide
Use these chunk units:
- `Who is eligible`
- `Issues eligible`
- `Issues not eligible`
- each mediation step as its own chunk
- `Insurance Terms and Phrases` as small grouped glossary chunks

This guide contains a clear process flow and issue taxonomy, so preserving those boundaries will help user questions like “am I eligible?” or “what happens after I request mediation?”

### California auto insurance guide / NAIC guide
Use these chunk units:
- one coverage topic per chunk
- one rights / complaint / claims topic per chunk
- glossary terms in grouped chunks
- do not mix broad shopping advice with claims-process content

These are educational guides, so topic purity matters more than fine-grained paragraph splitting.

### Low-priority guide chunks
Contact pages and “Talk to Us” sections should either be:
- omitted, or
- stored as low-priority fallback chunks

They are useful for complaint-routing, but should not dominate normal claims retrieval.

---

## 5. Chunk size policy

### Default target
- target: **120–350 words**
- soft max: **450 words**
- hard max: **~550 words**

### Why
Your files already provide natural boundaries. The goal is not to force every chunk to the same size, but to preserve meaning while keeping retrieval units small enough to rank well.

### If chunk is too short
Do not merge across unrelated headings or legal subsections just to hit a size target. Short but self-contained legal / policy chunks are acceptable.

### If chunk is too long
Split only inside the same:
- regulation subsection
- policy heading
- guide topic block

---

## 6. Metadata rules for each chunk

Every chunk must carry at least:

- `doc_id`
- `file_name`
- `document_type`
- `source_name`
- `jurisdiction`
- `page`
- `section`
- `section_root`
- `title`
- `coverage_category`
- `content_type`
- `chunk_id`

This matches your Week 1 metadata direction and is necessary for later citation UI and retrieval evaluation.

### Recommended metadata conventions

#### Regulations
- `section`: full path such as `2695.5(e)(2)`
- `section_root`: root such as `2695.5`
- `content_type`: `definition` / `rule` / `consumer_right`
- `coverage_category`: `claims_handling`, `auto_claims`, or `repair_rights`

#### Policies
- `section`: `PART A > Exclusions` or `PART E > General Duties`
- `section_root`: `PART A`, `PART E`, etc.
- `content_type`: `coverage_clause`, `exclusion`, `duty`, `limit`, `definition`
- `coverage_category`: usually `general_policy`, but use more specific categories when obvious

#### Guides
- `section`: user-facing topic name
- `section_root`: guide-level topic family
- `content_type`: `guidance`, `faq`, `workflow_step`, `glossary`
- `coverage_category`: based on topic

---

## 7. Priority hints for retrieval

For answer ranking, prefer sources in this order:

1. California regulations  
2. California-specific policy language  
3. other policy forms  
4. California consumer guides  
5. NAIC national guide

This ordering fits ClaimMate’s goal of grounding answers in both personal coverage and California / U.S. rights, while still allowing general guides to fill gaps.

---

## 8. Explicit do-not-do rules

Do **not**:
- chunk by fixed token length first
- merge multiple regulation subsections into one generic chunk
- split a policy heading mid-clause if the only reason is size normalization
- include Westlaw wrapper text, History, Credits, or duplicated TOC pages
- combine contact / hotline material with substantive legal or coverage content
- store duplicate copies of repeated policy pages

---

## 9. Week 1 implementation decision

For Week 1 co-testing, the approved initial strategy is:

- **Regulations:** subsection-first, with parent-child chunking for deeply nested sections  
- **Policies:** heading-first, with special care for definitions, exclusions, duties, appraisal, proof/payment of loss  
- **Guides:** topic-block / FAQ / workflow-step chunking  
- **Cleanup:** remove wrapper noise and duplicates before embedding