"""
results_dashboard.py  —  Combined harmonic + rhythmic analysis and visual summary.

Since basic-pitch doesn't yet support Python 3.13, harmonic analysis runs
directly on audio using librosa chroma features instead of MIDI. This gives
us four meaningful harmonic metrics without needing a transcription step:

  KEY DETECTION
    Krumhansl-Kessler key-finding: correlate the mean chroma vector with
    rotated major/minor pitch-class profiles. The key whose profile best
    matches the actual pitch-class usage wins. This is the same algorithm
    used inside music21 and most MIR key detectors.

  PITCH-CLASS DISTRIBUTION + JAZZ SIMILARITY
    The 12-bin chroma histogram, normalised. Compared via cosine similarity
    to empirical jazz and pop/rock baselines. Jazz has a flatter, more
    chromatic distribution; pop/rock clusters heavily on diatonic tones.

  HARMONIC COMPLEXITY  (0–1, higher = richer harmony)
    Shannon entropy of the chroma frame, averaged over time.
    A triad fills 3/12 bins → low entropy (~0.5).
    A dense jazz voicing with extensions fills 5–7 bins → higher entropy.
    We normalise by log2(12) to put the range in [0, 1].

  HARMONIC CHANGE RATE  (higher = faster-moving harmony)
    Mean L1 distance between consecutive chroma frames.
    Bebop: high rate (chord changes every beat).
    Modal jazz: low rate (one chord for 16 bars).
    This distinguishes style even when key detection is uncertain.

USAGE
-----
    python results_dashboard.py
    python results_dashboard.py --pieces ../pieces --figures ../figures
"""

import argparse
import os
import sys
from pathlib import Path

import librosa
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

# ---------------------------------------------------------------------------
# Plot style  (same as the other scripts)
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
    "legend.fontsize": 9,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.dpi": 150,
}
plt.rcParams.update(PLOT_STYLE)

# ---------------------------------------------------------------------------
# Jazz / pop pitch-class baselines  (same values as harmonic_analysis.py)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Krumhansl-Kessler key profiles
# These 12-element vectors describe how likely each pitch class is in a
# given key. C major starts at index 0; rotating by N shifts to key N.
# ---------------------------------------------------------------------------

KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                     2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                     2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".ogg", ".m4a"}


# ---------------------------------------------------------------------------
# Chroma-based harmonic analysis
# ---------------------------------------------------------------------------

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def detect_key(mean_chroma: np.ndarray) -> tuple[str, str]:
    """
    Estimate key and mode via Krumhansl-Kessler profile correlation.

    Tries all 12 rotations of the major and minor profiles and returns
    the key whose profile has the highest Pearson correlation with the
    actual mean chroma vector.
    """
    best_r = -np.inf
    best_key, best_mode = "C", "major"

    for i in range(12):
        r_maj, _ = pearsonr(mean_chroma, np.roll(KK_MAJOR, i))
        if r_maj > best_r:
            best_r, best_key, best_mode = r_maj, NOTE_NAMES[i], "major"

        r_min, _ = pearsonr(mean_chroma, np.roll(KK_MINOR, i))
        if r_min > best_r:
            best_r, best_key, best_mode = r_min, NOTE_NAMES[i], "minor"

    return best_key, best_mode


def analyze_harmony_audio(audio_path: str) -> dict:
    """
    Chroma-based harmonic analysis of an audio file.

    Args:
        audio_path : path to any librosa-readable audio file

    Returns dict with:
        key            : detected key + mode string, e.g. "D minor"
        jazz_sim       : cosine similarity to jazz pitch-class baseline (0–1)
        pop_sim        : cosine similarity to pop/rock baseline (0–1)
        complexity     : normalised mean chroma entropy (0–1)
                         ~0.4 = triad-level; ~0.6 = extended jazz voicings
        change_rate    : mean frame-to-frame chroma change (0+, arb. units)
                         higher = faster harmonic movement (bebop-like)
        pc_dist        : np.ndarray(12) — raw pitch-class distribution
    """
    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # CQT chroma with 36 bins/octave gives better pitch resolution than STFT
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=36)

    # Mean chroma across the whole piece → pitch-class distribution
    mean_chroma = chroma.mean(axis=1)
    pc_dist = mean_chroma / (mean_chroma.sum() + 1e-8)

    key_name, mode = detect_key(mean_chroma)

    jazz_sim = _cosine_sim(pc_dist, JAZZ_PC_BASELINE)
    pop_sim  = _cosine_sim(pc_dist, POP_PC_BASELINE)

    # Chroma entropy: normalise each frame to a probability distribution,
    # then compute Shannon entropy. Mean entropy / log2(12) → [0, 1].
    chroma_norm = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-8)
    # Clip to avoid log(0) — a bin with 0 energy contributes 0 to entropy
    entropy_per_frame = -np.sum(
        chroma_norm * np.log2(np.clip(chroma_norm, 1e-8, 1.0)), axis=0
    )
    complexity = float(entropy_per_frame.mean()) / np.log2(12)

    # Harmonic change rate: L1 norm of chroma difference between frames
    chroma_diff = np.abs(np.diff(chroma_norm, axis=1)).sum(axis=0)
    change_rate = float(chroma_diff.mean())

    return {
        "key":         f"{key_name} {mode}",
        "jazz_sim":    float(jazz_sim),
        "pop_sim":     float(pop_sim),
        "complexity":  float(complexity),
        "change_rate": float(change_rate),
        "pc_dist":     pc_dist,
    }


