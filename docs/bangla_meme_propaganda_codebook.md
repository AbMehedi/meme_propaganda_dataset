# Bangla Meme Propaganda — Strict MVP Codebook

## 1. General Annotation Rule
Annotators must evaluate three information sources together:
- OCR text
- Visual content
- Text–image interaction

A technique should be assigned only when there is observable evidence in the meme.

**Core rule:**
- **Do not** label based on what the meme might imply. Label only what the meme *actually communicates* through its text, image, or their combination.
- Political content alone is not propaganda.
- Criticism alone is not propaganda.
- Insults alone are not automatically *Name Calling*.
- An emotional image alone is not automatically *Appeal to Strong Emotions*.

## 2. Annotation Unit
The primary annotation unit is: **One complete meme/image post** containing its available OCR text and visual content.

Each meme can receive:
- 0 or more propaganda techniques
- Exactly 1 or more modality labels per technique
- 0 or more text spans

**Valid example:**
- **Technique:** Loaded Language + Smears
- **Modality:** TEXT
- **Text Span:** "দেশদ্রোহী দুর্নীতিবাজ"

**Important:**
No Propaganda Technique is mutually exclusive with all other techniques. Therefore, combining any technique with `No Propaganda Technique` (e.g., *Loaded Language + No Propaganda Technique*) is **INVALID**.

## 3. Strict Decision Hierarchy
Use this decision process for every meme:

```text
START
  │
  ▼
Is there sufficient image/text information?
  │
  ├── NO → Mark NEEDS_REVIEW
  │
  ▼
Does the meme contain an identifiable persuasive/manipulative technique?
  │
  ├── NO → NO_PROPAGANDA
  │
  ▼
Evaluate each of the 7 techniques independently
  │
  ├── Loaded Language?
  ├── Name Calling / Labeling?
  ├── Smears?
  ├── Appeal to Fear / Prejudice?
  ├── Exaggeration / Minimisation?
  ├── Slogans?
  └── Appeal to Strong Emotions?
```
*Do not stop after finding one technique. A meme may contain several.*

---

## 4. Label Definitions

### T01 — Loaded Language
**Definition:** Language containing strong positive or negative emotional connotations that are used to influence how the audience perceives a person, group, event, or issue.

**Positive evidence (Label `T01_LOADED_LANGUAGE` when):**
- Emotionally charged adjectives/nouns are used.
- Strong evaluative language is used.
- The wording is clearly designed to provoke approval or disapproval.
- The emotional wording does not primarily function as a specific insult, allegation, threat, slogan, or exaggeration covered by another category.

**Examples:**
- "জঘন্য শাসন"
- "ভয়ংকর পরিস্থিতি"
- "লজ্জাজনক সিদ্ধান্ত"
- "অমানবিক সরকার"

**Do NOT label when:**
The word is merely descriptive and contextually neutral. (e.g., "নতুন সরকার", "ঢাকার মেয়র", "গতকাল বৃষ্টি হয়েছে").

**Boundary rule:**
- If the word is a specific derogatory label applied to a person/group, prefer: `T02_NAME_CALLING`.
- If it is a specific damaging allegation, consider: `T03_SMEAR`.

### 5. T02 — Name Calling / Labeling
**Definition:** Assigning a derogatory, stigmatizing, insulting, or demeaning label to a person or group in order to discredit them.

**Positive evidence (Label `T02_NAME_CALLING` when):**
`TARGET` + `DEROGATORY LABEL` is explicitly present.
- "ওরা দেশদ্রোহী"
- "ওই লোকটা বিশ্বাসঘাতক"
- "দালাল সরকার"
*(The important feature is the label itself.)*

**Visual evidence:**
The technique can also be multimodal.
- *Example:* Political person + Animal face superimposed + Derogatory text
- *If the visual transformation itself functions as the degrading label:* `Modality = IMAGE` or `BOTH`.

**Do NOT label when:**
A negative statement is a specific allegation of wrongdoing.
- *Example:* "মন্ত্রী বিদেশ থেকে ৫ কোটি টাকা নিয়েছেন।"
- This should be evaluated primarily as `T03_SMEAR` if presented as an unverified damaging allegation.

