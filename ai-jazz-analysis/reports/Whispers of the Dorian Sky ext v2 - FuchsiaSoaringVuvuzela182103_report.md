# Piece Report: Whispers of the Dorian Sky ext v2 - FuchsiaSoaringVuvuzela182103

*Generated: 2026-07-07 12:38*

---

## Quick Stats

| Metric | Value |
| --- | --- |
| Tempo | 134 BPM |
| Detected key | C# minor |
| Swing ratio | 1.225  *(weak / light swing)* |
| Swing std dev | 0.617 |
| Jazz complexity | 77% |
| ii-V-I progressions | 0 |
| Unique chords | 40 |
| Jazz PC similarity | 0.948 |
| Harmonic complexity | 0.859 |
| Rubric total | 10/30 |

---

## AI Musical Assessment

The rhythmic profile of this piece is immediately at odds with its stated intent. A modal jazz piece in the Kind of Blue tradition should breathe at 60–75 BPM with brushed drums and deliberate space; the detected tempo is 134 BPM — nearly double that — and the swing ratio of 1.225 places it in "weak/light swing" territory, with a standard deviation of 0.617 that reflects genuine rhythmic instability rather than expressive rubato. The high variance is diagnostic: the human rater identifies the swing collapsing entirely at 0:32, suggesting the model cannot sustain even its modest initial rhythmic commitment. The percussion tracking a different feel from the melodic instruments compounds this — a problem of ensemble-level coordination that onset detection alone cannot capture, but that is immediately audible to any listener.

The harmonic data tells a contradictory story. A jazz pitch-class similarity of 0.948 and 77% jazz complexity (7th-chord-or-richer) suggest sophisticated vocabulary on paper — and the quality breakdown confirms this: major 7ths (29%), minor 7ths (24%), and half-diminished chords (15%) dominate, which is broadly modal-jazz-appropriate. However, 40 unique chords across a short piece, a chroma entropy of 0.859 (approaching the theoretical maximum of 1.0), and zero detected ii-V-I progressions paint a different picture: the model is not working within a stable modal framework, it is cycling through every available extended chord with no tonal anchor. The top chords — Dbmaj7, Dmaj7, Amaj7, Gm7b5, Am7 — span multiple key centres with no resolution logic, and the chroma entropy figure confirms that all twelve pitch classes are nearly equally active. Modal jazz should show the opposite: low entropy, strong pitch-class dominance in the governing mode.

The overall verdict is that this piece represents the clearest failure mode in this dataset. The model has absorbed the surface vocabulary of modal jazz — the extended chords, the solo-instrument melody, the sparse texture — but has no understanding of what modal jazz actually does: sustain a single tonal colour over time, resist cadential resolution, and allow silence to function as music. The style prompt requires commitment to stillness; the model instead applies jazz-sounding materials randomly, without any governing harmonic or rhythmic logic that holds beyond the first thirty seconds. Where Rail Yard Bop might fool a non-specialist as "bad jazz," this piece would not fool anyone listening past the first phrase. Specific weakness: total absence of modal stasis. Specific strength: the opening 30 seconds, before the collapse, demonstrate that the model can briefly assemble convincing modal textures — it simply cannot sustain them.

---

## Rhythmic Analysis

Mean swing ratio: **1.225** ± 0.617  
Valid eighth-note pairs analysed: **98**  

> Reference: 1.0 = straight · 1.5 = medium swing · 2.0 = hard swing / triplet feel

![Swing ratio over time](../figures/Whispers of the Dorian Sky ext v2 - FuchsiaSoaringVuvuzela182103_swing_ratio.png)

---

## Harmonic Analysis

**Jazz pitch-class similarity:** 0.948  
**Harmonic complexity (chroma entropy):** 0.859  
*(0 = single pitch class dominant; 1 = all 12 equally active)*

![Chord timeline](../figures/Whispers of the Dorian Sky ext v2 - FuchsiaSoaringVuvuzela182103_chord_timeline.png)

---

## Chord Vocabulary

| Chord | Quality | Beats | % of total |
| --- | --- | --- | --- |
| Dbmaj7 | major 7th | 10 | 10.4% |
| Gm7b5 | half-diminished (m7b5) | 6 | 6.2% |
| Dmaj7 | major 7th | 6 | 6.2% |
| Am7 | minor 7th | 5 | 5.2% |
| Bbm7 | minor 7th | 4 | 4.2% |
| Bbm | minor triad | 4 | 4.2% |
| Amaj7 | major 7th | 4 | 4.2% |
| Db | major triad | 3 | 3.1% |
| G | major triad | 3 | 3.1% |
| A7 | dominant 7th | 3 | 3.1% |

**Quality distribution:**

- major 7th                    █████ 29.2%
- minor 7th                    ████ 24.0%
- half-diminished (m7b5)       ██ 14.6%
- major triad                  ██ 12.5%
- minor triad                  ██ 10.4%
- dominant 7th                 █ 9.4%

---

## Rubric Scores

| Axis | Score (1–5) | Visual |
| --- | --- | --- |
| Harmonic Authenticity | 2 | ■■□□□ |
| Swing Feel | 2 | ■■□□□ |
| Improvisational Coherence | 1 | ■□□□□ |
| Idiomatic Vocabulary | 2 | ■■□□□ |
| Ensemble Interaction | 2 | ■■□□□ |
| Formal Structure | 1 | ■□□□□ |
| **Total** | **10/30** |  |

> Starts fine but devolves into chaos. Swing breaks at 0:32; random chords at 0:47; incoherent fast runs at 0:55. Percussion doesn't follow same swing. Zero repetition or formal structure.

---

## Human Analysis

*Add your own observations here after listening to the piece.*

**First impression:**

<!-- What stands out immediately on first listen? -->

**Rhythmic feel:**

<!-- Does it swing? Where does it feel natural or mechanical? -->

**Harmonic observations:**

<!-- Any unexpected chord choices, voice leading moments, or tonal ambiguity? -->

**Stylistic resemblance:**

<!-- What era or substyle of jazz does this most evoke? -->

**Discrepancies from AI assessment:**

<!-- Where does the AI analysis miss something you hear clearly? -->

---

## References

- Rubric and methodology: [methodology.md](../methodology.md)
- Original prompts: [PROMPTS.md](../PROMPTS.md)
- Re-generate this report: `python analysis/generate_report.py --piece "Whispers of the Dorian Sky ext v2 - FuchsiaSoaringVuvuzela182103"`