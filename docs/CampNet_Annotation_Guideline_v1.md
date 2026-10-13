# CampNet Annotation Guideline v1.0

**Prepared:** 12 October 2026
**Use:** 20-post calibration and 100-post reliability pilot. Freeze a revised version before main annotation. /give short line what a freeze revized version) 
**Purpose:** record observable persuasion techniques and the specific textual/visual evidence supporting each decision./how does analysis the single image through do any goood while we annonate?

## 1. What annotators decide

For one image post, decide:

1. Which retained persuasion techniques are observable?
2. Which words, visual regions, or combinations support each technique?
3. Is visual content required, reinforcing, unused, or unresolved for that instance?

The annotation concerns the message as presented. It does not establish factual falsity, the author's private intention, account ownership, or coordination.

**Evidence rule:** identify an observable persuasive operation: evaluative labeling, threat-based framing, reputation attack, exaggeration, rallying wording, or another defined mechanism. An annotator's political agreement/disagreement is not evidence.

Political content, criticism, a negative photograph, a flag, a famous face, or emotional news is insufficient by itself. Conversely, a factually true statement can use a persuasion technique. Satire may contain a technique; humor is not an automatic negative label.

The rule means annotate the persuasion technique you can see in the post, rather than deciding from its topic or appearance alone.

| Item | Short meaning |
|---|---|
| **Political content** | A post about politics is not automatically propaganda. |
| **Criticism** | Disagreeing with a person or policy is not automatically a technique. |
| **Negative photograph** | An unflattering or disturbing image needs a clear persuasive use. |
| **Flag** | A flag alone does not establish an appeal to national identity. |
| **Famous face** | Showing a well-known person alone does not establish an appeal to authority. |
| **Emotional news** | Reporting a sad or frightening event is not automatically an emotional appeal. |
| **Factually true statement**| A true claim can still use loaded words, a slogan, or another technique. |
| **Satire and humor** | A joke can use a technique; being funny does not make the label automatically negative. |

For example, "Publish the project accounts" is criticism. "Those thieves stole every penny" may be a smear if it targets an identifiable group or person.

## 2. Unit, context, and eligibility

The initial unit is **one single-image public post**, with original caption and visible embedded text. The caption is the platform post text, not an AI-generated image description.

Include readable Bangla-dominant and tagged Banglish/code-mixed posts relevant to the defined Bangladesh collection frame. Include cartoons, news cards, photographs, screenshots, posters, and text-dominant images. Retain natural negative examples. again question between my current .db and proposed how the transition pipeline should look like?

Quarantine multi-image posts, incomplete screenshots, or corrupt files until a policy is fixed. A missing caption is allowed and must be marked missing. Missing information must never be invented.

| Post status | Meaning | Main benchmark treatment |
|---|---|---|
| `COMPLETE` | Evidence supports a resolved technique set, including an empty set | Eligible for primary gold |
| `UNRESOLVED` | Missing context/readability or disagreement prevents a defensible set | Keep in audit pool; exclude from primary gold until resolved |
| `EXCLUDE` | Outside frame, corrupt, unintelligible, or violates the fixed unit policy | Preserve exclusion reason |

A known technique with uncertain **visual contribution** can remain a resolved classification annotation. Mark only its contribution/region supervision unavailable.

## 3. Annotation order

### Stage A — text only

Show corrected embedded text and original caption with explicit channel labels. Hide the image, publisher identity, engagement counts, model predictions, and previous human decisions.

- Select zero or more core techniques.
- Mark minimal spans and observable evidence.
- Record uncertainty and watchlist candidates.
- Save and lock the stage before showing the image.

### Stage B — full post

Reveal the original image together with the same caption and corrected OCR.

- Make a fresh technique decision. Labels may be added **or removed**.
- For each retained instance, mark channels, text spans, visual regions, and contribution.
- Record any reinterpretation: quotation, rejection of a slogan, satire, or a new target.
- Do not change the Stage A record to make the two views agree.

### Stage C — independent review and adjudication

A second human submits decisions without seeing the first human's labels. Then compare. The adjudicator resolves conflicts with a written codebook rule or marks the case unresolved.

Same-person text-before-image annotation reduces visual leakage into Stage A but can anchor Stage B. On a common blind audit subset, use a different reviewer for full-post judgment to estimate that effect. Do not claim the two stages are statistically independent just because they are stored separately.

## 4. Provisional core taxonomy

IDs remain stable across versions. This starting taxonomy adapts the supplied conceptual plan; it is not yet validated for the collected Bangla data.

### T01 — Loaded Language

**Rule:** emotionally evaluative words shape the audience's judgment beyond a neutral description.