**Strict distinction:**
| Situation | Label |
| :--- | :--- |
| "দেশদ্রোহী" | Name Calling |
| "চোর" used as derogatory label | Name Calling |
| "সে বিদেশ থেকে ৫ কোটি টাকা চুরি করেছে" | Smear |
| "সে দুর্নীতির টাকা নিয়েছে" | Smear if presented as a specific damaging allegation |

### 6. T03 — Smears
**Definition:** Making a specific damaging allegation about a person, group, or organization with the purpose of damaging reputation, particularly where the claim is presented without sufficient evidence.

**Required structure:**
`TARGET` + `SPECIFIC NEGATIVE CLAIM` + `REPUTATIONAL DAMAGE`

**Examples:**
- "অমুক নেতা বিদেশি সংস্থার কাছ থেকে টাকা নিয়েছেন।"
- "অমুক দল গোপনে দেশের বিরুদ্ধে ষড়যন্ত্র করছে।"
- "অমুক ব্যক্তি দুর্নীতির কোটি টাকা আত্মসাৎ করেছেন।"

**Important distinction:**
- Specific allegation → Smear
- General insult → Name Calling

**Do NOT automatically label:**
"এই নেতা খারাপ" (This is more likely Loaded Language or potentially Name Calling depending on context).

**Evidence rule:**
Annotators should not decide whether the allegation is factually true from their personal knowledge. The annotation concerns the *propagandistic presentation* of a damaging allegation. If the meme simply reports a documented fact neutrally, do not automatically label it Smear.

### 7. T04 — Appeal to Fear / Prejudice
**Definition:** Attempting to influence an audience by creating fear, threat, panic, insecurity, or prejudice against a social/religious/ethnic/political group.

**Required evidence:**
There should be an identifiable `THREAT` / `DANGER` / `FEAR` / `PREJUDICE` directed toward an audience, person, or group.

**Examples:**
- "ওরা ক্ষমতায় এলে দেশে আর মসজিদ থাকবে না!"
- "এই দল জিতলে দেশ ধ্বংস হয়ে যাবে।"
- "ওদের কারণে আমাদের ধর্ম বিপদে।"

**Visual examples:**
A meme showing: Political opponent + burning building + "দেশ শেষ!" may qualify if the combined message clearly constructs a threat.

**Prejudice:**
Prejudice can target Religion, Ethnicity, Nationality, Social group, Political group, or any other identifiable group.

**Do NOT label:**
Strong emotion without fear (e.g., "আমাদের নেতা মহান!"). This may be `T07_STRONG_EMOTION`, not T04.

### 8. T05 — Exaggeration / Minimisation
**Definition:** Deliberately representing an event, condition, achievement, failure, threat, or problem as substantially more extreme or substantially less important than the available context supports.

**8.1 Exaggeration**
The meme substantially amplifies Scale, Severity, Importance, Consequences, Frequency, or Achievement.
- *Examples:* "১ টাকা দাম বাড়লেই দেশ ধ্বংস!", "এটাই বাংলাদেশের ইতিহাসের সবচেয়ে ভয়াবহ ঘটনা!"

**8.2 Minimisation**
The meme substantially downplays Seriousness, Scale, Harm, Responsibility, or Consequences.
- *Example:* "কয়েক কোটি টাকার দুর্নীতি? সামান্য ভুল!"

**Strict rule:**
Normal opinions (e.g., "আমি মনে করি বিষয়টি খুব গুরুত্বপূর্ণ নয়।") are not automatically Minimisation. There must be clear contextual evidence of significant downplaying.

### 9. T06 — Slogans
**Definition:** A short, memorable, repetitive, or rallying phrase used as a persuasive substitute for detailed reasoning.

**Strong indicators:**
Political campaign slogans, movement slogans, repeated catchphrases, rallying phrases, memetic political phrases, hashtag-like political slogans.

**Example structure:**
`SHORT CATCHPHRASE` + `PERSUASIVE/RALLYING FUNCTION`

**Important:**
A sentence is not a slogan simply because it is short (e.g., "বাংলাদেশ এগিয়ে যাচ্ছে।" is not automatically a slogan). But a repeated political campaign catchphrase used as a rallying message may be.

**Do NOT label:**
Normal descriptive text (e.g., "আজকের খবর", "বিশ্বকাপের আপডেট").

### 10. T07 — Appeal to Strong Emotions
**Definition:** Using text, images, or text-image combinations to deliberately provoke intense non-fear emotions such as Rage, Outrage, Extreme pity, Excessive admiration, Extreme pride, Hatred, or Strong emotional sympathy.

