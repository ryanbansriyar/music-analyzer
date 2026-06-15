"""
swing_ratio.py  —  Quantitative swing analysis for the AI jazz evaluation.

WHAT IS SWING RATIO?
--------------------
In straight music (classical, pop), consecutive eighth notes are equal in
duration — ratio 1.0. In jazz, the first eighth note is held longer and the
second is shorter, creating the "lilt" that defines swing. The ratio of
long to short is called the swing ratio:

    1.0  =  straight (no swing)
   ~1.5  =  medium swing (the most common jazz feel)
   ~2.0  =  hard swing / triplet feel (like bebop at high tempos)
    2.0+ =  very heavy swing, heard in early New Orleans and some blues

Real players don't hold the ratio constant — they vary it expressively,
laying back on slow ballads and pushing harder on up-tempo bebop. That
variation is *itself* musical information. This script captures both the
mean ratio and its change over time.

HOW WE MEASURE IT
-----------------
Onset detection finds the moment each note begins. We look at three
consecutive onsets (t0, t1, t2). If their combined duration t2-t0 is close
to one quarter note at the detected tempo, we classify t0→t1 as the "long"
eighth and t1→t2 as the "short" eighth, then compute long/short.

LIMITATION
----------
Onset detection is noisy on dense polyphonic audio — it picks up every
piano chord, bass note, and cymbal hit, not just the melody. The result
is a noisy time series, but the mean and rolling trend are still
informative, especially when comparing across models. Treat as indicative,
not definitive.

USAGE
-----
    python swing_ratio.py ../pieces/piece_01.mp3
    python swing_ratio.py --batch ../pieces/
    python swing_ratio.py --batch ../pieces/ --output swing_results.csv
"""

import argparse
import os
import sys
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Consistent publication-ready plot style (applied at module level)
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

# Colour per model — used in the batch summary plot
MODEL_COLOURS = {
    "suno":         "#4878CF",
    "udio":         "#6ACC65",
    "musicgen":     "#D65F5F",
    "stable_audio": "#B47CC7",
    "aiva":         "#C4AD66",
    "unknown":      "#AAAAAA",
}