**Positive text example:** “এই ঘৃণ্য সিদ্ধান্ত মেনে নেওয়া যায় না।” The charged description “ঘৃণ্য” is the local evidence.

**Negative example:** “সিদ্ধান্তটি গতকাল প্রকাশিত হয়েছে।”

**Boundary:** a factual term such as “দুর্ঘটনা” is not automatically loaded. For “দেশদ্রোহী” assigned to a target, consider T02 as well. Assign multiple labels only when the specific mechanisms are supported.

**Visual rule:** frightening colors or a red border alone do not establish Loaded Language; this label needs linguistic evidence.

### T02 — Name Calling / Labeling

**Rule:** an evaluative name, nickname, or category is assigned to a discernible target to shape judgment.

**Positive example:** “ওরা জাতির শত্রু।” Mark the evaluative label and its target; use `target_unknown` if the post itself does not identify “ওরা”.

**Negative example:** “তিনি দলের সাধারণ সম্পাদক।” This is an ordinary role description.

**Boundary:** negative words without an assigned label fit T01 more naturally. A depicted target explicitly equated with a degrading category may be cross-modal; ordinary animal imagery without that association is insufficient.

### T03 — Smears

**Rule:** an identifiable target is framed as disreputable through an accusation, insinuation, or degrading association.

**Positive textual example:** a named fictional official with “সব টাকা নিজের পকেটে নিয়েছে।” This is an accusation about the target; annotators do not decide whether it is true.

**Positive visual example:** an unmistakable composite representing the target as a thief stealing from citizens. Mark both the target depiction and the theft-related region if both establish the association.

**Negative example:** “প্রকল্পের খরচের হিসাব প্রকাশ করুন।” A request for accountability does not itself supply a smear.

**Boundary:** do not add T03 automatically to every T02 instance. For the pilot, require a reputation-damaging proposition or degrading framing beyond merely recognizing an insulting word; examine whether this local rule improves agreement.

### T04 — Appeal to Fear / Prejudice

**Rule:** danger or an existing prejudice is used as a reason to support/reject a target, idea, or action.

**Positive example:** “ওদের সমর্থন করলে আপনার পরিবার কখনো নিরাপদ থাকবে না।” Mark the threat and the persuasive link.

**Negative example:** “নদীর পানি বাড়ছে; নিরাপদ স্থানে যান।” A proportionate safety instruction is not automatically a fear appeal.

**Visual rule:** an alarming scene must be connected to the advocated/rejected position. A disturbing news photograph without that link is insufficient.

**Boundary:** prefer T04 for a specifically threat-based mechanism. Add T07 only if a distinct visual emotional appeal is independently supported, rather than counting the same threat twice.

### T05 — Exaggeration / Minimisation

**Rule:** the message visibly inflates or downplays magnitude, certainty, blame, importance, or consequences through its presentation.

**Positive example:** “একটি ভুলেই পুরো দেশ ধ্বংস হয়ে যাবে।” The sweeping consequence is observable without checking an external statistic.

**Minimisation example:** “কিছুই হয়নি, সামান্য ব্যাপার,” alongside the post's own depiction of serious destruction and an explicit dismissal of it.

**Negative example:** “সভায় প্রায় এক হাজার মানুষ ছিল।” An unverified number alone is not observable exaggeration.

**Visual rule:** a huge caricature figure or zoomed photograph is not automatically rhetorical exaggeration. Record how the visual scale or comparison supports the inflated/downplayed claim.

### T06 — Slogans

**Rule:** a memorable rallying phrase is used to mobilize support, identity, or action.

**Positive example:** “এক দাবি, এক লক্ষ্য—অন্যায় রুখে দাঁড়াও!” presented as the post's endorsed rallying message.

**Negative example:** “আজ বিকেলে বৃষ্টি হয়েছে।” Shortness alone is insufficient.

**Quotation example:** a news card neutrally quoting an organization's slogan may be a negative for the post's own technique use. Record the quotation and reporting stance; do not discard it mechanically.

**Visual rule:** repetition, placement, or typography can strengthen a slogan, but its linguistic evidence remains separate from non-textual visual evidence.

### T07 — Appeal to Strong Emotions

**Rule:** non-textual imagery is used to support a position through strong pity, grief, admiration, anger, or another emotional response.

**Positive example:** a distressing child image explicitly paired with a call to support a named cause, with the image serving as the appeal.

**Negative example:** a neutral report documenting the same distressing event without the codebook's persuasive framing.

**Boundary:** emotional wording without a visual emotional mechanism belongs under T01. Use T04 for a threat-specific appeal. A sad face or upsetting image alone is insufficient.