**Critical distinction:**
- Dominant emotional mechanism is FEAR/THREAT/PANIC → `T04_APPEAL_TO_FEAR_PREJUDICE`
- It is another intense emotion → `T07_STRONG_EMOTION`

**Examples:**
- A highly dramatic image of suffering combined with: "আপনার কি এখনও হৃদয় জাগেনি?"
- A heroic image designed to generate extreme admiration if the emotional manipulation is explicit.

**Visual-only example:**
Graphic suffering + dramatic emotional presentation + no relevant text = `T07_STRONG_EMOTION` (`Modality = IMAGE`).

**Do NOT label:**
Every emotional image. Emotion must be *central* to the persuasive message, not merely present.

### 11. T08 — No Propaganda Technique
**Definition:** No identifiable propaganda technique from the seven MVP categories is present.

**Valid cases:**
Ordinary humor, everyday memes, university jokes, weather jokes, pop-culture memes, neutral information, ordinary political discussion without identified propaganda technique, factual reporting without manipulative presentation.

**Critical rule:**
Political content ≠ propaganda.
- *Example:* "আজ সংসদে নতুন বিল নিয়ে আলোচনা হয়েছে।" should not receive a propaganda label simply because it concerns politics.

---

## 12. Strict Disambiguation Matrix
*This is the most important part of the codebook.*

| Question | If YES |
| :--- | :--- |
| Is there a specific derogatory label? | **T02 Name Calling** |
| Is there a specific damaging allegation? | **T03 Smear** |
| Is fear/threat/panic being deliberately created? | **T04 Fear/Prejudice** |
| Is something substantially overstated or downplayed? | **T05 Exaggeration/Minimisation** |
| Is there a short rallying/catchy persuasive phrase? | **T06 Slogan** |
| Is intense non-fear emotion being deliberately provoked? | **T07 Strong Emotion** |
| Is there strong emotionally charged wording without a more specific category? | **T01 Loaded Language** |
| None of the above? | **T08 No Propaganda** |

---

## 13. Priority Rules for Overlapping Labels
Multiple labels are allowed, but apply the following rules:

- **Example 1:** "দেশদ্রোহী চোর নেতা"
  - *Possible:* `T01 Loaded Language`, `T02 Name Calling` (because the text contains emotionally charged language and derogatory labels).
- **Example 2:** "নেতা X বিদেশি দেশের কাছ থেকে কোটি টাকা নিয়েছেন।"
  - *Primary:* `T03 Smear`. Do not add Name Calling merely because the allegation is negative.
- **Example 3:** "X ক্ষমতায় এলে দেশ ধ্বংস হয়ে যাবে!"
  - *Primary:* `T04 Appeal to Fear`. If the wording is also strongly emotionally charged, `T01` may be added only if the loaded wording contributes independently. Do not mechanically assign every possible label.

---

## 14. Modality Codebook
Every positive technique must receive **one** modality.

