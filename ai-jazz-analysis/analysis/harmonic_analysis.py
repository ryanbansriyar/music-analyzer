"""
harmonic_analysis.py  —  Chord vocabulary and harmony analysis for the AI jazz evaluation.

NOTE ON AUDIO-ONLY MODELS
--------------------------
This script operates on MIDI input. Four of the five models evaluated
(Suno, Udio, MusicGen, Stable Audio 2) produce audio files, not MIDI.
To use this script on those outputs you first need to transcribe the audio
to MIDI. The recommended tool is Spotify's Basic Pitch:

    pip install basic-pitch
    basic-pitch output_midi/ p iece_01.mp3

Basic Pitch uses a neural network trained on music data and handles
polyphonic audio reasonably well. Be aware that transcription is not
perfect — some chords will be misread, especially in busy textures.
Treat harmonic analysis of transcribed MIDI as approximate.

AIVA outputs MIDI directly. Run this script on AIVA files without any
transcription step.

WHAT THIS MEASURES
------------------
Jazz harmony is built on extensions beyond the triad. A C major triad
(C-E-G) has no jazz character on its own; it becomes idiomatic when extended
to Cmaj7, Cmaj9, or Cmaj9#11. This script counts how much of a piece lives
in triad-land versus seventh-chord-land versus full jazz extensions.

The jazz complexity ratio — proportion of chords that are 7th or beyond —
is a single number that summarises harmonic sophistication. A well-voiced
jazz standard should be above 0.7. A generic pop piece labelled as "jazz"
will typically be 0.2–0.4.

ii-V-I progressions are the DNA of jazz harmony. Almost every standard
contains them; if a model can't generate them, it has not learned jazz at
the chord-progression level, regardless of timbre.

USAGE
-----
    python harmonic_analysis.py ../pieces/piece_01.mid
    python harmonic_analysis.py --batch ../pieces/
    python harmonic_analysis.py --batch ../pieces/ --output harmony_results.csv
"""

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from music21 import chord, note
from music21 import converter as m21converter

# ---------------------------------------------------------------------------
# Consistent publication-ready plot style (same dict as swing_ratio.py)
# ---------------------------------------------------------------------------

PLOT_STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor": "#F7F7F7",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.4,
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "legend.framealpha": 0.85,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.dpi": 150,
}
plt.rcParams.update(PLOT_STYLE)

# Colour per model — same as swing_ratio.py for visual consistency
MODEL_COLOURS = {
    "suno":         "#4878CF",
    "udio":         "#6ACC65",
    "musicgen":     "#D65F5F",
    "stable_audio": "#B47CC7",
    "aiva":         "#C4AD66",
    "unknown":      "#AAAAAA",
}

# Colours for chord complexity bars
COMPLEXITY_COLOURS = {
    "triad":    "#4878CF",
    "seventh":  "#6ACC65",
    "extended": "#D65F5F",
    "altered":  "#B47CC7",
    "other":    "#C4AD66",
}

MIDI_EXTENSIONS = {".mid", ".midi"}


# ---------------------------------------------------------------------------
# Chord classification
# ---------------------------------------------------------------------------

def classify_chord(c: chord.Chord) -> str:
    """
    Classify a music21 Chord into a complexity category.

    Categories (from simplest to richest):
      'triad'    — 3 distinct pitch classes (major, minor, diminished, augmented)
      'seventh'  — 4 distinct pitch classes (maj7, dom7, min7, half-dim, dim7)
      'extended' — 5+ distinct pitch classes (9ths, 11ths, 13ths)
      'altered'  — dominant 7th with b9, #9, b5/#11, or b13 (jazz-specific tension)
      'other'    — dyads, clusters, or unrecognised structures

    Why this matters: jazz harmony is defined by its extension practice. A
    piece built on triads sounds like folk music regardless of the tempo or
    instrumentation. Sevenths are the minimum jazz entry point; extended and
    altered chords are the real vocabulary.
    """
    if not isinstance(c, chord.Chord) or len(c.pitches) < 2:
        return "other"

    name = (c.commonName or "").lower()
    # Count distinct pitch classes (C and C# are different pitch classes)
    pc_count = len({p.pitchClass for p in c.pitches})

    # Altered chords: dominant 7ths with tension tones (the spiciest jazz chords)
    altered_keywords = [
        "flat nine", "sharp nine", "flat five",
        "sharp eleven", "flat thirteen",
        "augmented seventh",  # aug7 = dominant with raised 5th
        "diminished seventh", # fully-dim: common in jazz as passing chord
    ]
    if any(kw in name for kw in altered_keywords):
        return "altered"

    if pc_count >= 5:
        return "extended"   # 9th, 11th, or 13th chord

    if pc_count == 4:
        return "seventh"    # any 7th chord

    if pc_count == 3:
        return "triad"

    return "other"