This operational restriction follows the image-oriented treatment of this category in SemEval-2021 [A1]. It is not a general definition of every emotional appeal.

## 5. Visual watchlist and taxonomy calibration

The seven starting labels may miss important visual persuasion. Record these candidates during the 100-post pilot, with the same evidence standard:

| ID | Watchlist technique | Evidence to look for | Insufficient by itself |
|---|---|---|---|
| W01 | Flag-Waving / Group-Identity Appeal | Group/national belonging used to justify a position or action | A flag, national color, or holiday greeting |
| W02 | Transfer | Positive or negative associations of a symbol/person transferred to a target through an explicit visual/message association | A famous face merely appearing in a picture |
| W03 | Glittering Generalities / Virtue | Attractive values or symbolic virtues attached to a target to invite endorsement without substantive support | A neutral use of “শান্তি” or a conventional logo |

These are established categories in the SemEval technique inventory [A1], not newly invented Bangla categories. Also note recurring Doubt, Authority, Whataboutism, or Causal Oversimplification as `other_candidate`; do not force them into the seven labels.

After the pilot, decide which labels form the primary benchmark based on definition stability, positive frequency, agreement, and feasible test coverage. Keep rare or unreliable candidates as auxiliary annotations. A practical final target is approximately 5–8 reliable labels, not a predetermined requirement.

## 6. Evidence channels and visual contribution

### 6.1 Evidence channels

Store one or more of:

- `CAPTION`: original post wording.
- `EMBEDDED_TEXT`: wording visible inside the image, transcribed into corrected OCR.
- `NON_TEXT_VISUAL`: faces as depicted, symbols, actions, composition, juxtaposition, or other non-textual evidence.
- `TYPOGRAPHY_LAYOUT`: persuasive treatment of text appearance or placement, when specifically evidenced.

Words in an image are **text evidence**. OCR's failure to read them does not turn them into non-textual visual evidence. Record typography separately so clean-view masking analyses can account for it.

### 6.2 Contribution judgments, per technique instance

| `visual_contribution` | Operational question | Example |
|---|---|---|
| `REQUIRED` | Without the relevant non-textual visual evidence, would the **same specific technique instance** still be supported by the text? If no, mark required. | Text “এদের দেখুন” obtains its target and degrading association only from a clear visual composite |
| `REINFORCING` | Text already supports the instance, and visuals strengthen or independently repeat it | A threat-based sentence plus a related danger scene |
| `NOT_USED` | No relevant visual evidence supports this instance | A slogan on a decorative background |
| `UNRESOLVED` | The contribution cannot be judged confidently | Obscured target, uncertain cultural symbol, or mixed image function |

Also record `text_sufficient` as `true`, `false`, or `null` for the same final technique instance.

- `REQUIRED` normally requires `text_sufficient=false`.
- `REINFORCING` requires `text_sufficient=true` and a named visual mechanism.
- `NOT_USED` requires a text-supported instance.
- If these answers conflict, review the case; do not automatically repair it in software.

Two modalities can both be sufficient. Under this convention, text sufficiency plus useful visual evidence is `REINFORCING`, even if the visual view could also support the technique independently. An optional `visual_sufficient` field may be collected on the separately blinded text-reduced-view subset; a judgment made after reading the original text is not an independent visual-only label.

These are human operational judgments, not causal measurements. Actual edited-view annotations provide a separate check.

### 6.3 Text-image relation

Optionally tag the observed relationship as `SUPPORTS`, `REFRAMES`, `CONTRADICTS`, `UNRELATED`, or `UNCLEAR`. Contradiction is not automatically propaganda. If imagery disproves a quoted statement rather than endorsing it, record the reinterpretation and reconsider the final technique set.

## 7. Marking textual evidence

Freeze `ocr_corrected` and `caption_canonical` before evidence annotation. Use human-checked transcription of what is actually visible, preserving misspellings, dialect, code-mixing, emojis, and negation. Keep a separate model-normalized version.

- Select the smallest span that expresses the mechanism, with nearby target/link spans if needed.
- Allow overlapping spans and multiple instances of the same technique.
- Spans are channel-relative **Unicode code-point indices**, zero-based, half-open `[start,end)`.
- Store the selected quote and channel text version/checksum.
- Require `channel_text[start:end] == quote`.
- Multiple disjoint spans use multiple span records, not one artificially long sentence span.
- Do not store UTF-8 byte offsets. JavaScript UTF-16 UI offsets need conversion for emoji and other non-BMP characters.
- If OCR text changes after annotation, invalidate/remap affected spans and review them; a successful file save does not fix offsets.