# Audio extensions recognised as input
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".ogg", ".m4a"}


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_swing(audio_path: str, tolerance: float = 0.3) -> dict:
    """
    Compute the swing ratio for an audio file.

    Loads the audio, estimates tempo, detects onsets, finds consecutive
    eighth-note pairs, and computes long/short ratio for each pair.

    Reference values:
        1.0  =  straight (all eighths equal)
        1.5  =  medium swing (typical jazz comping feel)
        2.0  =  hard swing / triplet feel (bebop, hard bop)

    Args:
        audio_path : path to any librosa-readable audio file
        tolerance  : accept onset pairs whose combined duration is within
                     this fraction (default ±30%) of one quarter note

    Returns dict with:
        mean_ratio   : mean swing ratio across all valid pairs (float or None)
        std_ratio    : standard deviation (float or None)
        n_pairs      : number of valid eighth-note pairs found (int)
        tempo_bpm    : detected tempo in BPM (float)
        time_series  : list of (timestamp_seconds, ratio) tuples — the raw
                       per-pair data for plotting the ratio over time
    """
    # Load audio as mono; keep native sample rate for best onset precision
    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # Tempo estimation: beat_track returns (tempo_array, beat_frames).
    # In librosa >= 0.10, tempo is a 1-element array; np.atleast_1d()[0] works
    # for both 0-d and 1-d returns across versions.
    tempo_arr, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo_arr)[0])

    # Onset detection with backtrack=True snaps each onset back to the
    # nearest energy peak — more accurate start times than frame centres.
    onset_frames = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        units="frames",
        backtrack=True,
        pre_max=3,
        post_max=3,
        pre_avg=5,
        post_avg=5,
        delta=0.07,
        wait=10,   # minimum 10 frames (~23ms at 22kHz) between onsets
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # --- Find eighth-note pairs ---
    # One quarter note at this tempo:
    quarter_dur = 60.0 / tempo

    pairs = []  # list of (timestamp, ratio) tuples

    # Slide a 3-onset window: t0, t1, t2.
    # If (t2 - t0) ≈ one quarter note, then t0→t1 is the long eighth
    # and t1→t2 is the short eighth. Their ratio is the swing ratio.
    for i in range(len(onset_times) - 2):
        t0, t1, t2 = onset_times[i], onset_times[i + 1], onset_times[i + 2]

        long_dur  = t1 - t0   # long (downbeat) eighth
        short_dur = t2 - t1   # short (upbeat) eighth
        total     = t2 - t0   # should be close to one quarter note

        # Skip if this pair doesn't plausibly span one quarter note
        if abs(total - quarter_dur) > tolerance * quarter_dur:
            continue

        # Skip if the short duration is suspiciously small (detection artifact)
        if short_dur < 0.01:
            continue

        ratio = long_dur / short_dur

        # Hard filter: ratios outside [0.5, 4.0] are almost certainly noise
        if 0.5 <= ratio <= 4.0:
            pairs.append((float(t0), float(ratio)))

    # --- Summarise ---
    if pairs:
        ratios = [r for _, r in pairs]
        mean_ratio = float(np.mean(ratios))
        std_ratio  = float(np.std(ratios))
    else:
        mean_ratio = None
        std_ratio  = None

    return {
        "mean_ratio":  mean_ratio,
        "std_ratio":   std_ratio,
        "n_pairs":     len(pairs),
        "tempo_bpm":   tempo,
        "time_series": pairs,   # list of (t, ratio)
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_swing_over_time(audio_path: str, figures_dir: str = "../figures") -> str:
    """
    Generate a swing-ratio-over-time plot for one audio file and save it.

    Calls analyze_swing() internally. Draws:
      • scatter of raw per-pair ratios (light dots)
      • rolling mean trend line (solid)
      • dashed reference lines at 1.0 (straight), 1.5 (medium), 2.0 (hard)

    Args:
        audio_path  : path to the audio file
        figures_dir : directory to save the figure (created if needed)

    Returns:
        Path to the saved figure file.
    """
    print(f"  Analysing: {Path(audio_path).name}")
    result = analyze_swing(audio_path)

    tempo    = result["tempo_bpm"]
    n_pairs  = result["n_pairs"]
    ts       = result["time_series"]

    stem     = Path(audio_path).stem
    title    = (f"Swing Ratio Over Time — {stem}\n"
                f"tempo ≈ {tempo:.0f} BPM  |  {n_pairs} eighth-note pairs")

    times  = np.array([t for t, _ in ts])
    ratios = np.array([r for _, r in ts])

    fig, ax = plt.subplots(figsize=(12, 4.5))

    if len(ratios) > 0:
        # Raw pairs as small semi-transparent dots
        ax.scatter(times, ratios, alpha=0.35, s=14, color="#4878CF",
                   label="Eighth-note pairs", zorder=2)

        # Rolling mean to reveal the trend without the noise
        if len(ratios) >= 10:
            window = max(5, min(20, len(ratios) // 5))
            rolling = pd.Series(ratios).rolling(window, center=True, min_periods=1).mean()
            ax.plot(times, rolling, color="#1A3A6B", linewidth=2.0,
                    label=f"Rolling mean (w = {window})", zorder=3)
    else:
        ax.text(0.5, 0.5, "No valid eighth-note pairs detected",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=12, color="#888888")

    # Reference lines — labelled at the right edge
    xmax = float(times[-1]) if len(times) else 60.0
    for y_val, label, colour in [
        (1.0, "straight",    "#CC3333"),
        (1.5, "medium swing","#E07B00"),
        (2.0, "hard swing",  "#227722"),
    ]:
        ax.axhline(y_val, color=colour, linewidth=1.2, linestyle="--",
                   label=f"{label} ({y_val})", zorder=1)

    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Swing ratio  (long ÷ short)")
    ax.set_title(title)
    ax.set_ylim(0.3, 3.2)
    ax.legend(loc="upper right", ncol=2)

    os.makedirs(figures_dir, exist_ok=True)
    out_path = os.path.join(figures_dir, f"{stem}_swing_ratio.png")
    plt.savefig(out_path)
    plt.close(fig)
    print(f"  Figure saved: {out_path}")
    return out_path


def _plot_batch_summary(df: pd.DataFrame, figures_dir: str) -> str:
    """
    Bar chart: mean swing ratio per piece, error bars = std, coloured by model.

    Joins df with results/key.csv (if it exists) to get model labels.
    If key.csv is missing or hasn't been decoded yet, all bars are grey.

    Returns path to saved figure.
    """
    # Try to load model info from key.csv (one level up from figures_dir)
    key_path = Path(figures_dir).parent / "results" / "key.csv"
    if key_path.exists():
        key_df = pd.read_csv(key_path)
        df = df.merge(key_df[["piece_id", "model"]], on="piece_id", how="left")
        df["model"] = df["model"].fillna("unknown")
    else:
        df = df.copy()
        df["model"] = "unknown"

    df = df.sort_values("piece_id")

    colours = [
        MODEL_COLOURS.get(str(m).lower(), MODEL_COLOURS["unknown"])
        for m in df["model"]
    ]

    fig, ax = plt.subplots(figsize=(max(10, len(df) * 0.55), 5))

    x = range(len(df))
    means = df["mean_ratio"].fillna(0)
    stds  = df["std_ratio"].fillna(0)

    bars = ax.bar(x, means, color=colours, edgecolor="white",
                  linewidth=0.7, zorder=2)
    ax.errorbar(x, means, yerr=stds, fmt="none", color="#333333",
                capsize=3, linewidth=1.0, zorder=3)

    # Reference lines
    for y_val, label, colour in [
        (1.0, "straight",     "#CC3333"),
        (1.5, "medium swing", "#E07B00"),
        (2.0, "hard swing",   "#227722"),
    ]:
        ax.axhline(y_val, color=colour, linewidth=1.0, linestyle="--",
                   label=f"{label} ({y_val})", zorder=1)

    ax.set_xticks(list(x))
    ax.set_xticklabels(df["piece_id"], rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Piece")
    ax.set_ylabel("Mean swing ratio")
    ax.set_title("Mean Swing Ratio per Piece  (error bars = ±1 SD)\n"
                 "Colour = model  |  grey = model not yet decoded from key.csv")
    ax.set_ylim(0, max(3.0, float(means.max()) + 0.5))

    # Build legend for models that actually appear
    seen_models = df["model"].unique()
    legend_patches = [
        plt.Rectangle((0, 0), 1, 1,
                       color=MODEL_COLOURS.get(m, MODEL_COLOURS["unknown"]),
                       label=m)
        for m in sorted(seen_models)
    ]
    ref_handles, ref_labels = ax.get_legend_handles_labels()
    ax.legend(handles=legend_patches + ref_handles,
              labels=[p.get_label() for p in legend_patches] + ref_labels,
              loc="upper right", ncol=2, fontsize=8)

    os.makedirs(figures_dir, exist_ok=True)
    out_path = os.path.join(figures_dir, "batch_swing_summary.png")
    plt.savefig(out_path)
    plt.close(fig)
    print(f"  Summary figure saved: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def batch_analyze(
    directory: str,
    figures_dir: str = "../figures",
) -> pd.DataFrame:
    """
    Run analyze_swing and plot_swing_over_time on every audio file in a directory.

    After processing all files, generates a summary bar chart coloured by model
    (joined from results/key.csv if available).

    Args:
        directory   : folder containing audio files (typically pieces/)
        figures_dir : where to save per-piece and summary figures

    Returns:
        pd.DataFrame with columns:
            piece_id, file, tempo_bpm, mean_ratio, std_ratio, n_pairs
    """
    audio_files = sorted([
        p for p in Path(directory).iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ])

    if not audio_files:
        print(f"No audio files found in {directory}")
        return pd.DataFrame()

    print(f"Found {len(audio_files)} audio files in {directory}")
    rows = []

    for path in audio_files:
        try:
            result = analyze_swing(str(path))
            plot_swing_over_time(str(path), figures_dir=figures_dir)
            rows.append({
                "piece_id":   path.stem,
                "file":       str(path),
                "tempo_bpm":  result["tempo_bpm"],
                "mean_ratio": result["mean_ratio"],
                "std_ratio":  result["std_ratio"],
                "n_pairs":    result["n_pairs"],
            })
        except Exception as exc:
            print(f"  ERROR on {path.name}: {exc}")
            rows.append({"piece_id": path.stem, "file": str(path), "error": str(exc)})

    df = pd.DataFrame(rows)
    print(f"\nProcessed {len(df)} files.")

    # Summary plot (skips files with errors)
    valid = df[df.get("mean_ratio", pd.Series(dtype=float)).notna()] if "mean_ratio" in df else df
    if not valid.empty:
        _plot_batch_summary(valid, figures_dir)

    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute swing ratio from jazz audio files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python swing_ratio.py ../pieces/piece_01.mp3
  python swing_ratio.py ../pieces/piece_01.mp3 --figures ../figures
  python swing_ratio.py --batch ../pieces/
  python swing_ratio.py --batch ../pieces/ --output swing_results.csv
        """,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a single audio file",
    )
    parser.add_argument(
        "--batch",
        metavar="DIR",
        help="Process all audio files in this directory",
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
        result = analyze_swing(args.input)
        plot_swing_over_time(args.input, figures_dir=args.figures)
        print()
        print("Results:")
        print(f"  Tempo:            {result['tempo_bpm']:.1f} BPM")
        print(f"  Valid pairs:      {result['n_pairs']}")
        if result["mean_ratio"] is not None:
            print(f"  Mean swing ratio: {result['mean_ratio']:.3f}")
            print(f"  Std deviation:    {result['std_ratio']:.3f}")
        else:
            print("  Mean swing ratio: (no valid pairs found)")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
