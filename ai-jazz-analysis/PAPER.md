# Research Paper: Abstract and Outline

**Working title:** Can AI Swing? A Musician-Centred Evaluation of Jazz Competence in Audio Generation Models

---

## Abstract

Rapid advances in AI music generation have produced systems capable of producing audio that superficially resembles jazz, yet it remains unclear whether these models achieve genuine musical competence or replicate surface-level plausibility. Jazz is an ideal test domain: it has deep, codifiable rules (swing microtiming, functional harmony, formal structure) alongside conventions learnable from a large recorded corpus, making both failure and success diagnostically interpretable. We present a structured evaluation of five leading AI music generation systems — Suno v4, Udio, MusicGen, Stable Audio 2, and AIVA — against six fixed prompts spanning bebop, modal jazz, ballad, jazz blues, big-band swing, and Latin jazz. Each of the 30 generated pieces is assessed on a six-axis rubric (harmonic authenticity, swing feel, improvisational coherence, idiomatic vocabulary, ensemble interaction, and formal structure) by a trained jazz musician, with a second rater providing inter-rater reliability scores. Quantitative analysis via onset-based swing ratio detection and chroma-based chord extraction complements qualitative assessment. Preliminary findings from 4 rated pieces reveal a consistent pattern: AI models exhibit stronger local coherence than global formal structure, automated swing ratio detection systematically underestimates perceptual swing in polyphonic audio, and template-based ii-V-I detection fails on mixed audio — findings that have implications for evaluation methodology as much as for the models themselves. The best-performing piece was judged by the primary rater as indistinguishable from amateur human jazz by a non-specialist listener. This work contributes a replicable evaluation framework, a diagnostic axis-by-axis breakdown of jazz competencies, and a critical analysis of the gap between quantitative audio metrics and musician-perceived quality.

---

## Paper Outline

### 1. Introduction

- The rapid improvement of audio generation models has produced systems that can mimic a wide range of musical styles
- Jazz as a testbed: why it is ideal (learnable rules, large corpus, diagnostic failure modes)
- The gap between plausibility and competence: a listener unfamiliar with jazz may be fooled; a trained musician may not be
- Research questions (as stated in README)
- Paper contribution: evaluation framework + preliminary findings + methodological critique of quantitative metrics
- Overview of paper structure

---

### 2. Related Work

#### 2.1 AI Music Generation Systems
- Survey of current audio-generative approaches (diffusion models, language-model token prediction, symbolic generation)
- Suno v4 and Udio: prompt-driven audio; MusicGen: melody-conditioned; Stable Audio 2: latent diffusion; AIVA: symbolic/MIDI
- Limitations of prior evaluations: subjective listening tests with lay raters, FID/FAD-style objective metrics, genre classification accuracy

#### 2.2 Computational Analysis of Jazz
- Swing ratio literature: Friberg & Sundstrom (2002), Benadon (2006)
- Chord detection and harmonic analysis: Fujishima (1999) key-finding, Mauch & Dixon (2010), Chroma-based approaches
- ii-V-I detection in jazz corpora
- Limitations of automatic analysis on polyphonic audio

#### 2.3 Human Evaluation in Music
- Rubric-based approaches in music education (ABRSM, Rockschool grading frameworks)
- Inter-rater reliability in music assessment: Cohen's kappa benchmarks
- Musician versus lay listener evaluation: what expertise reveals that casual listening misses
- The case for musician-centred evaluation of AI music

---

### 3. Methodology

#### 3.1 Model Selection
- Rationale for the five models: coverage across audio-generative (diffusion), language-model (Suno, Udio), and symbolic (AIVA) paradigms
- Version pinning and first-generation-only policy (no cherry-picking)

#### 3.2 Prompt Design
- Six prompts covering core jazz styles: bebop, modal jazz, ballad, jazz blues, big-band swing, Latin jazz
- Design principles: fixed text across all models, BPM targets, instrumentation requirements, style-specific evaluation criteria, and explicit failure modes
- Full prompts in Appendix A

#### 3.3 Evaluation Rubric
- Six axes with anchored 1–5 descriptors (full rubric in Appendix B):
  1. Harmonic Authenticity — chord quality, voice leading, functional progression
  2. Swing Feel & Microtiming — perceived rhythmic authenticity, not just tempo
  3. Improvisational Coherence — motivic development, tension and release, long-range logic
  4. Idiomatic Jazz Vocabulary — correct deployment of style-specific devices
  5. Ensemble Interaction — instrument roles, call-and-response, complementary texture
  6. Formal Structure — AABA, blues form, sectional coherence over full duration
- Axis selection rationale: derived from music education rubrics and prior AI music evaluation literature

#### 3.4 Blind Rating Protocol
- Primary rater completes all 30 ratings before seeing quantitative results
- Second rater (independent jazz musician) completes ratings without access to primary scores
- Reconciliation procedure for disagreements

#### 3.5 Quantitative Analysis Pipeline
- Swing ratio: librosa onset detection → consecutive eighth-note pair ratios → mean and standard deviation per piece
- Chord detection: chroma CQT → template matching → quality classification (7 quality types) → ii-V-I detection via root-interval pattern matching
- Key detection: Krumhansl-Kessler profiles applied to mean chroma vector
- Jazz pitch-class similarity: cosine distance to reference jazz corpus pitch-class distribution
- Harmonic complexity: chroma entropy (normalised to [0, 1])
- Figures: swing ratio over time, chord timeline, batch summary dashboard

#### 3.6 Limitations
- Polyphonic audio reduces chord and swing detection accuracy (documented in preliminary results)
- Single primary rater introduces subjectivity; second rater required for reliability claims
- Model versioning: generation quality may shift between paper submission and publication
- 30 pieces is a small N for cross-model statistical inference; findings are preliminary and diagnostic rather than conclusive