# ---------------------------------------------------------------------------
# ii-V-I detection
# ---------------------------------------------------------------------------

def _semitones_above_tonic(note_name: str, tonic_name: str) -> int:
    """
    Return how many semitones note_name is above tonic_name (0–11).
    Uses music21's Pitch class for enharmonic correctness.
    """
    from music21 import pitch as m21pitch
    return (m21pitch.Pitch(note_name).midi - m21pitch.Pitch(tonic_name).midi) % 12


def is_two_five_one(root_a: str, root_b: str, root_c: str, tonic: str) -> bool:
    """
    Return True if root_a / root_b / root_c form a ii-V-I in the given tonic.

    In C major:  ii = D (2 semitones above C)
                  V = G (7 semitones above C)
                  I = C (0 semitones above C)

    This works in any key — we measure intervals above the tonic, so the
    same logic applies to a piece in Bb or F#.
    """
    try:
        return (
            _semitones_above_tonic(root_a, tonic) == 2 and
            _semitones_above_tonic(root_b, tonic) == 7 and
            _semitones_above_tonic(root_c, tonic) == 0
        )
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Pitch-class baselines for comparison
# ---------------------------------------------------------------------------

# Approximate pitch-class distributions from corpus studies.
# Index 0 = C, 1 = C#/Db, ..., 11 = B.
# Jazz: relatively flat — chromaticism and non-diatonic tones used freely.
# Pop/rock: strong diatonic bias toward the major-scale notes of C major.

JAZZ_PC_BASELINE = np.array([
    0.112, 0.062, 0.095, 0.058, 0.089, 0.079,
    0.064, 0.098, 0.057, 0.085, 0.060, 0.041,
])
JAZZ_PC_BASELINE /= JAZZ_PC_BASELINE.sum()

POP_PC_BASELINE = np.array([
    0.148, 0.030, 0.108, 0.028, 0.124, 0.096,
    0.032, 0.142, 0.027, 0.106, 0.029, 0.130,
])
POP_PC_BASELINE /= POP_PC_BASELINE.sum()

