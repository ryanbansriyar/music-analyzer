"""
rating_helper.py  —  Interactive CLI for the blind rating pass.

WHY THIS EXISTS
---------------
Editing a CSV by hand while listening is error-prone (wrong row, wrong column,
fat-finger scores). This script loops through piece_01..piece_NN in order,
prints the rubric anchors as a reminder for each axis, prompts for a 1-5 score,
computes the total, and appends the row to results/scores.csv automatically.

RESUMING A SESSION
------------------
If you quit partway through (Ctrl+C or type 'q' at any prompt), pieces you
already scored are preserved. Next time you run the script it reads scores.csv,
finds the highest piece_id already present, and resumes from the next one.

USAGE
-----
    python rating_helper.py
    python rating_helper.py --scores ../results/scores.csv --pieces ../pieces/
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Rubric — copied from methodology.md so it's available without opening a doc
# ---------------------------------------------------------------------------

# Each axis is a dict with:
#   name        : display name
#   csv_key     : column name in scores.csv
#   question    : the diagnostic question the rater is answering
#   anchors     : {score: one-line descriptor} for scores 1–5
RUBRIC = [
    {
        "name": "Harmonic Authenticity",
        "csv_key": "harmonic_authenticity",
        "question": "Does the piece use jazz harmony convincingly?",
        "anchors": {
            1: "No jazz harmony — triads or power chords, pop/folk feel",
            2: "Superficial jazz markers — 7ths present but don't function",
            3: "Surface-plausible but flawed — ii-V-I exists, voice leading clunky",
            4: "Convincing with minor lapses — extensions mostly idiomatic",
            5: "Idiomatic and inventive — tritone subs, altered dominants, smooth voice leading",
        },
    },
    {
        "name": "Swing Feel and Microtiming",
        "csv_key": "swing_feel",
        "question": "Does the piece actually swing?",
        "anchors": {
            1: "Completely straight — all eighths equal, mechanical",
            2: "Attempted swing, fails — uneven but not groove",
            3: "Weak/inconsistent swing — present in parts, not convincing",
            4: "Clear swing feel with minor inconsistencies — you'd tap your foot",
            5: "Natural, idiomatic swing — organic long/short ratio, backbeat accents, lays back",
        },
    },
    {
        "name": "Improvisational Coherence",
        "csv_key": "improv_coherence",
        "question": "Does the improvised content have musical logic?",
        "anchors": {
            1: "Incoherent — random notes within a scale, no phrases",
            2: "Phrases exist but don't connect — random licks stitched together",
            3: "Surface coherence, no depth — phrases clean but no motivic development",
            4: "Clear motivic logic — motif recurs/develops, tension builds",
            5: "Excellent narrative — exposition, development, climax, resolution",
        },
    },
    {
        "name": "Idiomatic Jazz Vocabulary",
        "csv_key": "idiomatic_vocabulary",
        "question": "Are the sounds and gestures recognisably jazz?",
        "anchors": {
            1: "No jazz vocabulary — generic instrumentation, rock beat, no articulation",
            2: "Jazz instruments, wrong roles — no walking bass, piano chorded badly",
            3: "Mostly correct roles, vocabulary thin — correct but sterile",
            4: "Strong vocabulary with occasional lapses — ghost notes, fall-offs, ride pattern present",
            5: "Fully idiomatic — every instrument sounds like a jazz musician",
        },
    },
    {
        "name": "Ensemble Interaction",
        "csv_key": "ensemble_interaction",
        "question": "Do the instruments respond to each other?",
        "anchors": {
            1: "No interaction — parts are independent, no listening",
            2: "Minimal awareness — compatible but independent",
            3: "Functional ensemble — fits together, no real conversation",
            4: "Reactive playing evident — comping changes density, drums set up arrivals",
            5: "Genuine conversation — call-and-response, piano lays out, drummer drops bombs",
        },
    },
    {
        "name": "Formal Structure",
        "csv_key": "formal_structure",
        "question": "Does the piece have a recognisable jazz form?",
        "anchors": {
            1: "No discernible form — formless texture",
            2: "Some section contrast, no jazz form — doesn't cycle",
            3: "Approximate jazz form — AABA or blues audible but doesn't execute cleanly",
            4: "Correct form with minor inconsistencies — head, solos, out-head mostly works",
            5: "Idiomatic form executed cleanly — any jazz musician could sit in",
        },
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCORES_HEADER = [
    "piece_id",
    "harmonic_authenticity",
    "swing_feel",
    "improv_coherence",
    "idiomatic_vocabulary",
    "ensemble_interaction",
    "formal_structure",
    "total_score",
    "timestamp_notes",
]


def load_scored_pieces(scores_path: Path) -> set[str]:
    """Return the set of piece_ids already present in scores.csv."""
    if not scores_path.exists():
        return set()
    with open(scores_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["piece_id"] for row in reader if row.get("piece_id")}


def find_pieces(pieces_dir: Path) -> list[str]:
    """
    Return sorted piece IDs (e.g. 'piece_01') for all audio files in pieces_dir
    whose names follow the piece_NN pattern.
    """
    audio_exts = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".ogg", ".m4a"}
    ids = []
    for p in sorted(pieces_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in audio_exts:
            if p.stem.startswith("piece_"):
                ids.append(p.stem)
    return ids


def append_score(scores_path: Path, row: dict) -> None:
    """Append one scored row to scores.csv. Creates the file with header if needed."""
    file_exists = scores_path.exists() and scores_path.stat().st_size > 1
    with open(scores_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCORES_HEADER)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def prompt_score(axis: dict) -> int:
    """
    Print the rubric for one axis and prompt for an integer 1–5.
    Returns the integer, or raises SystemExit on 'q'.
    """
    print()
    print(f"  ── {axis['name'].upper()} ──")
    print(f"  {axis['question']}")
    print()
    for score, desc in axis["anchors"].items():
        print(f"    {score}  {desc}")
    print()

    while True:
        raw = input("  Score [1-5], or 'q' to quit and save progress: ").strip().lower()
        if raw == "q":
            print("\n  Progress saved. Re-run rating_helper.py to continue.\n")
            sys.exit(0)
        if raw in {"1", "2", "3", "4", "5"}:
            return int(raw)
        print("  Please enter a number 1–5, or 'q' to quit.")


def prompt_notes(piece_id: str) -> str:
    """Prompt for optional free-text notes. Empty is fine."""
    print()
    raw = input("  Notes (optional — timestamps, standout moments, anything odd): ").strip()
    return raw


def divider(char: str = "─", width: int = 68) -> str:
    return "  " + char * width


# ---------------------------------------------------------------------------
# Main rating loop
# ---------------------------------------------------------------------------

def run_rating(pieces_dir: Path, scores_path: Path) -> None:
    already_scored = load_scored_pieces(scores_path)
    all_pieces = find_pieces(pieces_dir)

    if not all_pieces:
        print(f"\n  No blinded files (piece_NN.*) found in {pieces_dir}")
        print("  Run blind_rename.py first to blind the pieces/ folder.\n")
        sys.exit(1)

    remaining = [p for p in all_pieces if p not in already_scored]

    print()
    print(divider("═"))
    print()
    print("  JAZZ EVALUATION — RATING SESSION")
    print()
    print(f"  Pieces in pieces/: {len(all_pieces)}")
    print(f"  Already scored:    {len(already_scored)}")
    print(f"  Remaining:         {len(remaining)}")
    print()
    print("  Each piece: 6 axes, scores 1–5. Total = sum of axes (max 30).")
    print("  Type 'q' at any score prompt to quit and save your progress.")
    print()
    print(divider("═"))

    if not remaining:
        print()
        print("  All pieces already scored. Nothing to do.")
        print(f"  Results are in {scores_path}")
        print()
        return

    for piece_id in remaining:
        print()
        print(divider("═"))
        print()
        print(f"  PIECE: {piece_id}   ({remaining.index(piece_id) + 1} of {len(remaining)} remaining)")
        print()
        print("  Listen to the file now, then score each axis.")
        print()

        scores = {}
        for axis in RUBRIC:
            scores[axis["csv_key"]] = prompt_score(axis)

        total = sum(scores.values())
        notes = prompt_notes(piece_id)

        row = {
            "piece_id": piece_id,
            **scores,
            "total_score": total,
            "timestamp_notes": notes,
        }

        append_score(scores_path, row)

        print()
        print(divider())
        print(f"  Saved:  {piece_id}  →  total {total}/30")
        score_line = "  " + "  ".join(
            f"{axis['csv_key'].split('_')[0][:4]}={scores[axis['csv_key']]}"
            for axis in RUBRIC
        )
        print(score_line)
        print(divider())

    print()
    print(divider("═"))
    print()
    print(f"  Session complete! All {len(all_pieces)} pieces scored.")
    print(f"  Results saved to {scores_path}")
    print()
    print("  Next steps:")
    print("    • Share the blinded files with your second rater")
    print("    • Once both raters are done, open results/key.csv to decode")
    print("    • Run swing_ratio.py --batch ../pieces/ for quantitative analysis")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive rating tool for the blind jazz evaluation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rating_helper.py
  python rating_helper.py --scores ../results/scores.csv --pieces ../pieces/
        """,
    )
    parser.add_argument(
        "--scores",
        default="../results/scores.csv",
        metavar="CSV",
        help="Path to scores.csv (default: ../results/scores.csv)",
    )
    parser.add_argument(
        "--pieces",
        default="../pieces",
        metavar="DIR",
        help="Directory of blinded audio files (default: ../pieces)",
    )

    args = parser.parse_args()

    scores_path = Path(args.scores).resolve()
    pieces_dir = Path(args.pieces).resolve()

    if not pieces_dir.exists():
        print(f"\n  ERROR: pieces directory not found: {pieces_dir}\n")
        sys.exit(1)

    scores_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        run_rating(pieces_dir, scores_path)
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Progress saved. Re-run to continue.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
