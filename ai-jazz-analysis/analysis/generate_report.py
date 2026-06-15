"""
generate_report.py  —  Single-piece analysis report generator.

Generates a Markdown report for ONE piece at a time, combining:
  - Swing ratio analysis (from results/swing_results.csv)
  - Chord vocabulary and ii-V-I data (from results/notes/{piece}_chords.csv)
  - Chroma-based key and harmonic complexity (recomputed from audio, ~2s)
  - Rubric scores (from results/scores.csv, if rated)
  - AI-written musical summary (Claude API — requires ANTHROPIC_API_KEY)

Output: reports/{piece_stem}_report.md

USAGE
-----
    python generate_report.py --piece "Blue Note Bounce"
    python generate_report.py --piece "Corner Pocket Riff" --no-ai
    python generate_report.py          # lists available pieces and exits

API KEY
-------
Set OPENAI_API_KEY as an environment variable, or pass --api-key.
If the key is absent the AI summary section is skipped and clearly marked.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

# ---------------------------------------------------------------------------
# Key detection  (same as results_dashboard.py / generate_report.py v1)
# ---------------------------------------------------------------------------

KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                     2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                     2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTE_NAMES_KK = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

JAZZ_PC = np.array([0.112,0.062,0.095,0.058,0.089,0.079,
                    0.064,0.098,0.057,0.085,0.060,0.041])
JAZZ_PC /= JAZZ_PC.sum()
POP_PC  = np.array([0.148,0.030,0.108,0.028,0.124,0.096,
                    0.032,0.142,0.027,0.106,0.029,0.130])
POP_PC  /= POP_PC.sum()

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".ogg", ".m4a"}


def _cosine(a, b):
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / d) if d > 0 else 0.0


def detect_key_from_audio(audio_path: str) -> dict:
    """Return key, mode, jazz_sim, pop_sim, complexity from audio chroma."""
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=36)
    mean_chroma = chroma.mean(axis=1)
    pc_dist = mean_chroma / (mean_chroma.sum() + 1e-8)

    best_r, best_key, best_mode = -np.inf, "C", "major"
    for i in range(12):
        r, _ = pearsonr(mean_chroma, np.roll(KK_MAJOR, i))
        if r > best_r:
            best_r, best_key, best_mode = r, NOTE_NAMES_KK[i], "major"
        r, _ = pearsonr(mean_chroma, np.roll(KK_MINOR, i))
        if r > best_r:
            best_r, best_key, best_mode = r, NOTE_NAMES_KK[i], "minor"

    chroma_norm = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-8)
    entropy = -np.sum(chroma_norm * np.log2(np.clip(chroma_norm, 1e-8, 1)), axis=0)
    complexity = float(entropy.mean()) / np.log2(12)

    return {
        "key":        f"{best_key} {best_mode}",
        "jazz_sim":   _cosine(pc_dist, JAZZ_PC),
        "pop_sim":    _cosine(pc_dist, POP_PC),
        "complexity": complexity,
    }


# ---------------------------------------------------------------------------
# Chord CSV helpers
# ---------------------------------------------------------------------------

JAZZ_QUALITIES = {"dom7", "maj7", "min7", "hdim7", "dim7"}

QUALITY_DISPLAY = {
    "maj":   "major triad",    "min":   "minor triad",
    "dom7":  "dominant 7th",   "maj7":  "major 7th",
    "min7":  "minor 7th",      "hdim7": "half-diminished (m7b5)",
    "dim7":  "diminished 7th", "N":     "uncertain",
}


def _root_pc(label: str) -> int:
    for root, pc in zip(
        ["Db","Eb","Gb","Ab","Bb","C#","D#","F#","G#","A#","B","C","D","E","F","G","A"],
        [1,   3,   6,   8,   10,  1,   3,   6,   8,   10,  11, 0,  2,  4,  5,  7,  9],
    ):
        if label.startswith(root):
            return pc
    return 0


def load_chord_data(chord_csv: str) -> dict:
    df = pd.read_csv(chord_csv)
    df = df[df["chord"] != "N"]
    if df.empty:
        return {"jazz_ratio": 0, "ii_V_I_count": 0, "top_chords": [],
                "quality_dist": {}, "total_segments": 0, "n_unique": 0,
                "quality_for": {}}

    total = len(df)
    jazz_ratio = df["quality"].isin(JAZZ_QUALITIES).sum() / total

    quality_dist = (
        df["quality"].value_counts(normalize=True)
        .mul(100).round(1).to_dict()
    )
    top_chords = df["chord"].value_counts().head(10).items()
    top_chords = [(ch, int(ct)) for ch, ct in top_chords]

    # ii-V-I count
    chords, qualities = df["chord"].tolist(), df["quality"].tolist()
    ii_v_i = 0
    for i in range(len(chords) - 2):
        qa, qb, qc = qualities[i], qualities[i+1], qualities[i+2]
        if qa not in ("min7","hdim7") or qb != "dom7" or qc not in ("maj","maj7"):
            continue
        ra, rb, rc = _root_pc(chords[i]), _root_pc(chords[i+1]), _root_pc(chords[i+2])
        if (rb - ra) % 12 == 5 and (rc - rb) % 12 == 5:
            ii_v_i += 1

    quality_for = (
        df.groupby("chord")["quality"]
        .agg(lambda x: x.mode().iloc[0] if len(x) else "")
        .to_dict()
    )

    return {
        "jazz_ratio":     float(jazz_ratio),
        "ii_V_I_count":   ii_v_i,
        "top_chords":     top_chords,
        "quality_dist":   quality_dist,
        "total_segments": total,
        "n_unique":       df["chord"].nunique(),
        "quality_for":    quality_for,
    }


# ---------------------------------------------------------------------------
# Swing helpers
# ---------------------------------------------------------------------------

def swing_label(r: float) -> str:
    if r < 1.10: return "essentially straight — no swing feel"
    if r < 1.30: return "weak / light swing"
    if r < 1.55: return "medium swing"
    if r < 1.85: return "strong swing"
    return "hard swing / triplet feel"


# ---------------------------------------------------------------------------
# AI summary via Claude API
# ---------------------------------------------------------------------------

def build_ai_prompt(p: dict) -> str:
    """
    Construct the prompt sent to Claude for the musical summary.
    Includes all quantitative data so Claude can reason from numbers to music.
    """
    top_chords_str = ", ".join(
        f"{ch} ({ct} beats)" for ch, ct in (p.get("top_chords") or [])[:6]
    )
    quality_str = "  ".join(
        f"{QUALITY_DISPLAY.get(q, q)}: {pct:.0f}%"
        for q, pct in sorted(
            (p.get("quality_dist") or {}).items(), key=lambda x: -x[1]
        )[:5]
    )

    return f"""You are a jazz musician and music analyst evaluating an AI-generated jazz piece. \
