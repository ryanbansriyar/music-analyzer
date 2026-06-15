"""
chord_detection.py  —  Template-based chord detection from audio.

HOW IT WORKS
------------
We never need MIDI. Instead:

  1. CHROMA FEATURES
     librosa computes a chromagram — a 12-bin energy vector per frame,
     one bin per pitch class (C, C#, D, ..., B). Loud notes in that
     pitch class light up that bin.

  2. BEAT SYNCHRONISATION
     Rather than analysing every 23ms frame, we average the chroma within
     each detected beat. This gives one chroma vector per beat, which is
     the right timescale for chord changes in jazz (one chord per beat in
     bebop, one per bar in modal jazz).

  3. CHORD TEMPLATES
     We define 7 chord qualities × 12 roots = 84 templates. Each template
     is a 12-element binary vector with 1s on the pitch classes that belong
     to that chord type:
         major triad   : root, major 3rd (+4), perfect 5th (+7)
         minor triad   : root, minor 3rd (+3), perfect 5th (+7)
         dominant 7th  : root, M3, P5, minor 7th (+10)   ← the jazz workhorse
         major 7th     : root, M3, P5, major 7th (+11)   ← lush, Bill Evans style
         minor 7th     : root, m3, P5, minor 7th (+10)   ← ii chord in ii-V-I
         half-diminished: root, m3, dim 5th (+6), m7      ← ii chord in minor ii-V-I
         diminished 7th: root, m3, d5, dim 7th (+9)      ← passing chord, bebop vocab

  4. MATCHING
     For each beat, compute cosine similarity between the beat's chroma
     and every template. The best-matching template above a confidence
     threshold is the detected chord. Below threshold → "N" (no chord /
     uncertain).

  5. SEGMENTATION
     Consecutive beats with the same chord label are merged into a segment
     with a start time, end time, and duration.

  6. ANALYSIS
     From the chord sequence we derive:
       - Vocabulary breakdown (triad vs 7th vs uncertain)
       - Jazz complexity ratio (proportion that are 7th or richer)
       - ii-V-I progression detection

KNOWN LIMITATIONS
-----------------
- Template matching is polyphonic but coarse — it detects the dominant
  harmony, not every voice. A dense orchestral texture will confuse it.
- Altered chords (b9, #11, b13) don't have their own templates; they'll
  typically be matched to the nearest dominant 7th.
- This is a research tool. Cross-check interesting results by ear.

USAGE
-----
    python chord_detection.py ../pieces/piece_01.mp3
    python chord_detection.py --batch ../pieces/
    python chord_detection.py ../pieces/piece_01.mp3 --output chords.csv
"""

import argparse
import os
import sys
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Plot style  (consistent with all other scripts in this project)
# ---------------------------------------------------------------------------

PLOT_STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor": "#F7F7F7",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.dpi": 150,
}
plt.rcParams.update(PLOT_STYLE)

# ---------------------------------------------------------------------------
# Chord template definitions
# ---------------------------------------------------------------------------

# The 12 note names used for labelling detected chords.
# We use flats for enharmonic notes (Eb, Ab, Bb) because jazz musicians
# generally prefer flat keys — the circle of fifths for jazz runs flat.
NOTE_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

# Each template is a 12-element array indexed by semitone interval above the root.
# Index 0 = root, index 4 = major 3rd, index 7 = perfect 5th, etc.
# We start from C (index 0) and rotate to build all 12 roots.
_BASE_TEMPLATES = {
    "maj":   np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], dtype=float),
    "min":   np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0], dtype=float),
    "dom7":  np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], dtype=float),
    "maj7":  np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1], dtype=float),
    "min7":  np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0], dtype=float),
    "hdim7": np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0], dtype=float),
    "dim7":  np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0], dtype=float),
}

