"""
blind_rename.py  —  Step 1 of the rating protocol.

WHAT THIS DOES
--------------
Scans pieces/ for audio files, randomly assigns each one a neutral ID
(piece_01, piece_02, ...) preserving the original extension, writes the
decode key to results/key.csv, and renames the files.

WHY BLINDING MATTERS
--------------------
If you know you're listening to Suno before you press play, your ear is
already primed. Even a jazz musician with 10 years training has unconscious
priors about which models "should" sound better. Blinding makes the scores
defensible and publishable.

NAMING CONVENTION (from methodology.md section 2)
--------------------------------------------------
Save files to pieces/ as:   {model}_{prompt_id}_raw.{ext}
Examples:                   suno_p1_raw.mp3
                            udio_p3_raw.wav
                            aiva_p5_raw.mid

If your filenames don't match this pattern (e.g. you saved them with the
original title from the generator), the model and prompt_id columns in
key.csv will be left blank. A clear WARNING is printed. You must fill in
key.csv manually before batch_analyze in swing_ratio.py / harmonic_analysis.py
can colour its plots by model.

!! KEY.CSV PRIVACY !!
---------------------
results/key.csv is gitignored and must NOT be opened during rating.
Even a glance at a few rows breaks the blind. Keep it closed until
both raters have submitted all 30 scores.

USAGE
-----
    python blind_rename.py                  # dry-run: shows plan, asks to confirm
    python blind_rename.py --dry-run        # prints plan only, exits without asking
    python blind_rename.py --pieces ../pieces/ --results ../results/
"""

import argparse
import csv
import os
import random
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Audio extensions to include when scanning pieces/
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".ogg", ".m4a"}

# Prompt names keyed by prompt ID — used to fill in the prompt_name column.
# These match the 6 prompts defined in PROMPTS.md.
PROMPT_NAMES = {
    "p1": "Up-Tempo Bebop Head",
    "p2": "Modal Jazz (Kind of Blue Style)",
    "p3": "Jazz Ballad with Lush Extensions",
    "p4": "12-Bar Jazz Blues in Bb",
    "p5": "Up-Tempo Swing (Big Band / Basie Style)",
    "p6": "Latin Jazz (Bossa Nova / Afro-Cuban)",
}

# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

# Matches: {model}_{prompt_id}_raw.{ext}
# Examples: suno_p1_raw.mp3  /  stable_audio_p3_raw.wav
_NAMING_PATTERN = re.compile(
    r"^(?P<model>[a-zA-Z0-9_-]+?)_(?P<prompt_id>p\d+)_raw\.[a-zA-Z0-9]+$",
    re.IGNORECASE,
)


def parse_filename(filename: str) -> tuple[str, str, str]:
    """
    Try to extract model and prompt_id from a filename.

    Returns (model, prompt_id, prompt_name). All three are empty strings if
    the filename does not match the expected convention.
    """
    m = _NAMING_PATTERN.match(filename)
    if m:
        model = m.group("model").lower()
        prompt_id = m.group("prompt_id").lower()
        prompt_name = PROMPT_NAMES.get(prompt_id, "")
        return model, prompt_id, prompt_name
    return "", "", ""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def scan_pieces(pieces_dir: Path) -> list[Path]:
    """Return all audio files in pieces_dir, sorted by name."""
    files = [
        p for p in pieces_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]
    return sorted(files)


def build_mapping(files: list[Path]) -> list[dict]:
    """
    Randomly shuffle files and assign piece_01, piece_02, ... IDs.

    Returns a list of dicts (one per file) with keys:
        piece_id, original_filename, model, prompt_id, prompt_name, new_path
    """
    shuffled = files[:]
    random.shuffle(shuffled)

    n_digits = max(2, len(str(len(shuffled))))  # at least 2 digits for clean sorting
    mapping = []

    for i, original_path in enumerate(shuffled, start=1):
        piece_id = f"piece_{i:0{n_digits}d}"
        new_filename = piece_id + original_path.suffix.lower()
        new_path = original_path.parent / new_filename

        model, prompt_id, prompt_name = parse_filename(original_path.name)

        mapping.append({
            "piece_id": piece_id,
            "original_filename": original_path.name,
            "model": model,
            "prompt_id": prompt_id,
            "prompt_name": prompt_name,
            "original_path": original_path,
            "new_path": new_path,
        })

    return mapping


def check_naming_warnings(mapping: list[dict]) -> bool:
    """
    Print a warning for any file whose model/prompt could not be parsed.
    Returns True if any warnings were found.
    """
    unparsed = [row for row in mapping if not row["model"]]
    if not unparsed:
        return False

    print()
    print("=" * 70)
    print("  WARNING: Could not parse model/prompt_id from these filenames.")
    print()
    print("  Expected format:  {model}_{prompt_id}_raw.{ext}")
    print("  Example:          suno_p1_raw.mp3")
    print()
    print("  Affected files:")
    for row in unparsed:
        print(f"    {row['original_filename']}")
    print()
    print("  ACTION REQUIRED: After blinding, open results/key.csv and fill in")
    print("  the model, prompt_id, and prompt_name columns for these rows.")
    print("  This is needed before batch_analyze can colour plots by model.")
    print("=" * 70)
    print()
    return True