PC_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_harmony(midi_path: str) -> dict:
    """
    Full harmonic analysis of a MIDI file using music21.

    Args:
        midi_path : path to a .mid or .midi file

    Returns dict with:
        key_name           : tonic note name (e.g. "D")
        mode               : "major" or "minor"
        chord_counts       : dict mapping category → count
                             categories: triad, seventh, extended, altered, other
        total_chords       : total number of chords analysed (int)
        jazz_complexity_ratio : proportion of chords that are 7th or beyond
                               (seventh + extended + altered) / total
                               A jazz piece should be > 0.7; pop-labelled-jazz < 0.4
        ii_V_I_count       : number of ii-V-I progressions detected (int)
        pitch_class_dist   : np.ndarray of shape (12,), normalised
        jazz_pc_similarity : cosine similarity to jazz pitch-class baseline
        pop_pc_similarity  : cosine similarity to pop/rock baseline
    """
    print(f"  Loading: {midi_path}")
    score = m21converter.parse(midi_path)

    # --- Key detection ---
    # music21's Krumhansl-Schmuckler key-finding algorithm
    detected_key = score.analyze("key")
    key_name = detected_key.tonic.name
    mode = detected_key.mode
    print(f"  Detected key: {key_name} {mode}")

    # --- Chord extraction ---
    # chordify() collapses all simultaneous notes into chord objects,
    # regardless of which instrument plays them. This gives us a harmonic
    # reduction of the full score.
    chordified = score.chordify()
    all_chords = list(chordified.flatten().getElementsByClass(chord.Chord))
    print(f"  Total chord objects: {len(all_chords)}")

    chord_counts = Counter()
    chord_roots = []  # for ii-V-I sliding-window scan

    for c in all_chords:
        # Grace notes and very short chords are passing tones, not harmony
        if c.duration.quarterLength < 0.25:
            continue
        category = classify_chord(c)
        chord_counts[category] += 1
        try:
            chord_roots.append(c.root().name)
        except Exception:
            chord_roots.append(None)

    total_chords = sum(chord_counts.values())

    # Jazz complexity ratio: what fraction of chords are 7th or richer?
    # A piece that uses nothing but triads has ratio 0.0; a bebop head
    # with dense harmony should be 0.7 or higher.
    jazz_complex_count = (
        chord_counts.get("seventh", 0) +
        chord_counts.get("extended", 0) +
        chord_counts.get("altered", 0)
    )
    jazz_complexity_ratio = jazz_complex_count / total_chords if total_chords else 0.0

    # --- ii-V-I detection ---
    # Slide a window of 3 consecutive roots over the chord sequence.
    # Even a single ii-V-I indicates the model has learned functional jazz harmony.
    valid_roots = [r for r in chord_roots if r is not None]
    ii_v_i_count = sum(
        1 for i in range(len(valid_roots) - 2)
        if is_two_five_one(valid_roots[i], valid_roots[i+1], valid_roots[i+2], key_name)
    )

    # --- Pitch-class distribution ---
    # Count all individual note events (not chord objects) for raw pitch usage.
    all_notes = list(score.flatten().getElementsByClass(note.Note))
    pc_counts = np.zeros(12)
    for n in all_notes:
        pc_counts[n.pitch.pitchClass] += 1

    pc_dist = pc_counts / pc_counts.sum() if pc_counts.sum() > 0 else np.ones(12) / 12.0

    # Cosine similarity: how close is this piece's pitch profile to each baseline?
    def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.dot(a, b) / denom) if denom > 0 else 0.0

    jazz_sim = cosine_sim(pc_dist, JAZZ_PC_BASELINE)
    pop_sim  = cosine_sim(pc_dist, POP_PC_BASELINE)

    result = {
        "file":                  midi_path,
        "key_name":              key_name,
        "mode":                  mode,
        "chord_counts":          dict(chord_counts),
        "total_chords":          total_chords,
        "jazz_complexity_ratio": jazz_complexity_ratio,
        "ii_V_I_count":          ii_v_i_count,
        "pitch_class_dist":      pc_dist,
        "jazz_pc_similarity":    jazz_sim,
        "pop_pc_similarity":     pop_sim,
    }

    # Print a compact summary so results are visible in the terminal
    print(f"  Key: {key_name} {mode}  |  chords: {total_chords}  |  "
          f"jazz complexity: {jazz_complexity_ratio:.2f}  |  ii-V-I: {ii_v_i_count}")

    return result


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_chord_complexity(midi_path: str, figures_dir: str = "../figures") -> str:
    """
    Bar chart of chord complexity distribution for one MIDI file.

    Calls analyze_harmony() internally. Saves the figure to figures_dir.

    Args:
        midi_path   : path to the MIDI file
        figures_dir : directory to save figure (created if needed)

    Returns:
        Path to the saved figure file.
    """
    result = analyze_harmony(midi_path)
    stem = Path(midi_path).stem

    categories = ["triad", "seventh", "extended", "altered", "other"]
    counts  = [result["chord_counts"].get(cat, 0) for cat in categories]
    colours = [COMPLEXITY_COLOURS[cat] for cat in categories]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: chord complexity bar chart
    ax = axes[0]
    bars = ax.bar(categories, counts, color=colours, edgecolor="white", linewidth=0.8)
    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.3,
                    str(count),
                    ha="center", va="bottom", fontsize=10)

    ax.set_xlabel("Chord complexity")
    ax.set_ylabel("Count")
    ax.set_title(
        f"Chord Vocabulary — {stem}\n"
        f"key: {result['key_name']} {result['mode']}  |  "
        f"jazz complexity: {result['jazz_complexity_ratio']:.0%}  |  "
        f"ii-V-I: {result['ii_V_I_count']}"
    )

    # Right: pitch-class distribution vs. baselines
    ax2 = axes[1]
    x = np.arange(12)
    w = 0.27
    ax2.bar(x - w,  result["pitch_class_dist"], w, label="This piece",   color="#4878CF", alpha=0.85)
    ax2.bar(x,      JAZZ_PC_BASELINE,            w, label="Jazz baseline",color="#6ACC65", alpha=0.85)
    ax2.bar(x + w,  POP_PC_BASELINE,             w, label="Pop baseline", color="#D65F5F", alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels(PC_NAMES, fontsize=8)
    ax2.set_xlabel("Pitch class")
    ax2.set_ylabel("Proportion")
    ax2.set_title(
        f"Pitch-Class Distribution — {stem}\n"
        f"jazz sim: {result['jazz_pc_similarity']:.3f}  |  "
        f"pop sim: {result['pop_pc_similarity']:.3f}"
    )
    ax2.legend()

    plt.tight_layout()
    os.makedirs(figures_dir, exist_ok=True)
    out_path = os.path.join(figures_dir, f"{stem}_harmony.png")
    plt.savefig(out_path)
    plt.close(fig)
    print(f"  Figure saved: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def batch_analyze(
    directory: str,
    figures_dir: str = "../figures",
) -> pd.DataFrame:
    """
    Run analyze_harmony and plot_chord_complexity on every MIDI file in a directory.

    Args:
        directory   : folder containing .mid / .midi files
        figures_dir : where to save per-piece figures

    Returns:
        pd.DataFrame with one row per file, columns:
            piece_id, key_name, mode, total_chords, n_triads, n_sevenths,
            n_extended, n_altered, jazz_complexity_ratio, ii_V_I_count,
            jazz_pc_similarity, pop_pc_similarity
    """
    midi_files = sorted([
        p for p in Path(directory).iterdir()
        if p.is_file() and p.suffix.lower() in MIDI_EXTENSIONS
    ])

    if not midi_files:
        print(f"No MIDI files found in {directory}")
        print("Tip: run  basic-pitch output_midi/ <audio_file>  to transcribe audio to MIDI.")
        return pd.DataFrame()

    print(f"Found {len(midi_files)} MIDI files in {directory}")
    rows = []

    for path in midi_files:
        try:
            result = analyze_harmony(str(path))
            plot_chord_complexity(str(path), figures_dir=figures_dir)
            rows.append({
                "piece_id":              path.stem,
                "key_name":              result["key_name"],
                "mode":                  result["mode"],
                "total_chords":          result["total_chords"],
                "n_triads":              result["chord_counts"].get("triad", 0),
                "n_sevenths":            result["chord_counts"].get("seventh", 0),
                "n_extended":            result["chord_counts"].get("extended", 0),
                "n_altered":             result["chord_counts"].get("altered", 0),
                "jazz_complexity_ratio": result["jazz_complexity_ratio"],
                "ii_V_I_count":          result["ii_V_I_count"],
                "jazz_pc_similarity":    result["jazz_pc_similarity"],
                "pop_pc_similarity":     result["pop_pc_similarity"],
            })
        except Exception as exc:
            print(f"  ERROR on {path.name}: {exc}")
            rows.append({"piece_id": path.stem, "error": str(exc)})

    df = pd.DataFrame(rows)
    print(f"\nBatch complete. {len(df)} files processed.")
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harmonic analysis of MIDI files using music21.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python harmonic_analysis.py ../pieces/piece_01.mid
  python harmonic_analysis.py ../pieces/piece_01.mid --figures ../figures
  python harmonic_analysis.py --batch ../pieces/
  python harmonic_analysis.py --batch ../pieces/ --output harmony_results.csv

Audio-only files must be converted to MIDI first:
  pip install basic-pitch
  basic-pitch output_midi/ piece_01.mp3
        """,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a single MIDI file",
    )
    parser.add_argument(
        "--batch",
        metavar="DIR",
        help="Process all MIDI files in this directory",
    )
    parser.add_argument(
        "--figures",
        default="../figures",
        metavar="DIR",
        help="Directory for output figures (default: ../figures)",
    )
    parser.add_argument(
        "--output",
        metavar="CSV",
        help="(Batch only) Save results DataFrame to this CSV path",
    )

    args = parser.parse_args()

    if args.batch:
        df = batch_analyze(args.batch, figures_dir=args.figures)
        if args.output and not df.empty:
            df.to_csv(args.output, index=False)
            print(f"Results saved to {args.output}")
        elif not df.empty:
            print("\nSummary:")
            print(df.to_string(index=False))

    elif args.input:
        plot_chord_complexity(args.input, figures_dir=args.figures)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