# Friendly display names for chord qualities
QUALITY_DISPLAY = {
    "maj":   "",        # C  (no suffix = major triad)
    "min":   "m",       # Cm
    "dom7":  "7",       # C7
    "maj7":  "maj7",    # Cmaj7
    "min7":  "m7",      # Cm7
    "hdim7": "m7b5",    # Cm7b5  (half-diminished = minor 7 flat 5)
    "dim7":  "dim7",    # Cdim7
}

# For the rubric: is this chord "jazz-complex" (7th or richer)?
QUALITY_IS_JAZZ = {
    "maj":   False,
    "min":   False,
    "dom7":  True,
    "maj7":  True,
    "min7":  True,
    "hdim7": True,
    "dim7":  True,
}

# Colours for the chord timeline and distribution chart
QUALITY_COLOUR = {
    "maj":   "#4878CF",   # blue
    "min":   "#6ACC65",   # green
    "dom7":  "#D65F5F",   # red  ← dominant chords carry the most tension in jazz
    "maj7":  "#B47CC7",   # purple
    "min7":  "#4EACC5",   # teal
    "hdim7": "#E07B00",   # orange
    "dim7":  "#C4AD66",   # gold
    "N":     "#DDDDDD",   # grey (uncertain / below threshold)
}

# Build the full 84-template library by rotating each base template
# np.roll(arr, n) shifts element 0 to position n, which is equivalent
# to transposing the chord up by n semitones.
ALL_TEMPLATES: dict[str, tuple[str, np.ndarray]] = {}  # chord_label → (quality, template)

for quality, base in _BASE_TEMPLATES.items():
    suffix = QUALITY_DISPLAY[quality]
    for semitone, root in enumerate(NOTE_NAMES):
        label = root + suffix
        ALL_TEMPLATES[label] = (quality, np.roll(base, semitone))

# Pre-normalise all templates (for faster cosine similarity later)
_TEMPLATE_MATRIX = np.stack([v for _, v in ALL_TEMPLATES.values()], axis=0)  # (84, 12)
_TEMPLATE_MATRIX /= np.linalg.norm(_TEMPLATE_MATRIX, axis=1, keepdims=True)
_TEMPLATE_LABELS = list(ALL_TEMPLATES.keys())
_TEMPLATE_QUALITIES = [q for q, _ in ALL_TEMPLATES.values()]

# Confidence threshold below which we label a beat "N" (no clear chord).
# Lower this if you want more chord guesses; raise it for fewer but surer ones.
CONFIDENCE_THRESHOLD = 0.65


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------