- **M1 — TEXT:** The technique is expressed primarily through written language. The technique can be understood from OCR/text alone. (e.g., "দেশদ্রোহী নেতা")
- **M2 — IMAGE:** The technique is expressed primarily through visual content. (e.g., Target person's face + degrading visual manipulation without relevant textual evidence.)
- **M3 — BOTH:** Both text and image are necessary or substantially contribute to the technique. (e.g., Image of political opponent + "দেশ ধ্বংসের ষড়যন্ত্রকারী", where visual and text jointly construct the message.)

---

## 15. Text Span Rules
For text-based techniques, annotate the **smallest meaningful evidence span**.

**Example:**
Text: "এই দুর্নীতিবাজ নেতা দেশ ধ্বংস করছে"
- Span 1: "দুর্নীতিবাজ" → Name Calling
- Span 2: "দেশ ধ্বংস করছে" → potentially Fear/Exaggeration depending on context.

*Do not select the entire paragraph unnecessarily. Use `start_char` and `end_char` for exact character boundaries.*

## 16. Visual Annotation Rule
**For MVP:** Do not manually draw visual bounding boxes.
Annotators should only record `Modality = IMAGE` or `Modality = BOTH` when appropriate. Visual-region extraction will be handled by future automated object-detection pipelines.

---

## 17. Evidence Requirement
Every positive annotation should have an evidence basis. Recommended JSON structures:

**For Text-based evidence:**
```json
{
  "technique": "T02_NAME_CALLING",
  "modality": "TEXT",
  "evidence_span": "দেশদ্রোহী",
  "evidence_type": "OCR_TEXT"
}
```

**For Image-based evidence:**
```json
{
  "technique": "T02_NAME_CALLING",
  "modality": "IMAGE",
  "evidence_span": null,
  "evidence_type": "VISUAL"
}
```

**For Multimodal evidence:**
```json
{
  "technique": "T04_APPEAL_TO_FEAR_PREJUDICE",
  "modality": "BOTH",
  "evidence_span": "দেশ ধ্বংস হয়ে যাবে",
  "evidence_type": "TEXT_IMAGE_INTERACTION"
}
```

---

## 18. "Do Not Infer Intent" Rule
Annotators should not attempt to determine the author's private intention.
- **Do not ask:** "Did the creator intentionally manipulate people?"
- **Instead ask:** "Does the meme contain an observable communication technique that matches the codebook?"

## 19. "Do Not Fact-Check" Rule
Annotators should not turn the annotation task into a general fact-checking task.
- *Example:* "Politician X stole 10 crore taka."
- **Do not ask:** "Is this actually true?"
- **Instead ask:** "Is this presented as a specific damaging allegation in a manner matching the Smear definition?"
*(If factual verification is required, store it as separate metadata, not inside the propaganda label.)*

---

## 20. Edge-Case Rules
- **Sarcasm:** If text and image together create a sarcastic propaganda meaning, use `Modality = BOTH`. Rely on the combined observable meaning.
- **Banglish:** Annotate normally. (e.g., "Ei neta puro chor!" → `T02_NAME_CALLING`).
- **Code-switching:** Bangla + English (e.g., "এই সরকার is a complete disaster") should be evaluated normally.
- **Political criticism:** Criticism alone is not propaganda (e.g., "সরকারের এই সিদ্ধান্ত ভুল।" → No automatic label).
- **Insult:** An insult is generally `T02 Name Calling` only when functioning as a derogatory label directed at a target.
- **Multiple techniques:** If independent evidence supports multiple techniques (`T01 + T02 + T04`), assign all of them. Do not force single-label classification.

---

## 21. Final Annotator Checklist

**Text**
- [ ] Did I read the complete OCR text?
- [ ] Did I consider Banglish?
- [ ] Did I identify exact evidence spans?

**Image**
- [ ] Did I inspect the complete image?
- [ ] Did I consider symbols, faces, gestures, edits, and visual manipulation?

**Multimodal**
- [ ] Does the image change the meaning of the text?
- [ ] Does the text change the interpretation of the image?
- [ ] Is `BOTH` actually justified?

**Taxonomy**
- [ ] Is there Loaded Language?
- [ ] Is there Name Calling?
- [ ] Is there a specific Smear?
- [ ] Is there Fear/Prejudice?
- [ ] Is there Exaggeration/Minimisation?
- [ ] Is there a Slogan?
- [ ] Is there Strong Emotion?

**Final check**
- [ ] Did I accidentally label political content as propaganda?
- [ ] Did I confuse an insult with a specific allegation?
- [ ] Did I confuse fear with general emotion?
- [ ] Did I label exaggeration without sufficient evidence?
- [ ] Did I assign No Propaganda Technique only when *none* of the seven techniques apply?

---

## 22. Recommended Machine-Readable Codes

**Taxonomy Codes:**
| Code | Label |
| :--- | :--- |
| `T01` | Loaded Language |
| `T02` | Name Calling / Labeling |
| `T03` | Smears |
| `T04` | Appeal to Fear / Prejudice |
| `T05` | Exaggeration / Minimisation |
| `T06` | Slogans |
| `T07` | Appeal to Strong Emotions |
| `T08` | No Propaganda Technique |

**Modality Codes:**
| Code | Label |
| :--- | :--- |
| `M1` | TEXT |
| `M2` | IMAGE |
| `M3` | BOTH |

**Annotation Status Codes:**
| Code | Meaning |
| :--- | :--- |
| `LLM_PRE` | LLM pre-annotation |
| `HUMAN_VERIFIED` | Human verified |
| `HUMAN_CORRECTED` | Human changed LLM output |
| `ADJUDICATED` | Resolved by adjudicator |