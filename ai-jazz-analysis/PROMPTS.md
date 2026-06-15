# Jazz Generation Prompts

These are the exact prompt texts sent to every model, unchanged. Do not paraphrase or adapt for a specific model — consistency across models is the point.

---

## Prompt 1 — Up-Tempo Bebop Head

**Prompt text:**
> Generate an original bebop jazz piece at approximately 220 BPM. Include a 32-bar AABA head melody with a swinging rhythm section (piano, upright bass, drums, and alto or tenor saxophone). The head should feature the angular, chromatic melodic lines typical of Charlie Parker or Dizzy Gillespie, with fast harmonic movement including ii-V-I progressions and tritone substitutions. After the head, include at least one improvised chorus over the changes before returning to the out-head.

**Target duration:** 75–90 seconds

**Jazz-specific elements to evaluate:**
- Chromatic, rhythmically displaced bebop melody in the head
- Fast harmonic rhythm (chord changes every 1–2 beats is authentic bebop)
- Swing feel at high tempo — swing ratio should hold up above 200 BPM
- AABA form executed correctly (8+8+8+8 bars = 32 bars)
- Piano comping style (sparse, rhythmically reactive, not stride)
- Bebop vocabulary in any improvised section (chromatic passing tones, enclosures, triplet figures)

**Known failure modes to watch for:**
- Model slows the tempo to something comfortable (150 BPM) and labels it bebop
- Melody is diatonic and stepwise rather than chromatic and leaping
- Piano plays full block chords on every beat (a beginner mistake, not bebop comping)
- Swing ratio collapses to straight eighths at high tempo
- AABA form is ignored — piece runs as a continuous texture

---

## Prompt 2 — Modal Jazz (Miles Davis / Kind of Blue Style)

**Prompt text:**
> Generate an original modal jazz piece in the style of Miles Davis's Kind of Blue. The tempo should be slow and spacious, around 60–75 BPM. Build the piece on a single Dorian mode — for example D Dorian — rather than fast-moving chord changes. The melody should be lyrical and sparse, leaving room for silence. Use a small jazz combo: muted trumpet or flugelhorn, piano, upright bass, and brushed drums. The harmonic texture should be static and meditative, with the soloist exploring the mode freely rather than navigating chord changes.

**Target duration:** 75–90 seconds

**Jazz-specific elements to evaluate:**
- Static, modal harmonic language (not cycling through ii–V–I changes)
- Correct modal colour — D Dorian has a raised 6th that distinguishes it from D natural minor
- Lyrical, spacious melody with deliberate use of silence (rests are musical, not absent)
- Brushed drums: light texture, not a loud swinging ride pattern
- Muted trumpet or flugelhorn timbre (warm, not bright)
- Absence of bebop vocabulary — this style deliberately avoids chromatic complexity

**Known failure modes to watch for:**
- Model defaults to fast harmonic movement because "jazz" triggers ii–V–I training patterns
- Incorrect Dorian colour (plays natural minor or major by mistake)
- Drums are too loud/busy for the meditative texture
- Piece is too short — modal jazz breathes slowly; 60 seconds may only be one or two phrases
- Melody is too ornate or bebop-like; Kind of Blue is famously simple and expressive

---

## Prompt 3 — Jazz Ballad with Lush Extensions

**Prompt text:**
> Generate an original jazz ballad at a slow tempo (around 50–60 BPM). The piece should feature lush chord extensions — major 9th, major 7th, minor 11th, and dominant 13th chords — creating a rich, romantic harmonic texture in the style of Bill Evans or Keith Jarrett. Use piano as the primary voice, supported by upright bass and light brushed drums. The melody should be singable and emotionally expressive. The harmonic language should include jazz reharmonisation and voice-leading movements where inner voices resolve smoothly while the bass moves independently.

**Target duration:** 60–90 seconds

**Jazz-specific elements to evaluate:**
- Chord extensions beyond triads and basic 7ths — 9ths, 11ths, 13ths audible in the voicings
- Smooth voice leading: inner voices moving by step while outer voices leap
- Singable, emotionally shaped melody — not a sequence of scalar runs
- Brushed drums, very light texture
- Walking or sustained bass complementing (not doubling) the piano
- Sense of harmonic colour and mood — ballads should feel like something

**Known failure modes to watch for:**
- Model uses simple triads or dominant 7ths only — ignores the extended harmony instruction
- Piano melody is busy and virtuosic (inappropriate for ballad style)
- Tempo too fast — if it's above 80 BPM it's probably not a ballad
- Drums are too present; in a piano ballad the drums should almost disappear
- Melody lacks contour — it plateaus at one register rather than arching

---

## Prompt 4 — 12-Bar Jazz Blues in Bb

