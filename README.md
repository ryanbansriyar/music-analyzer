# Can AI Swing? A Jazz Musician's Evaluation of Harmonic and Rhythmic Competence in AI Music Generation

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Research Question

**Which specific jazz competencies do current AI generation models succeed and fail at, and what does the pattern of failure reveal about the models' underlying musical representations?**

Sub-questions:
- Do models produce authentic swing microtiming, or metronomically straight rhythms labelled as "jazz"?
- Can models navigate functional jazz harmony (ii–V–I, tritone substitution, modal interchange) beyond surface chord labels?
- Does improvisational content exhibit motivic development, or is it statistically plausible but structurally incoherent?
- Is there a meaningful difference between audio-generative models and the symbolic/MIDI-based AIVA on rubric axes where notation-level control matters?

---

## Models Evaluated

| Model | Developer | Output Type | Notes |
|---|---|---|---|
| **Suno v4** | Suno AI | Audio | Vocal + instrumental; prompt-driven |
| **Udio** | Udio | Audio | High-fidelity audio generation |
| **MusicGen** | Meta AI | Audio | Open-source; melody-conditioned variant used |
| **Stable Audio 2** | Stability AI | Audio | Latent diffusion; strong on timbre |
| **AIVA** | AIVA Technologies | MIDI / Symbolic | Outputs symbolic notation, not audio. Evaluated on MIDI export; some audio-domain metrics will be substituted with score-level analysis. |

---

## Process

### Phase 1 — Design (complete)

- Defined the core research question and four sub-questions
- Wrote 6 fixed jazz prompts covering: bebop, modal jazz, ballad, 12-bar blues, big-band swing, and Latin jazz (see [PROMPTS.md](ai-jazz-analysis/PROMPTS.md))
- Each prompt includes target BPM, instrumentation, jazz-specific evaluation criteria, and a list of known failure modes to watch for
- Designed a 6-axis evaluation rubric with anchored 1–5 scores per axis (see [methodology.md](ai-jazz-analysis/methodology.md)):
  1. Harmonic Authenticity
  2. Swing Feel & Microtiming
  3. Improvisational Coherence
  4. Idiomatic Jazz Vocabulary
  5. Ensemble Interaction
  6. Formal Structure
- Established blind rating protocol: files renamed to opaque identifiers before evaluation
- Defined quantitative analysis methods: onset-based swing ratio, chroma-based key detection, chord vocabulary extraction

### Phase 2 — Data Collection (in progress)

- Submitted all 6 prompts to each model; collecting first-generation outputs only (no regeneration)
- Target: 30 pieces (5 models × 6 prompts)
- Collected to date: 7 pieces — 5 from Suno v4, 2 from Udio
- Pieces collected:

| Piece | Model | Prompt Style | Rated? |
|---|---|---|---|
| Rail Yard Bop | Suno v4 | Bebop | Yes — 26/30 |
| Moonlit Voicings | Suno v4 | Jazz Ballad | Yes — 23/30 |
| Blue Dorian Drift | Suno v4 | Modal Jazz | Yes — 19/30 |
| Blue Note Bounce | Suno v4 | 12-Bar Blues / Big Band | No |
| Corner Pocket Riff | Suno v4 | Jazz Blues | No |
| Chasing the High Flight | Udio | (TBD) | No |
| Whispers of the Dorian Sky | Udio | Modal Jazz | Yes — 10/30 |

### Phase 3 — Quantitative Analysis Pipeline (complete)

Built a fully operational Python analysis suite under `ai-jazz-analysis/analysis/`:

| Script | Purpose |
|---|---|
| `swing_ratio.py` | Onset detection → eighth-note pair ratios → swing ratio per piece |
| `chord_detection.py` | Chroma-based chord segmentation, quality classification, ii-V-I detection |
| `harmonic_analysis.py` | Batch harmonic stats — pitch-class distribution, jazz/pop similarity |
| `results_dashboard.py` | Single-image summary dashboard across all rated pieces |
| `generate_report.py` | Full per-piece Markdown report with AI summary, charts, rubric scores, and a human analysis section |
| `rating_helper.py` | CLI tool for completing rubric scores interactively |
| `blind_rename.py` | Renames files to `piece_NN` identifiers before rating begins |

All scripts output to `figures/` and `reports/`. Reports now include a `## Human Analysis` section for the rater to annotate.

### Phase 4 — Human Rating (in progress)

- **Rater:** Grade 8 Rockschool jazz pianist, 10 years of training
- **Rating method:** Listen at least once blind, score all 6 axes, write detailed per-axis notes, then compare against automated analysis and note agreements/discrepancies
- Detailed written assessments completed: Blue Dorian Drift, Rail Yard Bop, Moonlit Voicings, Whispers of the Dorian Sky
- Rubric scores entered in `results/scores.csv` for 4 pieces

### Phase 5 — Second Rater & IRR (not started)

- Recruit an independent second rater (target: another trained jazz musician)
- Second rater completes the same 30 ratings blind, without seeing primary scores
- Calculate Cohen's kappa; target ≥ 0.6 for acceptable inter-rater reliability

### Phase 6 — Analysis & Write-Up (not started)

- Cross-model comparison on each rubric axis
- Correlation analysis: do quantitative metrics predict rubric scores?
- Identify which jazz competencies are systematically absent across all models
- Write the research paper (see [PAPER.md](ai-jazz-analysis/PAPER.md) for abstract and outline)

---

## Current Status — June 14, 2026