Avoid claiming a reputation attack from a subject's name span alone. Mark the operative accusation, label, or association.

## 8. Marking visual regions

Draw the smallest practical region or region set supporting the technique. Work on the **orientation-corrected original**, not a resized crop, and normalize coordinates to `[0,1]`.

- Rectangle: `[x_min,y_min,x_max,y_max]` with top-left origin.
- Polygon: ordered normalized vertex pairs, when a rectangle captures too much irrelevant material.
- Use one or more regions per technique instance; share a region ID if multiple techniques legitimately use it.
- When a relation between target and symbol is essential, mark both and store a `relation_note`.
- For global composition, use `scope=GLOBAL`, region covering the image, and explain why localization is not meaningful.
- Mark typography as `kind=TYPOGRAPHY_LAYOUT`, not `NON_TEXT`.
- Keep uncertain regions unavailable for supervised loss; absence of a box is not evidence of absence.

Mechanism tags are a **provisional descriptive vocabulary**, not propaganda labels:

| Tag | Observable evidence |
|---|---|
| `DEGRADING_ASSOCIATION` | Target linked to an explicitly degrading object/symbol/depiction |
| `THREAT_SCENE` | Dangerous imagery linked to support/rejection of a position |
| `EMOTIONAL_APPEAL` | Depicted distress, admiration, grief, or anger used in the message's appeal |
| `IDENTITY_SYMBOL` | Group/national symbol performing an identity-based argument |
| `VIRTUE_ASSOCIATION` | Positive symbolic value attached to a target |
| `JUXTAPOSITION` | Side-by-side or composite relation changes interpretation |
| `VISUAL_MAGNITUDE` | Depicted scale/comparison supports exaggeration/minimisation |
| `TYPOGRAPHIC_EMPHASIS` | Text presentation performs evidenced rhetorical work |
| `OTHER` | Explain the observable mechanism; consider refining after the pilot |

A portrait, color, or object can be context without being evidence. Explain the link between the marked region and the named technique in one factual sentence. Do not infer a real person's mental state from facial appearance or use face identification to infer an unnamed target.

## 9. Empty labels, other persuasion, and uncertainty

`No Propaganda Technique` is an **empty core technique set**, not an eighth technique class.

| Situation | Core set | `has_core_technique` | Other fields |
|---|---|---|---|
| No defined technique after complete review | `[]` | `false` | Status complete |
| One or more resolved core techniques | Instances | `true` | Evidence required |
| Only persuasive watchlist/out-of-taxonomy mechanism | `[]` | `false` for core-only task | `out_of_taxonomy=true`; do not call it globally non-propagandistic |
| Too uncertain to decide the set | Unresolved | `null` | Exclude from primary classification until adjudicated |

For a binary **any-curated-technique** benchmark, define the retained taxonomy after calibration and recompute the flag. Do not equate core absence with absence of every possible persuasion technique.

Confidence is an annotation aid: `1=uncertain`, `2=borderline but supported`, `3=clear evidence`. It is not a probability and cannot replace evidence or agreement.

## 10. Frequent boundary cases

| Case | Decision rule |
|---|---|
| Reported allegation | Examine quotation/reporting stance; keep the allegation's presence separate from endorsement |
| Fact-check or rebuttal containing a slogan | Reconsider full-post labels when the phrase is rejected rather than used as an appeal |
| Satirical portrait | Require a defined persuasive mechanism; caricature alone is insufficient |
| Disaster/violence photograph | Record emotional content; assign a technique only with supported framing/link |
| “All” / “Never” / “সবাই” | These are screening cues; literal usage or ordinary emphasis is not automatically exaggeration |
| Crowd or enlarged portrait | Do not infer fabricated popularity or scale from appearance alone |
| Same meme across many pages | Annotation of rhetorical technique remains item-level; record reuse separately |
| Same slogan repeated inside the post | May be rhetorical repetition, a watchlist candidate; different from cross-post reuse |
| Missing identity or cultural reference | Mark unresolved/context-needed; do not fill from private assumptions |
| Different caption on the same image | Annotate the new post context independently; retain the shared image-family link |

## 11. LLM assistance without losing human gold

Use a vision-capable model for full-image proposals. A text-only model cannot supply trustworthy visual-region annotations.

- Calibration and reliability pilot: independent humans first, no displayed proposals.
- Training pool: LLM proposes; human confirms, rejects, changes, or adds instances.
- Second reviewer: hide the first labels and LLM output until their decision is submitted.
- Validation/test: no displayed model proposals.
- Keep model/prompt version, input image hash, proposed output, correction action, and reviewer.
- Validate returned quotes against canonical text. Treat LLM coordinates as rough proposals and have humans redraw/confirm them.