---

### 4. Results

#### 4.1 Overall Rubric Scores
- Cross-model comparison table: mean score per axis per model
- Total score distribution: which models fall in which competency band?
- Radar chart: each model's competency profile across the six axes

#### 4.2 Axis-by-Axis Analysis

##### 4.2.1 Harmonic Authenticity
- Which models produce functional jazz harmony vs. surface-level chord labels?
- Chord quality distribution: proportion of 7th-chord-or-richer voicings
- ii-V-I counts per piece (with caveat about detector reliability)
- Case study: Blue Dorian Drift — detected ii-V-Is (Gm7→C7→Fm7, Fm7→Bb7→Eb) missed by automated detector

##### 4.2.2 Swing Feel & Microtiming
- Swing ratio vs. human swing score: the Rail Yard Bop discrepancy
- High-ratio pieces (Blue Note Bounce: 2.014) vs. high-variance pieces (Blue Dorian Drift: ±0.894)
- When does high swing ratio reflect genuine swing versus metric noise?
- The case for hybrid swing evaluation: quantitative onset ratio + qualitative drum/bass interaction assessment

##### 4.2.3 Improvisational Coherence
- Short-term vs. long-term coherence: AI models perform better in 30-second excerpts than over full pieces
- Case study: Blue Dorian Drift (4/5 improvisational coherence, 2/5 formal structure)
- Case study: Whispers of the Dorian Sky — coherent opening, chaos by 0:55

##### 4.2.4 Idiomatic Jazz Vocabulary
- Which models deploy jazz-specific devices (chromatic approach notes, bebop licks, blues inflection)?
- Generic jazz vs. style-specific competency: Rail Yard Bop as competent but generic bebop

##### 4.2.5 Ensemble Interaction
- Instrument role definition: do models assign meaningful, differentiated roles to each instrument?
- Rail Yard Bop (5/5): each instrument fulfils its idiomatic function
- Blue Dorian Drift (3/5): instruments coexist without genuine interaction

##### 4.2.6 Formal Structure
- The most consistent weakness across all models and styles
- No piece achieved a clear B section or committed to a full AABA or blues form over its duration
- Hypothesis: generative models optimise locally and lack a representation of large-scale formal intention
- Mean formal structure score across all rated pieces: ~2.5/5

#### 4.3 Quantitative vs. Human Rating Correlation
- Pearson r between swing ratio and human swing score
- Pearson r between jazz chord richness (% 7th-or-richer) and harmonic authenticity score
- Systematic biases in automated metrics and their diagnostic interpretation

#### 4.4 Inter-Rater Reliability
- Cohen's kappa per axis and overall
- Which axes are most reliably agreed upon? Which require reconciliation?
- Implications for rubric design

---

### 5. Discussion

#### 5.1 What AI Jazz Models Have Learned
- Local harmonic logic (functional progressions, voice leading) is reliably present in the best pieces
- Timbre and texture: models produce convincingly jazz-like soundscapes
- Standard vocabulary items (chromatic runs, ii-V-I progressions, ballad voicings) appear in the expected contexts

#### 5.2 What AI Jazz Models Have Not Learned
- Formal structure: no model demonstrates the ability to plan and execute a complete jazz form
- Long-range coherence: pieces degrade over time in ways that human performances do not
- Style-consistent swing: the relationship between tempo, feel, and rhythmic density is not reliably maintained

#### 5.3 The Measurement Problem: Automated Metrics and Polyphonic Audio
- The swing ratio underestimation finding is itself a contribution: onset-based detection on polyphonic audio is unreliable as a sole measure of perceptual swing
- The ii-V-I detector fails on polyphonic audio due to chord onset ambiguity and harmonic smearing
- Proposed mitigations: source separation as pre-processing; spectrogram-based chord models; hybrid human/automated evaluation

#### 5.4 The "Amateur Jazz" Ceiling
- Rail Yard Bop (26/30): competent, indistinguishable from an amateur by a non-specialist
- Jazz musicians detect it not as "AI-generated" but as "bad jazz" — a meaningful distinction
- This ceiling is diagnostic: models have passed the plausibility threshold but not the competence threshold for trained listeners

#### 5.5 Implications for AI Music Evaluation Practice
- Lay listener ratings are insufficient for genre-competence claims
- Domain-expert rubric evaluation is necessary but must be accompanied by inter-rater reliability
- Quantitative metrics should be treated as diagnostics, not ground truth

---

### 6. Conclusion

- Summary of key findings: local coherence achieved, formal structure not; swing ratio diverges from perceptual swing; models produce "amateur jazz" at best
- The diagnostic value of failure: which axes fail tells us what the models are not representing
- Recommended next steps: longitudinal study as models improve, formal structure as explicit evaluation criterion in future generation research
- Call for standardised, musician-validated evaluation frameworks in AI music generation

---

### References

*(To be populated — key citations will include:)*

- Friberg, A. & Sundstrom, A. (2002). Swing ratios and ensemble timing in jazz performance.
- Benadon, F. (2006). Slicing the beat: Jazz eighth-notes as expressive microrhythm.
- Mauch, M. & Dixon, S. (2010). Approximate note transcription for the improved identification of difficult chords.
- Copet, J. et al. (2023). Simple and Controllable Music Generation (MusicGen). NeurIPS.
- Evaluation rubric literature from ABRSM / Rockschool grading frameworks

---

### Appendix A — Full Prompt Texts

*See [PROMPTS.md](PROMPTS.md)*

### Appendix B — Rubric with Anchored Descriptors

*See [methodology.md](methodology.md)*

### Appendix C — Per-Piece Human Assessments

*See `results/notes/`*

### Appendix D — Quantitative Results Tables

*To be populated once all 30 pieces are rated*