def detect_chords(audio_path: str) -> dict:
    """
    Run full chord detection on an audio file.

    Returns dict with:
        segments       : pd.DataFrame — one row per chord segment
                         columns: onset, offset, duration, chord, quality, confidence
        beat_chords    : list of (beat_time, chord_label, quality, confidence)
        tempo_bpm      : detected tempo
        vocab_counts   : Counter of chord labels
        quality_counts : Counter of chord quality (maj, min7, dom7, ...)
        jazz_ratio     : fraction of beats that are 7th-or-richer chords
        ii_V_I_count   : number of ii-V-I progressions in the segment sequence
    """
    print(f"  Loading: {Path(audio_path).name}")
    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # --- Tempo and beat tracking ---
    tempo_arr, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo_arr)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"  Tempo: {tempo:.1f} BPM  |  {len(beat_times)} beats")

    # --- Chroma (beat-synchronised) ---
    # CQT chroma is more pitch-accurate than STFT chroma for music.
    # bins_per_octave=36 (3× the default) gives better frequency resolution.
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=36)

    # Average chroma within each beat using the median (more robust to noise
    # than mean — a single loud transient won't dominate the whole beat).
    # librosa.util.sync returns N+1 columns for N beat_frames (one extra segment
    # before the first beat). Trim to len(beat_times) to keep shapes aligned.
    chroma_sync = librosa.util.sync(chroma, beat_frames, aggregate=np.median)
    chroma_sync = chroma_sync[:, :len(beat_times)]   # (12, n_beats)

    # --- Match each beat against all 84 chord templates ---
    # Normalise each beat's chroma vector, then compute dot product with
    # pre-normalised templates — that gives cosine similarity for every
    # (beat, template) pair in one matrix multiplication.
    norms = np.linalg.norm(chroma_sync, axis=0, keepdims=True)
    chroma_norm = chroma_sync / np.where(norms > 0, norms, 1.0)   # (12, n_beats)

    # similarities: (84 templates) × (n_beats) — each cell is cosine similarity
    similarities = _TEMPLATE_MATRIX @ chroma_norm   # (84, n_beats)

    best_idx = np.argmax(similarities, axis=0)       # index of best template per beat
    best_sim = similarities[best_idx, np.arange(len(beat_times))]  # confidence score

    beat_chords = []
    for i, (t, idx, conf) in enumerate(zip(beat_times, best_idx, best_sim)):
        if conf >= CONFIDENCE_THRESHOLD:
            label   = _TEMPLATE_LABELS[idx]
            quality = _TEMPLATE_QUALITIES[idx]
        else:
            label, quality = "N", "N"
        beat_chords.append((float(t), label, quality, float(conf)))

    # --- Merge consecutive identical chords into segments ---
    segments = _build_segments(beat_chords, total_duration=float(len(y) / sr))

    print(f"  Detected {len(segments)} chord segments  "
          f"(threshold = {CONFIDENCE_THRESHOLD})")

    # --- Vocabulary statistics ---
    from collections import Counter
    vocab_counts   = Counter(seg["chord"]   for seg in segments if seg["chord"] != "N")
    quality_counts = Counter(seg["quality"] for seg in segments if seg["quality"] != "N")

    total_beats = sum(1 for _, _, q, _ in beat_chords if q != "N")
    jazz_beats  = sum(1 for _, _, q, _ in beat_chords if QUALITY_IS_JAZZ.get(q, False))
    jazz_ratio  = jazz_beats / total_beats if total_beats else 0.0

    # --- ii-V-I detection ---
    chord_seq   = [seg["chord"]   for seg in segments if seg["chord"] != "N"]
    quality_seq = [seg["quality"] for seg in segments if seg["quality"] != "N"]
    ii_v_i_count = _count_ii_V_I(chord_seq, quality_seq)

    print(f"  Jazz complexity: {jazz_ratio:.0%}  |  ii-V-I progressions: {ii_v_i_count}")

    return {
        "file":          audio_path,
        "tempo_bpm":     tempo,
        "segments":      pd.DataFrame(segments),
        "beat_chords":   beat_chords,
        "vocab_counts":  vocab_counts,
        "quality_counts": quality_counts,
        "jazz_ratio":    jazz_ratio,
        "ii_V_I_count":  ii_v_i_count,
    }


def _build_segments(beat_chords: list, total_duration: float) -> list[dict]:
    """
    Merge consecutive beats sharing the same chord label into timed segments.

    Each segment: onset, offset, duration, chord, quality, confidence (mean).
    """
    if not beat_chords:
        return []

    segments = []
    cur_label, cur_quality = beat_chords[0][1], beat_chords[0][2]
    cur_start = beat_chords[0][0]
    cur_confs = [beat_chords[0][3]]

    for t, label, quality, conf in beat_chords[1:]:
        if label == cur_label:
            cur_confs.append(conf)
        else:
            segments.append({
                "onset":      cur_start,
                "offset":     t,
                "duration":   t - cur_start,
                "chord":      cur_label,
                "quality":    cur_quality,
                "confidence": float(np.mean(cur_confs)),
            })
            cur_label, cur_quality = label, quality
            cur_start = t
            cur_confs = [conf]

    # Final segment runs to the end of the audio
    segments.append({
        "onset":      cur_start,
        "offset":     total_duration,
        "duration":   total_duration - cur_start,
        "chord":      cur_label,
        "quality":    cur_quality,
        "confidence": float(np.mean(cur_confs)),
    })

    return segments


# ---------------------------------------------------------------------------
# ii-V-I detection
# ---------------------------------------------------------------------------