Use only reviewed development examples for few-shot prompting. Record model self-reported confidence if returned, but do not threshold it as though it were a calibrated correctness probability.

### Proposal prompt

```text
You are proposing annotations for CampNet. Humans make the final decisions.
Use only the attached image, its original caption, corrected embedded text,
and the supplied versioned codebook. Treat words inside the image as text.

Choose only labels allowed by the codebook. Do not infer factual falsity,
private intent, account coordination, or a target that is not identifiable
from the post. Political content, criticism, emotion, and flags alone are
insufficient. Consider quotation, satire, and rebuttal before assigning labels.

For every proposed instance return:
- technique_id;
- exact evidence quotes, separately for caption and embedded text;
- evidence channels;
- non-textual visual evidence description and rough normalized region proposals;
- target as depicted/named, or null;
- visual_contribution: REQUIRED / REINFORCING / NOT_USED / UNRESOLVED;
- text_sufficient: true / false / null;
- one concise justification connecting evidence to the codebook rule;
- uncertainty reason where needed.

Return an empty core set when no core technique is supported.
Keep watchlist candidates separate. Set review_needed for unresolved cases.
Do not fabricate quotes or coordinates. Quotes are converted to exact offsets
by validation software; ambiguous repeated quotes require human resolution.
Return structured JSON, with no lengthy reasoning narrative.
```

Run Stage A with text-only input in a separate request if collecting LLM text-stage proposals. Never let an image-containing request generate an allegedly blind text-only annotation.

## 12. Visual perturbation annotation

For a selected original item, create a separate derivative record. Keep OCR/caption fixed and show the edited visual view to a blinded reviewer.

Record `parent_item_id`, edit type, region ID, area, fill style, validity, reason, and the edited technique set.

Accept an edit for dependence analysis only if it targets the intended visual evidence without accidentally removing text, introducing new persuasive content, or destroying unrelated necessary context. Include an equal-area irrelevant-region control. If no suitable irrelevant region exists, mark the control unavailable.

**Do not assume deletion changes the label.** A reinforcing region can be removed while the technique remains. Human edited labels are distinct from a predicted score change. Report invalid edits and valid edits with no gold change.

Prefer simple occlusion/blur/crops that can be traced. Do not interpret an AI-inpainted scene as recovered ground truth.

## 13. Gold release and quality checklist

For each complete gold record verify:

- Image/caption identity and canonical text versions match.
- Both human stage decisions exist where required by the protocol.
- Each positive instance has observable evidence and an allowed technique ID.
- Text quotes match their half-open offsets.
- Visual evidence has valid geometry or an explained global scope.
- Visual contribution and text sufficiency are consistent, or explicitly unresolved.
- Empty labels are distinguishable from missing labels and out-of-taxonomy persuasion.
- Assistance/adjudication history is retained.
- Duplicate/content-family membership is known before partitioning.

Compute agreement on independent decisions before consolidation: per-technique alpha or kappa, positive agreement, label-set Jaccard, span overlap, visual-contribution agreement, and region overlap for matched instances. A single aggregate accuracy can be misleading under imbalance.

### 20-post calibration selection

Use approximately four neutral/news posts, four text-dominant cards, four visually framed attacks, four fear/emotion/identity examples, and four mixed/satirical/borderline cases. These are intentional coverage quotas for calibration, not estimates of the natural distribution. If the pool lacks a category, record the gap instead of inventing data.

Discuss every disagreement, revise examples, and record the rule changed. Then annotate 80 additional items independently for the reliability pilot.

## Annotation basis

The provisional seven core labels come from the supplied conceptual plan and remain subject to calibration. The staged evidence approach and visual watchlist draw on the following primary sources. CampNet's contribution judgments, detailed region schema, and decision rules above are **proposed operational adaptations**, not claims that these exact fields existed in the source datasets.

[A1] Dimitrov et al. (2021). *SemEval-2021 Task 6: Detection of Persuasion Techniques in Texts and Images*. [Source](https://aclanthology.org/2021.semeval-1.7/)

[A2] Dimitrov et al. (2024). *SemEval-2024 Task 4: Multilingual Detection of Persuasion Techniques in Memes*. [Source](https://aclanthology.org/2024.semeval-1.275/)

[A3] Sharma and Patil (2026). *Small Cues, Big Consequences: Learning Pivotal Cues for Multimodal Meme Classification*. Relevant close prior art for cue/contribution/intervention annotations; author preprint. [Source](https://arxiv.org/html/2609.26907v1)
