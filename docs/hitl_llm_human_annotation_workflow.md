# Human-in-the-Loop (HITL) Annotation Workflow
## LLM Pre-Annotation + Human Verification for the Multimodal Bangla Propaganda Dataset

Building a high-quality dataset using **LLM pre-annotation combined with human verification**—often called **Human-in-the-Loop (HITL) annotation**—can reduce the manual annotation bottleneck while maintaining strong data-quality controls.

Manual annotation by experts is time-consuming and expensive. However, relying entirely on unverified LLM-generated labels can introduce systematic errors, hallucinations, and model bias. Therefore, the proposed workflow uses LLMs as **pre-annotators**, while humans remain responsible for verification, correction, and final decisions.

The workflow consists of five phases:

1. **Codebook & Schema Standardization**
2. **Batch LLM Pre-Annotation & Uncertainty Scoring**
3. **Stratified Human Verification**
4. **Quality Control & Inter-Annotator Agreement**
5. **Final Dataset Auditing & Provenance**

---

# Phase 1: Codebook & Schema Standardization

Before invoking an LLM or assigning human annotation tasks, establish a clear and consistent annotation framework.

## 1.1 Define a Structured Codebook

The annotation codebook should contain:

- Explicit definitions for every label.
- Positive examples.
- Negative examples.
- Boundary conditions.
- Edge-case handling rules.
- Rules for multi-label cases.
- Rules for modality assignment.
- Rules for text-span selection.

For the propaganda detection task, the codebook should be aligned with the project's initial taxonomy:

1. Loaded Language
2. Name Calling / Labeling
3. Smears
4. Appeal to Fear / Prejudice
5. Exaggeration / Minimisation
6. Slogans
7. Appeal to Strong Emotions
8. No Propaganda Technique

The codebook should be treated as the primary reference for both LLM prompts and human annotation.

---

## 1.2 Structured LLM Prompt

The LLM should be instructed to return structured output rather than unrestricted natural-language responses.

A suitable output structure is:

```json
{
  "labels": [
    {
      "label": "Loaded Language",
      "confidence_score": 0.91,
      "rationale_span": "example text span",
      "reasoning": "Concise explanation of why the span supports the label."
    }
  ],
  "modality": "TEXT"
}
```

### Required LLM Fields

| Field | Purpose |
|---|---|
| `label` | Predicted propaganda technique |
| `confidence_score` | Model's estimated uncertainty/confidence |
| `rationale_span` | Exact text evidence supporting the prediction |
| `reasoning` | Concise explanation supporting the prediction |
| `modality` | `TEXT`, `IMAGE`, or `BOTH` |

### Important Note

The `rationale_span` should identify the exact evidence used for the prediction.

For research reproducibility, the system should retain the original LLM output and the final human-verified annotation separately.

---

## 1.3 Pilot Calibration

Before processing the complete dataset, conduct a pilot evaluation using a small **Gold Standard** sample.

Recommended size:

```text
100–200 samples
```

The pilot sample should be independently labeled by at least **two human experts**.

Use this sample to evaluate the initial LLM pre-annotation performance using metrics such as:

- Precision
- Recall
- F1-score

The pilot should also identify common failure modes, such as:

- Misinterpretation of sarcasm.
- Incorrect handling of Bangla/Banglish code-switching.
- Confusion between related propaganda techniques.
- Incorrect text-span boundaries.
- Incorrect modality assignment.
- Failure to recognize implicit visual propaganda.

The findings should be used to refine the annotation codebook and LLM prompt before large-scale annotation begins.

---

# Phase 2: Batch LLM Pre-Annotation & Uncertainty Scoring

After the codebook and prompt have been calibrated, process the remaining raw dataset using the LLM as a **pre-annotation system**.

The LLM's predictions are not considered final labels at this stage.

---

## 2.1 Multi-Sample Consistency

For each sample, the LLM may be queried multiple times.

A possible configuration is:

```text
Number of runs: 3–5
Temperature: T = 0.7
```

The resulting predictions can be compared for consistency.

### Example

If five runs produce:

```text
Run 1 → Loaded Language
Run 2 → Loaded Language
Run 3 → Loaded Language
Run 4 → Loaded Language
Run 5 → Loaded Language
```

the prediction demonstrates high consistency.

If the outputs are:

```text
Run 1 → Loaded Language
Run 2 → Smears
Run 3 → Loaded Language
Run 4 → Appeal to Fear / Prejudice
Run 5 → Smears
```

the sample should be treated as uncertain and prioritized for human review.

### Consistency Principle

```text
High agreement between runs
        ↓
Higher pre-annotation confidence

Low agreement between runs
        ↓
Higher human-review priority
```