Write a concise musical assessment (3 paragraphs, ~200 words total) based on the quantitative \
data below. Use specific jazz terminology. Be honest about weaknesses — this is research, \
not marketing copy.

PIECE: {p['name']}

RHYTHMIC DATA
  Detected tempo: {p.get('tempo', '?'):.0f} BPM
  Mean swing ratio: {p.get('swing_ratio', 0):.3f}  (1.0 = straight, 1.5 = medium swing, 2.0 = hard/triplet swing)
  Swing std deviation: {p.get('swing_std', 0):.3f}  (higher = more expressive variation)
  Interpretation: {swing_label(p.get('swing_ratio', 1.0))}

HARMONIC DATA
  Detected key: {p.get('key', 'unknown')}
  Jazz complexity: {p.get('jazz_ratio', 0):.0%}  (proportion of beats with 7th-or-richer chords)
  ii-V-I progressions detected: {p.get('ii_v_i', 0)}
  Top chords: {top_chords_str or 'none detected'}
  Quality breakdown: {quality_str or 'unavailable'}
  Jazz pitch-class similarity: {p.get('jazz_sim', 0):.3f}  (1.0 = perfect match to jazz corpus)
  Harmonic complexity (chroma entropy): {p.get('complexity', 0):.3f}  (normalised 0–1)

RUBRIC SCORES (if rated — 1–5 per axis, 30 total)
  {_rubric_summary(p)}