def _root_pc(chord_label: str) -> int:
    """
    Extract the pitch class (0=C … 11=B) of a chord's root.
    Handles both sharp (#) and flat (b) accidentals.
    """
    for root, pc in zip(
        ["C#", "Db", "D#", "Eb", "F#", "Gb", "G#", "Ab", "A#", "Bb", "B", "C",
         "D", "E", "F", "G", "A"],
        [1,     1,    3,    3,    6,    6,    8,    8,    10,   10,   11,  0,
         2,    4,    5,    7,    9],
    ):
        if chord_label.startswith(root):
            return pc
    return 0


def _count_ii_V_I(chord_seq: list[str], quality_seq: list[str]) -> int:
    """
    Count ii-V-I progressions in a chord sequence.

    A ii-V-I is:
      chord A: min7 or hdim7  (the ii chord)
      chord B: dom7            (the V chord — dominant tension)
      chord C: maj, maj7       (the I chord — resolution)

    Root movement: A → B is up a perfect 4th (+5 semitones),
                   B → C is up a perfect 4th (+5 semitones).

    This is the most fundamental harmonic motion in jazz. Charlie Parker
    built entire improvisations on ii-V-I cycles. A model that can't
    generate them hasn't learned jazz harmony at a structural level.
    """
    count = 0
    for i in range(len(chord_seq) - 2):
        qa, qb, qc = quality_seq[i], quality_seq[i+1], quality_seq[i+2]

        # Quality check
        if qa not in ("min7", "hdim7"):
            continue
        if qb != "dom7":
            continue
        if qc not in ("maj", "maj7"):
            continue

        # Root movement check: both steps should be up a perfect 4th (5 semitones)
        ra = _root_pc(chord_seq[i])
        rb = _root_pc(chord_seq[i+1])
        rc = _root_pc(chord_seq[i+2])

        if (rb - ra) % 12 == 5 and (rc - rb) % 12 == 5:
            count += 1

    return count


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_chord_timeline(result: dict, figures_dir: str) -> str:
    """
    Two-panel figure:
      Top   : chord timeline — horizontal bars showing which chord plays when,
               coloured by chord quality.
      Bottom : bar chart of the 12 most common chords, coloured by quality.

    Args:
        result      : dict returned by detect_chords()
        figures_dir : directory to save the figure

    Returns path to saved figure.
    """
    stem    = Path(result["file"]).stem
    segs    = result["segments"]
    tempo   = result["tempo_bpm"]
    jr      = result["jazz_ratio"]
    n_2v1   = result["ii_V_I_count"]

    fig, (ax_time, ax_bar) = plt.subplots(
        2, 1, figsize=(14, 8),
        gridspec_kw={"height_ratios": [3, 2]},
    )
    fig.suptitle(
        f"Chord Analysis — {stem}\n"
        f"tempo ≈ {tempo:.0f} BPM  |  "
        f"jazz complexity: {jr:.0%}  |  "
        f"ii-V-I progressions: {n_2v1}",
        fontsize=12, fontweight="bold",
    )

    # ---- Top panel: chord timeline ----
    present_chords = [
        seg["chord"] for _, seg in segs.iterrows()
        if seg["chord"] != "N"
    ]

    def _chord_quality(label: str) -> str:
        """Look up quality from ALL_TEMPLATES; fall back to 'maj'."""
        return ALL_TEMPLATES[label][0] if label in ALL_TEMPLATES else "maj"

    quality_rank = {"maj": 0, "maj7": 1, "dom7": 2, "min7": 3, "min": 4, "hdim7": 5, "dim7": 6}
    unique_chords = sorted(
        set(present_chords),
        key=lambda c: (_root_pc(c), quality_rank.get(_chord_quality(c), 9))
    )
    chord_to_y = {c: i for i, c in enumerate(unique_chords)}

    for _, seg in segs.iterrows():
        if seg["chord"] == "N":
            continue
        y = chord_to_y[seg["chord"]]
        colour = QUALITY_COLOUR.get(seg["quality"], "#AAAAAA")
        ax_time.barh(
            y, seg["duration"], left=seg["onset"],
            color=colour, edgecolor="white", linewidth=0.5, height=0.75,
            alpha=0.85,
        )
        # Label the bar if it's wide enough to fit text
        if seg["duration"] > 1.5:
            ax_time.text(
                seg["onset"] + seg["duration"] / 2, y,
                seg["chord"],
                ha="center", va="center", fontsize=7, color="white",
                fontweight="bold",
            )

    ax_time.set_yticks(range(len(unique_chords)))
    ax_time.set_yticklabels(unique_chords, fontsize=8)
    ax_time.set_xlabel("Time (seconds)")
    ax_time.set_ylabel("Chord")
    ax_time.set_xlim(0, segs["offset"].max())

    # Legend for chord qualities
    legend_patches = [
        mpatches.Patch(color=QUALITY_COLOUR[q], label=f"{QUALITY_DISPLAY[q] or 'major triad'} ({q})")
        for q in ["maj", "min", "dom7", "maj7", "min7", "hdim7", "dim7"]
        if q in result["quality_counts"] or True
    ]
    ax_time.legend(handles=legend_patches, loc="upper right",
                   ncol=4, fontsize=7.5, framealpha=0.9)

    # ---- Bottom panel: chord frequency bar chart ----
    top_chords = result["vocab_counts"].most_common(14)
    if top_chords:
        ch_labels, ch_counts = zip(*top_chords)
        ch_colours = [
            QUALITY_COLOUR.get(_chord_quality(c), "#AAAAAA")
            for c in ch_labels
        ]

        bars = ax_bar.bar(range(len(ch_labels)), ch_counts,
                          color=ch_colours, edgecolor="white", linewidth=0.7)
        ax_bar.set_xticks(range(len(ch_labels)))
        ax_bar.set_xticklabels(ch_labels, rotation=30, ha="right", fontsize=9)
        ax_bar.set_ylabel("Occurrences (beats)")
        ax_bar.set_title("Most Common Chords")
        for bar, count in zip(bars, ch_counts):
            ax_bar.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.2, str(count),
                        ha="center", va="bottom", fontsize=8)
    else:
        ax_bar.text(0.5, 0.5, "No chords detected above threshold",
                    ha="center", va="center", transform=ax_bar.transAxes, color="#888")

    plt.tight_layout()
    os.makedirs(figures_dir, exist_ok=True)
    out_path = os.path.join(figures_dir, f"{stem}_chord_timeline.png")
    plt.savefig(out_path)
    plt.close(fig)
    print(f"  Figure saved: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Batch processing + summary plot
# ---------------------------------------------------------------------------

def _plot_batch_summary(rows: list[dict], figures_dir: str) -> str:
    """
    Summary bar chart: jazz complexity and ii-V-I count across all pieces.
    """
    if not rows:
        return ""

    labels     = [str(r["piece"])[:20] for r in rows]
    jazz_ratios = [r["jazz_ratio"] for r in rows]
    ii_v_i      = [r["ii_V_I_count"] for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))
    fig.suptitle("Batch Harmonic Summary", fontsize=13, fontweight="bold")

    x = np.arange(len(labels))
    ax1.bar(x, jazz_ratios, color="#4878CF", edgecolor="white", linewidth=0.7)
    ax1.axhline(0.7, color="#227722", linewidth=1.2, linestyle="--",
                label="≥ 0.7 = strong jazz harmony")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax1.set_ylabel("Jazz complexity ratio\n(fraction of beats with 7th+ chord)")
    ax1.set_ylim(0, 1.05)
    ax1.set_title("Jazz Harmonic Complexity")
    ax1.legend(fontsize=8)

    ax2.bar(x, ii_v_i, color="#D65F5F", edgecolor="white", linewidth=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax2.set_ylabel("Count")
    ax2.set_title("ii-V-I Progressions Detected")
    for i, v in enumerate(ii_v_i):
        if v > 0:
            ax2.text(i, v + 0.05, str(v), ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    out_path = os.path.join(figures_dir, "batch_chord_summary.png")
    plt.savefig(out_path)
    plt.close(fig)
    print(f"  Batch summary saved: {out_path}")
    return out_path


def batch_analyze(directory: str, figures_dir: str = "../figures") -> pd.DataFrame:
    """
    Run detect_chords + plot_chord_timeline on every audio file in a directory.
    Returns a summary DataFrame and saves per-piece chord CSVs.
    """
    audio_exts = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".ogg", ".m4a"}
    files = sorted(p for p in Path(directory).iterdir()
                   if p.is_file() and p.suffix.lower() in audio_exts)

    if not files:
        print(f"No audio files found in {directory}")
        return pd.DataFrame()

    print(f"Found {len(files)} audio files\n")
    summary_rows = []

    for path in files:
        try:
            result = detect_chords(str(path))
            plot_chord_timeline(result, figures_dir)

            # Save per-piece chord sequence CSV
            os.makedirs(figures_dir, exist_ok=True)
            chord_csv = os.path.join(
                str(Path(figures_dir).parent / "results" / "notes"),
                f"{path.stem}_chords.csv",
            )
            os.makedirs(Path(chord_csv).parent, exist_ok=True)
            result["segments"].to_csv(chord_csv, index=False)
            print(f"  Chord sequence saved: {chord_csv}\n")

            summary_rows.append({
                "piece":         path.stem,
                "tempo_bpm":     result["tempo_bpm"],
                "jazz_ratio":    result["jazz_ratio"],
                "ii_V_I_count":  result["ii_V_I_count"],
                "top_chord":     result["vocab_counts"].most_common(1)[0][0]
                                 if result["vocab_counts"] else "—",
                "n_unique_chords": len(result["vocab_counts"]),
            })
        except Exception as exc:
            print(f"  ERROR on {path.name}: {exc}\n")
            summary_rows.append({"piece": path.stem, "error": str(exc)})

    df = pd.DataFrame(summary_rows)
    _plot_batch_summary(
        [r for r in summary_rows if "jazz_ratio" in r],
        figures_dir,
    )
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Template-based chord detection from jazz audio.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python chord_detection.py ../pieces/piece_01.mp3
  python chord_detection.py --batch ../pieces/
  python chord_detection.py ../pieces/piece_01.mp3 --output chords.csv
        """,
    )
    parser.add_argument("input", nargs="?", help="Single audio file path")
    parser.add_argument("--batch", metavar="DIR",
                        help="Process all audio files in this directory")
    parser.add_argument("--figures", default="../figures",
                        help="Output directory for figures (default: ../figures)")
    parser.add_argument("--output", metavar="CSV",
                        help="Save chord segments to this CSV (single-file mode)")
    parser.add_argument("--threshold", type=float, default=CONFIDENCE_THRESHOLD,
                        help=f"Confidence threshold 0-1 (default: {CONFIDENCE_THRESHOLD})")

    args = parser.parse_args()

    # Allow threshold to be overridden from CLI
    import chord_detection as _self
    _self.CONFIDENCE_THRESHOLD = args.threshold

    if args.batch:
        df = batch_analyze(args.batch, figures_dir=args.figures)
        if not df.empty:
            print("\nBatch summary:")
            print(df.to_string(index=False))

    elif args.input:
        result = detect_chords(args.input)
        plot_chord_timeline(result, args.figures)

        print("\nTop 10 chords:")
        for chord, count in result["vocab_counts"].most_common(10):
            print(f"  {chord:8s}  {count:3d} beats")

        if args.output:
            result["segments"].to_csv(args.output, index=False)
            print(f"\nChord sequence saved to {args.output}")
        else:
            print("\nChord sequence (first 20 segments):")
            print(result["segments"].head(20).to_string(index=False))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