def print_dry_run_table(mapping: list[dict]) -> None:
    """Print the planned rename mapping as a human-readable table."""
    print()
    print("  PLANNED RENAME MAPPING")
    print("  " + "-" * 62)
    print(f"  {'NEW NAME':<14}  {'ORIGINAL FILENAME':<35}  {'MODEL'}")
    print("  " + "-" * 62)
    for row in mapping:
        model_display = row["model"] if row["model"] else "(fill in manually)"
        print(f"  {row['piece_id'] + row['new_path'].suffix:<14}  "
              f"{row['original_filename']:<35}  {model_display}")
    print("  " + "-" * 62)
    print(f"  Total: {len(mapping)} files")
    print()


def write_key_csv(mapping: list[dict], key_path: Path) -> None:
    """
    Write results/key.csv — the decode key that maps piece IDs back to models.

    !!! THIS FILE MUST NOT BE OPENED DURING RATING !!!
    """
    key_path.parent.mkdir(parents=True, exist_ok=True)

    with open(key_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["piece_id", "original_filename", "model", "prompt_id", "prompt_name"],
        )
        writer.writeheader()
        for row in mapping:
            writer.writerow({
                "piece_id": row["piece_id"],
                "original_filename": row["original_filename"],
                "model": row["model"],
                "prompt_id": row["prompt_id"],
                "prompt_name": row["prompt_name"],
            })

    print(f"  Key written to: {key_path}")
    print()
    print("  !! CLOSE key.csv NOW. Do not open it again until both raters")
    print("  !! have submitted all scores. See methodology.md §3.")
    print()


def do_renames(mapping: list[dict]) -> None:
    """Rename files according to the mapping. key.csv is written first."""
    for row in mapping:
        original = row["original_path"]
        new = row["new_path"]
        if original == new:
            continue
        if new.exists():
            print(f"  SKIP (target already exists): {new.name}")
            continue
        original.rename(new)
        print(f"  Renamed: {original.name}  →  {new.name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Blind-rename audio files in pieces/ before rating.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python blind_rename.py              # shows plan, asks for confirmation
  python blind_rename.py --dry-run    # shows plan only, does nothing
  python blind_rename.py --pieces /path/to/pieces --results /path/to/results
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rename plan and exit without making any changes.",
    )
    parser.add_argument(
        "--pieces",
        default="../pieces",
        metavar="DIR",
        help="Directory containing the original audio files (default: ../pieces)",
    )
    parser.add_argument(
        "--results",
        default="../results",
        metavar="DIR",
        help="Directory where key.csv will be written (default: ../results)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help="Random seed for reproducible shuffling (optional).",
    )

    args = parser.parse_args()

    pieces_dir = Path(args.pieces).resolve()
    key_path = Path(args.results).resolve() / "key.csv"

    # --- Validate pieces dir ---
    if not pieces_dir.exists():
        print(f"ERROR: pieces directory not found: {pieces_dir}")
        sys.exit(1)

    files = scan_pieces(pieces_dir)

    if not files:
        print(f"No audio files found in {pieces_dir}")
        print(f"Supported extensions: {', '.join(sorted(AUDIO_EXTENSIONS))}")
        sys.exit(0)

    if len(files) != 30:
        print(f"  NOTE: Found {len(files)} audio files (expected 30 for the full study).")
        print(f"  That's fine — proceed when you have all files, or blind in batches.")
        print()

    # --- Check if key.csv already exists (don't overwrite silently) ---
    if key_path.exists():
        print(f"WARNING: {key_path} already exists.")
        resp = input("  Overwrite the existing key and re-blind? This will re-shuffle. [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            sys.exit(0)

    # --- Build and show the mapping ---
    if args.seed is not None:
        random.seed(args.seed)

    mapping = build_mapping(files)
    has_warnings = check_naming_warnings(mapping)
    print_dry_run_table(mapping)

    if args.dry_run:
        print("  Dry-run mode: no files changed.")
        sys.exit(0)

    # --- Ask for confirmation ---
    print("  This will:")
    print(f"    1. Write the decode key to:  {key_path}")
    print(f"    2. Rename {len(files)} files in:   {pieces_dir}")
    print()
    if has_warnings:
        print("  Remember to fill in the blank model/prompt columns in key.csv afterwards.")
        print()

    resp = input("  Proceed with blinding? [y/N] ").strip().lower()
    if resp != "y":
        print("Aborted. No files changed.")
        sys.exit(0)

    # --- Execute ---
    print()
    write_key_csv(mapping, key_path)
    do_renames(mapping)

    print()
    print("  Blinding complete.")
    print(f"  {len(mapping)} files renamed in {pieces_dir}")
    print(f"  Decode key stored in {key_path}")
    print()
    print("  Next steps:")
    print("    1. Fill in any blank rows in key.csv (if warned above)")
    print("    2. Run: python rating_helper.py   to begin scoring")
    print("    3. Do NOT re-open key.csv until both raters are done")


if __name__ == "__main__":
    main()