Structure your response as three paragraphs:
  1. Rhythmic character — what the swing ratio says about this piece's feel and whether it genuinely swings
  2. Harmonic sophistication — what the chord vocabulary and progression data say about jazz literacy
  3. Overall verdict — what style of jazz this most resembles, and one specific strength and one specific weakness"""


def _rubric_summary(p: dict) -> str:
    sc = p.get("scores")
    if not sc:
        return "Not yet rated."
    axes = [
        ("harmonic_authenticity", "Harmonic authenticity"),
        ("swing_feel",            "Swing feel"),
        ("improv_coherence",      "Improvisational coherence"),
        ("idiomatic_vocabulary",  "Idiomatic vocabulary"),
        ("ensemble_interaction",  "Ensemble interaction"),
        ("formal_structure",      "Formal structure"),
    ]
    lines = []
    for col, label in axes:
        val = sc.get(col, "—")
        lines.append(f"{label}: {val}/5")
    lines.append(f"Total: {sc.get('total_score', '—')}/30")
    return "  ".join(lines)


def generate_ai_summary(p: dict, api_key: str | None) -> str:
    """
    Call OpenAI to write a musical assessment. Returns the text, or a
    placeholder message if the API key is missing or the call fails.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return (
            "*AI summary not generated — set the `OPENAI_API_KEY` environment variable "
            "or pass `--api-key` to enable this section.*"
        )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=600,
            messages=[{"role": "user", "content": build_ai_prompt(p)}],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"*AI summary failed: {exc}*"


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def _img(alt: str, abs_path: str, report_dir: Path) -> str:
    if Path(abs_path).exists():
        return f"![{alt}]({os.path.relpath(abs_path, report_dir)})"
    return f"*({alt} — figure not found)*"


def _table(headers: list, rows: list) -> str:
    def r(cells): return "| " + " | ".join(str(c) for c in cells) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    return "\n".join([r(headers), sep] + [r(row) for row in rows])


RUBRIC_AXES = [
    ("harmonic_authenticity", "Harmonic Authenticity"),
    ("swing_feel",            "Swing Feel"),
    ("improv_coherence",      "Improvisational Coherence"),
    ("idiomatic_vocabulary",  "Idiomatic Vocabulary"),
    ("ensemble_interaction",  "Ensemble Interaction"),
    ("formal_structure",      "Formal Structure"),
]


# ---------------------------------------------------------------------------
# Piece data loader
# ---------------------------------------------------------------------------