**Prompt text:**
> Generate an original 12-bar jazz blues in Bb major at a medium swing tempo (around 130–140 BPM). Use the standard jazz blues chord progression: Bb7 – Eb7 – Bb7 – Bb7 / Eb7 – Edim7 – Bb7 – G7 / Cm7 – F7 – Bb7 – F7. Include a piano, upright bass, drums, and tenor saxophone. The saxophone should play a blues-inflected melody or riff over the changes. The piece should cycle through the 12-bar form at least twice. Use jazz blues vocabulary: blues scales, chromatic approach notes, bent notes, call-and-response between sax and piano.

**Target duration:** 60–75 seconds (to allow 2+ full cycles)

**Jazz-specific elements to evaluate:**
- Correct 12-bar jazz blues changes (not a simplified I–IV–V blues; the jazz version has the turnaround and passing chords)
- Blues inflection: flat 3rds, flat 7ths, bent notes in the melody
- Medium swing feel — this tempo should swing comfortably
- Call-and-response between saxophone and piano
- Tenor saxophone timbre (full, slightly raspy — not a soprano or alto sound)
- The form cycles cleanly — bar 13 should feel like a new beginning, not a random continuation

**Known failure modes to watch for:**
- Model uses a rock/pop I–IV–V blues instead of the jazz blues changes with passing chords
- Bb7 becomes Bbmaj7 (major 7th instead of dominant 7th — a fundamental error)
- Form doesn't cycle — piece plays through once and then wanders
- Swing feel is absent at this tempo (130 BPM is very achievable for human swing)
- Blues inflection is absent — melody sounds like generic jazz rather than blues-influenced jazz

---

## Prompt 5 — Up-Tempo Swing (Big Band / Count Basie Style)

**Prompt text:**
> Generate an original up-tempo swing piece in the style of Count Basie's big band, at approximately 180–200 BPM. Use a full big band arrangement: brass section (trumpets and trombones), saxophone section (alto, tenor, baritone), rhythm section (piano, guitar, upright bass, drums). Include the characteristic Basie elements: riff-based brass figures, call-and-response between the brass and saxophone sections, a walking bass line, a swinging ride cymbal pattern, and a moment where the full band drops to a sparse rhythm-section-only passage before building back up. The piece should feel like it's swinging hard.

**Target duration:** 75–90 seconds

**Jazz-specific elements to evaluate:**
- Full big band texture (brass + reeds + rhythm section, not a small combo)
- Section writing: brass and reeds as distinct blocks, not everyone playing in unison
- Call-and-response between sections — one of the most idiomatic big band devices
- Walking bass line at high tempo (bass should be articulating every beat)
- Ride cymbal pattern clearly audible in the drums
- Dynamic contrast: the full-band passage vs. the sparse drop-out moment
- Riff-based writing (short, repeated figures in the brass) — Basie's signature

**Known failure modes to watch for:**
- Model generates a small combo (piano trio, quartet) despite the explicit big band instruction
- All horns play in unison throughout — no section writing
- Tempo drifts or sits below 170 BPM (not a convincing "hard swing" feel)
- Rhythm section is buried under the horns — in big band, the rhythm section is the engine
- Piano plays too many notes (Basie's piano style is famously sparse — the "less is more" approach)

---

## Prompt 6 — Latin Jazz (Bossa Nova / Afro-Cuban)

**Prompt text:**
> Generate an original Latin jazz piece in either bossa nova or Afro-Cuban (mambo/cha-cha) style. If bossa nova: use a gentle, syncopated guitar rhythm pattern, soft samba-derived drum pattern, warm jazz chord extensions (major 7ths, 9ths), and a smooth melodic line at around 120–130 BPM. If Afro-Cuban: use clave rhythm (either son clave or rumba clave), congas and timbales in the percussion, brass stabs on the clave, and a montuno piano pattern at 160–180 BPM. Whichever style, the harmonic language should be jazz (extended chords, ii-V-I movements) not pop or salsa-pop.

**Target duration:** 60–90 seconds

**Jazz-specific elements to evaluate:**
- Correct rhythmic pattern for the chosen style (bossa nova guitar pattern OR clave-based Afro-Cuban percussion)
- Jazz harmonic language (extended chords, ii–V–I) not pop harmony
- For bossa nova: the characteristic syncopated guitar pattern where the bass note anticipates the beat
- For Afro-Cuban: clave rhythm present and consistent across all percussion voices
- Ensemble texture appropriate to the style (guitar + bass + brushed drums for bossa; percussion section for Afro-Cuban)
- The Latin feel and jazz harmony should coexist — neither swallowing the other

**Known failure modes to watch for:**
- Model generates generic jazz with no Latin rhythmic content — ignores the Latin instruction
- Bossa nova guitar pattern is absent or wrong (the pattern is very specific and well-documented)
- Clave rhythm is present but inconsistent — drops out in the middle of the piece
- Harmony reverts to simple triads or dominant 7ths, losing the jazz quality
- Model blends bossa and Afro-Cuban indiscriminately, producing neither convincingly
- Tempo is wrong for the chosen style (bossa at 200 BPM, or Afro-Cuban at 90 BPM)
