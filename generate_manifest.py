#!/usr/bin/env python3
"""
Generate / refresh manifest.json for the islami-era-sounds GitHub repository.

Run it from the ROOT of that repository after adding or replacing .wav files:

    python3 generate_manifest.py --username YOUR_GITHUB_USERNAME

What it does
  * scans every  era_<key>/  folder for *.wav files
  * computes SHA-256 per file  (the app verifies it after download)
  * bumps an era's "version" ONLY when its files (names or contents) changed since the
    previous manifest.json  → installed apps re-download exactly that era
  * keeps "initial" / "unlock_condition" from the previous manifest (or defaults for new eras)
  * warns about eras that do not have all 5 required sound files

Only the Python standard library is needed.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

REQUIRED_EVENTS = ["tap", "select", "success", "error", "unlock_legendary"]
BASE_ERAS = {"contemporary", "umayyad", "mamluk"}  # HeritageEra.isBaseEra
DEFAULT_UNLOCK = {  # informational only (mirrors EraUnlockAchievementMap)
    "abbasid": "KHATMAT_FINISHED", "ottoman": "COMPETITION_50_WINS", "andalusian": "TASBIH_STREAK_30",
    "fatimid": "QUIZ_GRANDMASTER", "seljuk": "COMMUNITY_CHAMPION", "safavid": "MATCHING_GRANDMASTER",
    "mughal": "GOLD_COLLECTOR", "ghaznavid": "COMPETITION_100_WINS", "ayyubid": "OFFICIAL_100_WINS",
    "mali": "RANDOM_DOMINATOR", "ilkhanate": "ORDERING_GRANDMASTER", "samanid": "HARD_MASTER",
    "timurid": "EXPERT_MASTER", "kilwa": "FASTEST_PLAYER", "malacca": "SUPER_HOST", "songhai": "VIEWERS_10000",
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--username", required=True, help="GitHub username that owns the repository")
    parser.add_argument("--repo", default="islami-era-sounds")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_path = root / "manifest.json"
    previous = {}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8")).get("eras", {})

    eras = {}
    for folder in sorted(p for p in root.glob("era_*") if p.is_dir()):
        key = folder.name[len("era_"):]
        files = sorted(p.name for p in folder.glob("*.wav"))
        if not files:
            print(f"! {folder.name}: no .wav files, skipped", file=sys.stderr)
            continue
        expected = {f"sound_{key}_{event}.wav" for event in REQUIRED_EVENTS}
        missing = sorted(expected - set(files))
        if missing:
            print(f"! {folder.name}: missing required files: {', '.join(missing)}", file=sys.stderr)

        checksums = {name: sha256_of(folder / name) for name in files}
        old = previous.get(key, {})
        changed = old.get("files") != files or old.get("sha256") != checksums
        version = old.get("version", 0) + 1 if (changed and old) else old.get("version", 1)

        entry = {"initial": old.get("initial", key in BASE_ERAS), "version": version}
        condition = old.get("unlock_condition", DEFAULT_UNLOCK.get(key))
        if condition:
            entry["unlock_condition"] = condition
        entry.update({"files": files, "sha256": checksums})
        eras[key] = entry
        print(f"{'*' if changed else '='} {key}: v{version} ({len(files)} files){' [changed]' if changed and old else ''}")

    global_version = 1
    if manifest_path.exists():
        global_version = json.loads(manifest_path.read_text(encoding="utf-8")).get("version", 0)
        if eras != previous:
            global_version += 1

    base = f"https://raw.githubusercontent.com/{args.username}/{args.repo}/{args.branch}/"
    mirror = f"https://cdn.jsdelivr.net/gh/{args.username}/{args.repo}@{args.branch}/"
    manifest = {"version": global_version, "base_url": base, "fallback_urls": [mirror], "eras": eras}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {manifest_path} with {len(eras)} era(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