Self-consistency should be treated as an uncertainty signal rather than proof that the LLM prediction is correct.

---

## 2.2 Ensemble / Multi-Model Pre-Annotation

Where resources allow, use two different LLM families or model types.

For example:

```text
Model A
   +
Model B
   ↓
Compare Predictions
```

When both models produce the same prediction, the item may be placed into a higher-confidence tier.

When the models disagree, the item should receive higher review priority.

### Example

```text
Model A → Loaded Language
Model B → Loaded Language
        ↓
Agreement
        ↓
Higher-confidence candidate
```

versus:

```text
Model A → Loaded Language
Model B → Smears
        ↓
Disagreement
        ↓
Human review required
```

Model agreement should not replace human verification for the final dataset.

---

# Phase 3: Stratified Human Verification

The purpose of human annotation changes from **creating every annotation from scratch** to **verifying and correcting LLM-generated pre-annotations**.

The review system should prioritize difficult and uncertain samples while still auditing high-confidence predictions.

## 3.1 Confidence Tiers

| Confidence Tier | Criteria | Human Review Workflow |
|---|---|---|
| **High Confidence** | Models agree / high consistency | **Random spot-check (5–10%)** to detect subtle errors and systematic bias |
| **Medium Confidence** | Single model / moderate certainty | **Single-expert verification**; human accepts, modifies, or re-labels |
| **Low Confidence / Disagreement** | Models disagree / low consistency / edge case | **Dual-expert review**; disagreements proceed to senior adjudication |

---

## 3.2 High-Confidence Samples

High-confidence predictions should not automatically be accepted.

Instead:

- Randomly sample approximately **5–10%**.
- Have a human expert audit these predictions.
- Monitor systematic errors.
- Increase the audit percentage if substantial errors are discovered.

This provides a quality-control mechanism for detecting cases where the LLM is consistently confident but systematically wrong.

---

## 3.3 Medium-Confidence Samples

Medium-confidence samples should undergo **single-expert verification**.

The expert can:

```text
ACCEPT
   ↓
Keep LLM annotation

EDIT
   ↓
Modify incorrect label/span/modality

REJECT / RELABEL
   ↓
Replace the LLM prediction with the human decision
```

The original LLM prediction should remain stored for provenance.

---

## 3.4 Low-Confidence or Disagreement Samples

Samples with:

- LLM disagreement,
- Low self-consistency,
- Conflicting model predictions,
- Ambiguous evidence,
- Difficult edge cases,

should receive **dual-expert review**.

If the two experts disagree, the case should be forwarded to a **senior adjudicator** or domain expert.

The final adjudicated decision becomes the authoritative annotation.

---

# Phase 4: Quality Control & Inter-Annotator Agreement

The dataset must include formal quality-control procedures to evaluate both human annotation quality and LLM pre-annotation performance.

---

## 4.1 Inter-Annotator Agreement (IAA)

Measure agreement using appropriate statistical metrics.

Possible metrics include:

- **Cohen's Kappa (κ)** for agreement between two annotators.
- **Fleiss' Kappa** for agreement among multiple annotators.

Agreement should be evaluated separately for relevant annotation components where appropriate:

```text
Technique Label Agreement
        +
Modality Agreement
        +
Span Agreement
```

For text spans, additional span-level metrics may be appropriate because exact character-boundary agreement is different from categorical label agreement.

---

## 4.2 Compare LLM and Human Annotations

Evaluate:

```text
LLM Pre-Annotation
        ↕
Human Verification
```

and:

```text
Human Annotator A
        ↕
Human Annotator B
```

This allows the research team to distinguish:

- LLM prediction quality.
- Human annotation consistency.
- Difficult annotation categories.
- Systematic LLM failure modes.

The LLM should be evaluated against human-verified labels rather than treated as the ground truth.

---

## 4.3 Adjudication & Disagreement Resolution

When disagreements occur:

1. Record the disagreement.
2. Identify the source of the disagreement.
3. Review the relevant codebook rule.
4. Allow the assigned experts to discuss the case where appropriate.
5. Escalate unresolved cases to a senior adjudicator.
6. Record the final decision.
7. Record the reason for the decision when useful.

Common failure patterns should be tracked, including:

- Implicit sarcasm.
- Bangla/Banglish code-switching.
- Ambiguous wording.
- Political or cultural context.
- Technical terminology.
- Visual-textual interactions.
- Difficult text-span boundaries.
- Multiple simultaneous propaganda techniques.

---

## 4.4 Prompt Iteration Loop

Resolved edge cases should be used to improve subsequent LLM pre-annotation.

The iterative process is:

```text
LLM Pre-Annotation
        ↓
Human Verification
        ↓
Disagreement Analysis
        ↓
Identify Failure Pattern
        ↓
Update Codebook / Few-Shot Examples
        ↓
Update LLM Prompt
        ↓
Next Annotation Batch
```

The goal is to continuously improve pre-annotation quality without allowing the LLM to become the source of the final ground truth.

---

# Phase 5: Final Dataset Auditing & Provenance

Every annotation should maintain a clear record of how it was produced.

This is important for research reproducibility, dataset auditing, and later model evaluation.

---

## 5.1 Annotation Provenance

Each annotation should include metadata indicating its annotation pathway.

Recommended provenance categories:

| Provenance | Meaning |
|---|---|
| `human_annotated` | Annotation created directly by a human |
| `llm_preannotated_human_verified` | LLM generated the initial annotation and a human verified/corrected it |
| `llm_preannotated_spot_checked` | LLM generated the annotation and it passed the designated spot-check process |

Additional provenance fields may include:

```text
llm_model
llm_version
prompt_version
annotation_timestamp
human_annotator_id
verification_timestamp
adjudication_status
```

Where possible, retain the original LLM output separately from the final verified annotation.

---

# 5.2 Gold Standard Test Set

The final evaluation/test split must be protected from unverified LLM labels.

The test set should contain:

```text
100% Human-Annotated / Human-Verified Instances
```

No unverified LLM-generated annotation should be used as the ground truth for final model evaluation.

This prevents evaluation leakage and avoids measuring a model against labels generated by another model.

---

# 5.3 Dataset Split Principle

A suitable conceptual split is:

```text
Raw Dataset
     │
     ├── Training Set
     │      └── LLM pre-annotation + human verification
     │
     ├── Validation Set
     │      └── Human-verified
     │
     └── Test / Gold Standard Set
            └── 100% human-annotated / human-verified
```

The exact split ratio should be determined by the research design and final dataset size.

---

# End-to-End HITL Workflow

The complete annotation workflow can be summarized as:

```text
                 CODEBOOK
                    │
                    ▼
            Pilot Gold Sample
                    │
                    ▼
          LLM Prompt Calibration
                    │
                    ▼
           Batch LLM Annotation
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   Self-Consistency      Multi-Model
       Analysis            Agreement
          │                   │
          └─────────┬─────────┘
                    ▼
            Confidence Tiering
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
     HIGH         MEDIUM        LOW
       │            │            │
   Spot-check    1 Expert    2 Experts
       │            │            │
       └────────────┼────────────┘
                    ▼
             Adjudication
                    │
                    ▼
          Quality Control / IAA
                    │
                    ▼
          Prompt & Codebook Update
                    │
                    ▼
             Final Audit
                    │
                    ▼
       Human-Verified Dataset
                    │
                    ▼
        Locked Gold Test Set
```

---

# Recommended Annotation Data Structure

To preserve both the LLM history and final human decisions, the annotation system should conceptually separate **pre-annotation** from **final annotation**.

```text
ANNOTATION
├── annotation_id
├── post_id
├── technique_label
├── modality
├── start_char
├── end_char
├── annotation_source
├── verification_status
├── human_annotator_id
├── adjudication_status
└── created_at
```

LLM-specific information can be stored separately:

```text
LLM_PREANNOTATION
├── llm_annotation_id
├── post_id
├── model_name
├── model_version
├── prompt_version
├── predicted_label
├── confidence_score
├── rationale_span
├── reasoning
├── run_id
└── created_at
```

This separation prevents the original LLM prediction from being overwritten when a human corrects it.

---

# Core Principles

The HITL annotation system should follow these principles:

1. **LLMs are pre-annotators, not ground truth.**
2. **Humans make the final annotation decisions.**
3. **High-confidence predictions are still subject to spot-checking.**
4. **Low-confidence and disagreement cases receive more intensive review.**
5. **Original LLM outputs are preserved for provenance.**
6. **Human corrections are recorded separately from LLM predictions.**
7. **The annotation codebook is continuously refined using observed edge cases.**
8. **Multi-label, modality, and text-span information must be preserved.**
9. **IAA should be measured to monitor human annotation consistency.**
10. **The final test/gold-standard set must contain only human-annotated or human-verified instances.**

---

# Final Objective

The objective of this workflow is to achieve a practical balance between:

```text
Annotation Efficiency
        +
Human Reliability
        +
LLM-Assisted Scalability
        +
Research Reproducibility
        +
Dataset Quality
```

The resulting dataset should be sufficiently reliable for downstream experiments in **multimodal Bangla propaganda detection**, while retaining the annotation provenance and quality-control information necessary for rigorous research.