**Pieces rated:** 4 of a target 30

| Piece | Harmonic | Swing | Improv | Vocab | Ensemble | Form | Total |
|---|---|---|---|---|---|---|---|
| Rail Yard Bop | 4 | 5 | 4 | 4 | 5 | 4 | **26/30** |
| Moonlit Voicings | 4 | 4 | 4 | 4 | 4 | 3 | **23/30** |
| Blue Dorian Drift | 4 | 3 | 4 | 3 | 3 | 2 | **19/30** |
| Whispers of the Dorian Sky | 2 | 2 | 1 | 2 | 2 | 1 | **10/30** |

**Swing ratio measurements (all collected pieces):**

| Piece | Tempo (BPM) | Swing Ratio | Std Dev | Tool Label |
|---|---|---|---|---|
| Blue Note Bounce | 144 | 2.014 | 0.870 | hard swing / triplet feel |
| Blue Dorian Drift | 128 | 1.710 | 0.894 | strong swing |
| Moonlit Voicings | 69 | 1.513 | 0.819 | medium swing |
| Chasing the High Flight | 141 | 1.302 | 0.687 | weak / light swing |
| Rail Yard Bop | 125 | 1.159 | 0.500 | weak / light swing |
| Corner Pocket Riff | 100 | 1.096 | 0.422 | essentially straight |

**Key emerging findings:**

1. **Automated swing ratio underestimates perceptual swing in polyphonic audio.** Rail Yard Bop scores 1.159 ("weak swing") but receives 5/5 on the human swing axis — the most striking disagreement in the dataset so far. The onset-based detector captures isolated eighth-note pair ratios but misses the felt swing created by bass, drums, and piano interaction.

2. **The ii-V-I detector consistently underdetects on polyphonic audio.** Both Blue Dorian Drift and Rail Yard Bop show 0 detected ii-V-I progressions despite the human rater clearly hearing multiple functional progressions. This is a recurring limitation of template-matching on mixed audio.

3. **Formal structure is the weakest axis across all rated pieces** (average 2.5/5). Every piece loses points here — the AI models appear to lack the ability to commit to and execute a formal plan over the full duration of a piece.

4. **Local coherence outlasts global coherence.** Pieces can sound convincing on a 30-second excerpt but become incoherent as a full piece. Blue Dorian Drift's style shift at 1:34 is the clearest example. "Whispers of the Dorian Sky" began to deteriorate at 0:32, with random chords by 0:47 and incoherent fast runs by 0:55.

5. **The best-rated piece would pass as amateur human jazz.** Rail Yard Bop (26/30) received 5/5 on both swing and ensemble interaction. The human rater's verdict: "Non-jazz listeners would not be able to figure it out, and jazz musicians may just call it 'bad' rather than 'AI.'"

---

## Methodology Overview

- **6 fixed prompts** covering core jazz styles (see [PROMPTS.md](ai-jazz-analysis/PROMPTS.md))
- **30 pieces total** (5 models × 6 prompts), first output only — no regeneration
- **6-axis evaluation rubric** with anchored 1–5 scores per axis (see [methodology.md](ai-jazz-analysis/methodology.md))
- **Blind rating**: files encoded before rating; second rater scores same set independently
- **Inter-rater reliability**: Cohen's kappa target ≥ 0.6
- **Quantitative swing analysis**: onset detection via librosa, swing ratio computation per piece
- **Harmonic analysis**: chord vocabulary, ii–V–I detection, pitch-class distribution

Full methodology: [methodology.md](ai-jazz-analysis/methodology.md)

---

## Repository Structure

```
music-analyzer/
├── README.md                   # This file
└── ai-jazz-analysis/
    ├── methodology.md          # Rubric, protocol, and quantitative methods
    ├── PROMPTS.md              # The 6 fixed prompts sent to every model
    ├── PAPER.md                # Research paper abstract and outline
    ├── pieces/                 # Raw audio files (not tracked in git)
    ├── results/
    │   ├── scores.csv          # Master ratings spreadsheet
    │   ├── swing_results.csv   # Batch swing ratio results
    │   └── notes/              # Per-piece human assessments and chord CSVs
    ├── reports/                # Per-piece generated Markdown reports
    ├── figures/                # Output plots (generated by scripts)
    └── analysis/
        ├── swing_ratio.py
        ├── chord_detection.py
        ├── harmonic_analysis.py
        ├── results_dashboard.py
        ├── generate_report.py
        ├── rating_helper.py
        ├── blind_rename.py
        └── requirements.txt
```

---

## How to Reproduce

### 1. Install dependencies

```bash
cd ai-jazz-analysis/analysis
pip install -r requirements.txt
```

### 2. Run swing ratio analysis on a single file

```bash
python swing_ratio.py ../pieces/piece_01.wav
```

### 3. Batch analyse all pieces

```bash
python swing_ratio.py --batch ../pieces/
python chord_detection.py --batch ../pieces/
```

### 4. Generate a per-piece report

```bash
python generate_report.py --piece "Rail Yard Bop"
python generate_report.py --piece "Rail Yard Bop" --no-ai   # skip Claude API call
```

### 5. View the results dashboard

```bash
python results_dashboard.py
```

Figures are saved to `../figures/`. Ratings are in `results/scores.csv`.

---

## Author

Grade 8 Rockschool jazz pianist, 10 years of training. Evaluations reflect idiomatic jazz performance knowledge, not computational musicology credentials — which is precisely the point.