# ---------------------------------------------------------------------------
# Colour helpers for the table
# ---------------------------------------------------------------------------

def _score_colour(val: float, lo: float, hi: float,
                  low_colour=(0.94, 0.55, 0.50),
                  mid_colour=(1.00, 0.92, 0.68),
                  hi_colour=(0.67, 0.87, 0.64)) -> tuple:
    """
    Linear interpolation from low_colour → mid_colour → hi_colour.
    val is clamped to [lo, hi] then mapped to [0, 1].
    """
    t = np.clip((val - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    if t < 0.5:
        s = t * 2
        return tuple(low_colour[i] * (1 - s) + mid_colour[i] * s for i in range(3))
    else:
        s = (t - 0.5) * 2
        return tuple(mid_colour[i] * (1 - s) + hi_colour[i] * s for i in range(3))


def _neutral() -> tuple:
    return (0.93, 0.93, 0.93)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def build_dashboard(df: pd.DataFrame, figures_dir: str) -> str:
    """
    Build and save the results dashboard figure.

    Layout:
      Top   : colour-coded results table (all pieces × all metrics)
      Bottom: side-by-side bar charts for swing ratio and harmonic complexity
    """
    n = len(df)

    # ---- Prepare display values ----
    # Shorten long piece names for the table
    def shorten(name: str, max_len: int = 22) -> str:
        return name if len(name) <= max_len else name[:max_len - 1] + "…"

    col_labels = [
        "Piece", "Tempo\n(BPM)", "Swing\nRatio", "Key",
        "Jazz PC\nSim", "Harmonic\nComplexity", "Harm.\nChange",
    ]

    table_data = []
    cell_colours = []

    for _, row in df.iterrows():
        swing  = row.get("mean_ratio", np.nan)
        tempo  = row.get("tempo_bpm", np.nan)
        jsim   = row.get("jazz_sim", np.nan)
        comp   = row.get("complexity", np.nan)
        chrate = row.get("change_rate", np.nan)

        table_data.append([
            shorten(row["label"]),
            f"{tempo:.0f}" if not np.isnan(tempo) else "—",
            f"{swing:.2f}" if not np.isnan(swing) else "—",
            row.get("key", "—"),
            f"{jsim:.3f}" if not np.isnan(jsim) else "—",
            f"{comp:.3f}" if not np.isnan(comp) else "—",
            f"{chrate:.3f}" if not np.isnan(chrate) else "—",
        ])

        # Colour each cell independently
        row_colours = [
            _neutral(),                                                  # piece name
            _neutral(),                                                  # tempo (neutral)
            _score_colour(swing, 1.0, 2.2) if not np.isnan(swing) else _neutral(),
            _neutral(),                                                  # key (text)
            _score_colour(jsim,  0.90, 1.00) if not np.isnan(jsim) else _neutral(),
            _score_colour(comp,  0.45, 0.70) if not np.isnan(comp) else _neutral(),
            _score_colour(chrate, 0.01, 0.12) if not np.isnan(chrate) else _neutral(),
        ]
        cell_colours.append(row_colours)

    # ---- Figure layout ----
    fig = plt.figure(figsize=(14, 4.5 + n * 0.55))
    fig.patch.set_facecolor("white")

    gs = gridspec.GridSpec(
        2, 2,
        figure=fig,
        height_ratios=[n * 0.55 + 1.5, 3.5],
        hspace=0.45,
        wspace=0.35,
    )

    ax_table = fig.add_subplot(gs[0, :])
    ax_swing  = fig.add_subplot(gs[1, 0])
    ax_harm   = fig.add_subplot(gs[1, 1])

    # ---- Table ----
    ax_table.axis("off")
    ax_table.set_title(
        "AI Jazz Analysis — Harmonic & Rhythmic Results\n"
        "Colour: red = low / amber = mid / green = high  |  "
        "Swing ref: 1.0 straight · 1.5 medium · 2.0 hard",
        loc="left", fontsize=11, fontweight="bold", pad=10,
    )

    tbl = ax_table.table(
        cellText=table_data,
        colLabels=col_labels,
        cellColours=cell_colours,
        colColours=[_neutral()] * len(col_labels),
        cellLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9.5)
    tbl.scale(1.0, 1.55)

    # Bold the header row
    for j in range(len(col_labels)):
        tbl[0, j].set_text_props(fontweight="bold")
        tbl[0, j].set_facecolor("#DDDDDD")

    # ---- Swing ratio bar chart ----
    labels = [shorten(r["label"], 16) for _, r in df.iterrows()]
    swings = df["mean_ratio"].fillna(0).tolist()
    stds   = df["std_ratio"].fillna(0).tolist()

    swing_colours = [
        _score_colour(v, 1.0, 2.2) if v > 0 else _neutral()
        for v in swings
    ]

    y_pos = np.arange(n)
    ax_swing.barh(y_pos, swings, xerr=stds, color=swing_colours,
                  edgecolor="white", linewidth=0.7, capsize=3, error_kw={"linewidth": 1})
    ax_swing.set_yticks(y_pos)
    ax_swing.set_yticklabels(labels, fontsize=8)
    ax_swing.invert_yaxis()
    ax_swing.axvline(1.0, color="#CC3333", linewidth=1.1, linestyle="--", label="straight")
    ax_swing.axvline(1.5, color="#E07B00", linewidth=1.1, linestyle="--", label="medium")
    ax_swing.axvline(2.0, color="#227722", linewidth=1.1, linestyle="--", label="hard")
    ax_swing.set_xlabel("Mean swing ratio  (error = ±1 SD)")
    ax_swing.set_title("Swing Ratio")
    ax_swing.legend(loc="lower right", fontsize=8)
    ax_swing.set_xlim(0, max(2.5, max(swings) + 0.4))

    # ---- Harmonic complexity bar chart ----
    comp_vals = df["complexity"].fillna(0).tolist()
    comp_colours = [
        _score_colour(v, 0.45, 0.70) if v > 0 else _neutral()
        for v in comp_vals
    ]

    ax_harm.barh(y_pos, comp_vals, color=comp_colours,
                 edgecolor="white", linewidth=0.7)
    ax_harm.set_yticks(y_pos)
    ax_harm.set_yticklabels(labels, fontsize=8)
    ax_harm.invert_yaxis()
    # Reference lines: 0.5 ≈ triad-level, 0.65 ≈ extended jazz voicings
    ax_harm.axvline(0.50, color="#CC3333", linewidth=1.1, linestyle="--", label="≈ triads")
    ax_harm.axvline(0.62, color="#E07B00", linewidth=1.1, linestyle="--", label="≈ 7th chords")
    ax_harm.axvline(0.70, color="#227722", linewidth=1.1, linestyle="--", label="≈ extensions")
    ax_harm.set_xlabel("Harmonic complexity  (chroma entropy, normalised)")
    ax_harm.set_title("Harmonic Complexity")
    ax_harm.legend(loc="lower right", fontsize=8)
    ax_harm.set_xlim(0, 1.0)

    # ---- Save ----
    os.makedirs(figures_dir, exist_ok=True)
    out_path = os.path.join(figures_dir, "results_dashboard.png")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(pieces_dir: str, figures_dir: str, swing_csv: str) -> pd.DataFrame:
    """
    1. Load existing swing results (if available).
    2. Run chroma-based harmonic analysis on every audio file.
    3. Merge the data.
    4. Build and save the dashboard.
    5. Return the merged DataFrame.
    """
    pieces_path = Path(pieces_dir)
    audio_files = sorted([
        p for p in pieces_path.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ])

    if not audio_files:
        print(f"No audio files found in {pieces_dir}")
        sys.exit(1)

    # Load swing results if they exist
    swing_df = pd.DataFrame()
    if os.path.exists(swing_csv):
        swing_df = pd.read_csv(swing_csv)
        # piece_id in swing_results is the stem (e.g. "Rail Yard Bop")
        swing_df = swing_df.rename(columns={"piece_id": "stem"})

    # Run harmonic analysis
    print(f"Running chroma-based harmonic analysis on {len(audio_files)} files...\n")
    harm_rows = []
    for path in audio_files:
        print(f"  {path.name}")
        try:
            h = analyze_harmony_audio(str(path))
            harm_rows.append({"stem": path.stem, **h})
        except Exception as exc:
            print(f"    ERROR: {exc}")
            harm_rows.append({"stem": path.stem, "error": str(exc)})

    harm_df = pd.DataFrame(harm_rows)

    # Merge swing + harmony on stem
    if not swing_df.empty:
        merged = harm_df.merge(swing_df, on="stem", how="left")
    else:
        merged = harm_df

    # Human-readable label for display (use stem as fallback)
    merged["label"] = merged["stem"]

    print()
    print("Results:")
    print(merged[["label", "key", "jazz_sim", "complexity", "change_rate",
                  "mean_ratio"]].to_string(index=False))

    # Build dashboard
    out_path = build_dashboard(merged, figures_dir)
    print(f"\nDashboard saved to: {out_path}")

    return merged


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harmonic analysis + visual dashboard for the AI jazz evaluation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pieces",  default="../pieces",
                        help="Audio files directory (default: ../pieces)")
    parser.add_argument("--figures", default="../figures",
                        help="Output directory for figures (default: ../figures)")
    parser.add_argument("--swing-csv", default="../results/swing_results.csv",
                        help="Existing swing_results.csv to merge in")
    parser.add_argument("--output", default=None, metavar="CSV",
                        help="Optional: save merged DataFrame to this CSV")

    args = parser.parse_args()

    df = run(args.pieces, args.figures, args.swing_csv)

    if args.output:
        df.drop(columns=["pc_dist"], errors="ignore").to_csv(args.output, index=False)
        print(f"Merged results saved to {args.output}")


if __name__ == "__main__":
    main()