def load_piece_data(
    stem: str,
    audio_path: str,
    results_p: Path,
    figures_p: Path,
) -> dict:
    p: dict = {"name": stem, "stem": stem}

    # Swing
    swing_csv = results_p / "swing_results.csv"
    if swing_csv.exists():
        df = pd.read_csv(swing_csv)
        row = df[df["piece_id"] == stem]
        if not row.empty:
            p["tempo"]       = float(row["tempo_bpm"].iloc[0])
            p["swing_ratio"] = float(row["mean_ratio"].iloc[0])
            p["swing_std"]   = float(row["std_ratio"].iloc[0])
            p["n_pairs"]     = int(row["n_pairs"].iloc[0])

    # Chords
    chord_csv = results_p / "notes" / f"{stem}_chords.csv"
    if chord_csv.exists():
        stats = load_chord_data(str(chord_csv))
        p.update(stats)
    else:
        p["chord_csv_missing"] = True

    # Key + harmony (fast chroma re-computation)
    print(f"  Computing chroma analysis...")
    try:
        h = detect_key_from_audio(audio_path)
        p.update(h)
    except Exception as e:
        print(f"  Key detection failed: {e}")

    # Rubric scores
    scores_csv = results_p / "scores.csv"
    if scores_csv.exists():
        df = pd.read_csv(scores_csv)
        df = df.dropna(subset=[k for k, _ in RUBRIC_AXES], how="all")
        row = df[df["piece_id"] == stem]
        if not row.empty:
            p["scores"] = row.iloc[0].to_dict()
            p["total_score"] = p["scores"].get("total_score")

    return p


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(p: dict, figures_p: Path, report_path: Path, api_key: str | None) -> str:
    stem       = p["stem"]
    now        = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_dir = report_path.parent
    lines      = []

    # ---- Header ----
    lines += [
        f"# Piece Report: {stem}",
        f"",
        f"*Generated: {now}*",
        f"",
        "---",
        "",
    ]

    # ---- Quick stats block ----
    tempo  = p.get("tempo")
    swing  = p.get("swing_ratio")
    key    = p.get("key", "—")
    jr     = p.get("jazz_ratio")
    ii_v_i = p.get("ii_V_I_count", p.get("ii_v_i", "—"))
    score  = p.get("total_score")

    stat_rows = [
        ["Tempo",              f"{tempo:.0f} BPM" if tempo else "—"],
        ["Detected key",       key],
        ["Swing ratio",        f"{swing:.3f}  *({swing_label(swing)})*" if swing else "—"],
        ["Swing std dev",      f"{p['swing_std']:.3f}" if p.get("swing_std") else "—"],
        ["Jazz complexity",    f"{jr:.0%}" if jr is not None else "—"],
        ["ii-V-I progressions",str(ii_v_i)],
        ["Unique chords",      str(p.get("n_unique", "—"))],
        ["Jazz PC similarity", f"{p['jazz_sim']:.3f}" if p.get("jazz_sim") else "—"],
        ["Harmonic complexity",f"{p['complexity']:.3f}" if p.get("complexity") else "—"],
        ["Rubric total",       f"{score}/30" if score is not None else "*(not rated)*"],
    ]
    lines += ["## Quick Stats", ""]
    lines += [_table(["Metric", "Value"], stat_rows), "", "---", ""]

    # ---- AI summary ----
    lines += ["## AI Musical Assessment", ""]
    print("  Requesting AI summary from Claude...")
    ai_text = generate_ai_summary(p, api_key)
    lines += [ai_text, "", "---", ""]

    # ---- Rhythmic analysis ----
    lines += ["## Rhythmic Analysis", ""]
    if swing is not None:
        lines += [
            f"Mean swing ratio: **{swing:.3f}** ± {p.get('swing_std', 0):.3f}  ",
            f"Valid eighth-note pairs analysed: **{p.get('n_pairs', '—')}**  ",
            f"",
            f"> Reference: 1.0 = straight · 1.5 = medium swing · 2.0 = hard swing / triplet feel",
            "",
        ]
    fig_swing = str(figures_p / f"{stem}_swing_ratio.png")
    lines += [_img("Swing ratio over time", fig_swing, report_dir), "", "---", ""]

    # ---- Harmonic analysis ----
    lines += ["## Harmonic Analysis", ""]
    if p.get("jazz_sim"):
        lines += [
            f"**Jazz pitch-class similarity:** {p['jazz_sim']:.3f}  ",
            f"**Harmonic complexity (chroma entropy):** {p['complexity']:.3f}  ",
            f"*(0 = single pitch class dominant; 1 = all 12 equally active)*",
            "",
        ]
    fig_chord = str(figures_p / f"{stem}_chord_timeline.png")
    lines += [_img("Chord timeline", fig_chord, report_dir), "", "---", ""]

    # ---- Chord vocabulary ----
    lines += ["## Chord Vocabulary", ""]
    top = p.get("top_chords", [])
    if top:
        total_s = p.get("total_segments", 1) or 1
        qf = p.get("quality_for", {})
        chord_rows = [
            [ch, QUALITY_DISPLAY.get(qf.get(ch, ""), "—"), ct, f"{100*ct/total_s:.1f}%"]
            for ch, ct in top
        ]
        lines += [_table(["Chord", "Quality", "Beats", "% of total"], chord_rows), ""]

        qd = p.get("quality_dist", {})
        if qd:
            lines += ["**Quality distribution:**", ""]
            for q, pct in sorted(qd.items(), key=lambda x: -x[1]):
                bar = "█" * max(1, int(pct / 5)) if pct >= 2 else ""
                lines += [f"- {QUALITY_DISPLAY.get(q, q):28s} {bar} {pct:.1f}%"]
    else:
        lines += ["*No chord data available — run `chord_detection.py` first.*"]
    lines += ["", "---", ""]

    # ---- Rubric scores ----
    lines += ["## Rubric Scores", ""]
    sc = p.get("scores")
    if sc:
        score_rows = []
        for col, label in RUBRIC_AXES:
            val = sc.get(col, "—")
            if isinstance(val, (int, float)):
                bar = "■" * int(val) + "□" * (5 - int(val))
            else:
                bar = "—"
            score_rows.append([label, str(val), bar])
        score_rows.append(["**Total**", f"**{sc.get('total_score','—')}/30**", ""])
        lines += [_table(["Axis", "Score (1–5)", "Visual"], score_rows), ""]
        if sc.get("timestamp_notes"):
            lines += [f"> {sc['timestamp_notes']}", ""]
    else:
        lines += ["*Not yet rated. Run `rating_helper.py` to score this piece.*", ""]

    lines += ["---", ""]

    # ---- Human analysis ----
    lines += [
        "## Human Analysis",
        "",
        "*Add your own observations here after listening to the piece.*",
        "",
        "**First impression:**",
        "",
        "<!-- What stands out immediately on first listen? -->",
        "",
        "**Rhythmic feel:**",
        "",
        "<!-- Does it swing? Where does it feel natural or mechanical? -->",
        "",
        "**Harmonic observations:**",
        "",
        "<!-- Any unexpected chord choices, voice leading moments, or tonal ambiguity? -->",
        "",
        "**Stylistic resemblance:**",
        "",
        "<!-- What era or substyle of jazz does this most evoke? -->",
        "",
        "**Discrepancies from AI assessment:**",
        "",
        "<!-- Where does the AI analysis miss something you hear clearly? -->",
        "",
        "---",
        "",
    ]

    # ---- Footer ----
    lines += [
        "## References",
        "",
        "- Rubric and methodology: [methodology.md](../methodology.md)",
        "- Original prompts: [PROMPTS.md](../PROMPTS.md)",
        f"- Re-generate this report: `python analysis/generate_report.py --piece \"{stem}\"`",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Piece selection
# ---------------------------------------------------------------------------

def find_piece(query: str, pieces_dir: Path) -> Path | None:
    """Find an audio file whose stem matches query (case-insensitive, partial ok)."""
    audio_files = [
        p for p in pieces_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]
    q = query.lower()
    # Exact stem match first
    for f in audio_files:
        if f.stem.lower() == q:
            return f
    # Partial match
    matches = [f for f in audio_files if q in f.stem.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"Ambiguous match for '{query}':")
        for m in matches:
            print(f"  {m.stem}")
        print("Please be more specific.")
    return None


def list_pieces(pieces_dir: Path) -> None:
    audio_files = sorted(
        p for p in pieces_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )
    if not audio_files:
        print(f"No audio files found in {pieces_dir}")
        return
    print(f"\nAvailable pieces in {pieces_dir}:\n")
    for i, f in enumerate(audio_files, 1):
        print(f"  {i:2d}.  {f.stem}")
    print(f"\nUsage:  python generate_report.py --piece \"<name>\"")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a single-piece analysis report with AI summary.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_report.py --piece "Blue Note Bounce"
  python generate_report.py --piece "Corner"          # partial match
  python generate_report.py --piece "Rail Yard Bop" --no-ai
  python generate_report.py                           # list available pieces
        """,
    )
    parser.add_argument("--piece",   default=None,
                        help="Piece name (or partial match) to generate the report for")
    parser.add_argument("--pieces",  default="../pieces",
                        help="Audio files directory (default: ../pieces)")
    parser.add_argument("--results", default="../results",
                        help="Results directory (default: ../results)")
    parser.add_argument("--figures", default="../figures",
                        help="Figures directory (default: ../figures)")
    parser.add_argument("--out-dir", default="../reports",
                        help="Output directory for the report (default: ../reports)")
    parser.add_argument("--no-ai",   action="store_true",
                        help="Skip the Claude AI summary (faster, no API key needed)")
    parser.add_argument("--api-key", default=None,
                        help="Anthropic API key (overrides ANTHROPIC_API_KEY env var)")

    args = parser.parse_args()

    pieces_p  = Path(args.pieces).resolve()
    results_p = Path(args.results).resolve()
    figures_p = Path(args.figures).resolve()
    out_dir   = Path(args.out_dir).resolve()

    if not args.piece:
        list_pieces(pieces_p)
        sys.exit(0)

    audio_file = find_piece(args.piece, pieces_p)
    if not audio_file:
        print(f"No match for '{args.piece}'.")
        list_pieces(pieces_p)
        sys.exit(1)

    print(f"\nGenerating report for: {audio_file.stem}")

    p = load_piece_data(
        stem=audio_file.stem,
        audio_path=str(audio_file),
        results_p=results_p,
        figures_p=figures_p,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{audio_file.stem}_report.md"

    api_key = None if args.no_ai else args.api_key
    report_text = build_report(p, figures_p, report_path, api_key)

    report_path.write_text(report_text, encoding="utf-8")
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
