#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SRC_DIR.parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
OUTPUT_PATH = SRC_DIR / "archive-manifest.js"
ORDER_PATH = DOCUMENTS_DIR / "order.txt"
METADATA_FILE = "archive.json"

SECTION_DESCRIPTIONS = {
    "languages": "Reference grammars, lexicons, scripts, and linguistic survey material.",
    "biology": "Xenobiological field reports, anatomical plates, and ecological notes.",
    "cultures": "Ethnographic dossiers, settlement records, ritual notes, and political briefs.",
    "miscellany": "Unsorted transmissions, partial records, and recovered archival fragments.",
}

DEFAULT_EMPTY_WARNING = "INDEX UNDER MAINTENANCE"


def title_from_slug(value):
    normalized = value.replace("-", " ").replace("_", " ")
    return " ".join(word.capitalize() for word in normalized.split())


def title_from_pdf(path):
    stem = path.stem
    for suffix in ("-WIP", "_WIP", " WIP"):
        if stem.upper().endswith(suffix):
            stem = stem[:-len(suffix)]
            break

    return title_from_slug(stem)


def document_status(path):
    stem = path.stem.upper()
    is_wip = stem.endswith("-WIP") or stem.endswith("_WIP") or stem.endswith(" WIP")

    if is_wip:
        return {
            "status": "wip",
            "statusLabel": "Work In Progress",
        }

    return {
        "status": "current",
        "statusLabel": "Current Archive Copy",
    }


def default_metadata(folder_name):
    return {
        "title": title_from_slug(folder_name),
        "description": SECTION_DESCRIPTIONS.get(
            folder_name,
            "Station records filed under a newly opened archive heading.",
        ),
        "emptyWarning": DEFAULT_EMPTY_WARNING,
    }


def read_metadata(folder):
    metadata_path = folder / METADATA_FILE
    defaults = default_metadata(folder.name)

    if not metadata_path.exists():
        metadata_path.write_text(
            json.dumps(defaults, indent=2) + "\n",
            encoding="utf-8",
        )
        return defaults

    try:
        loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {metadata_path}: {error}") from error

    return {
        "title": str(loaded.get("title") or defaults["title"]),
        "description": str(loaded.get("description") or defaults["description"]),
        "emptyWarning": str(loaded.get("emptyWarning") or defaults["emptyWarning"]),
    }


def ordered_folders(folders):
    by_name = {folder.name: folder for folder in folders}
    folder_names = set(by_name)

    if not ORDER_PATH.exists():
        ORDER_PATH.write_text(
            "\n".join(folder.name for folder in folders) + "\n",
            encoding="utf-8",
        )
        return folders

    ordered_names = [
        line.strip()
        for line in ORDER_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    missing_names = [
        folder.name for folder in folders
        if folder.name not in ordered_names
    ]

    if missing_names:
        ORDER_PATH.write_text(
            "\n".join([
                *(name for name in ordered_names if name in folder_names),
                *missing_names,
            ]) + "\n",
            encoding="utf-8",
        )

    ordered = [by_name.pop(name) for name in ordered_names if name in by_name]
    ordered.extend(sorted(by_name.values(), key=lambda folder: folder.name.lower()))

    return ordered


def station_id(section_name, relative_path):
    raw = f"{section_name}/{relative_path.with_suffix('')}"
    clean = []
    previous_dash = False

    for char in raw:
        if char.isalnum():
            clean.append(char.upper())
            previous_dash = False
        elif not previous_dash:
            clean.append("-")
            previous_dash = True

    return f"L9-{''.join(clean).strip('-')}"


def href_for(section_name, relative_path):
    parts = ["..", "documents", section_name, *relative_path.parts]
    return "/".join(part if part == ".." else quote(part) for part in parts)


def collect_pdfs(section_path):
    return sorted(
        (
            path.relative_to(section_path)
            for path in section_path.rglob("*")
            if path.is_file()
            and not any(part.startswith(".") for part in path.parts)
            and path.name != METADATA_FILE
            and path.suffix.lower() == ".pdf"
        ),
        key=lambda path: str(path).lower(),
    )


def build_manifest():
    folders = ordered_folders(sorted(
        (
            path for path in DOCUMENTS_DIR.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ),
        key=lambda folder: folder.name.lower(),
    ))
    sections = []

    for folder in folders:
        metadata = read_metadata(folder)
        pdfs = collect_pdfs(folder)
        documents = [
            {
                "id": station_id(folder.name, relative_path),
                "title": title_from_pdf(relative_path),
                "fileName": relative_path.name,
                "href": href_for(folder.name, relative_path),
                "path": f"documents/{folder.name}/{relative_path.as_posix()}",
                **document_status(relative_path),
            }
            for relative_path in pdfs
        ]

        sections.append({
            "id": folder.name,
            "title": metadata["title"],
            "description": metadata["description"],
            "status": "available" if documents else "maintenance",
            "maintenanceLine": metadata["emptyWarning"],
            "count": len(documents),
            "documents": documents,
        })

    return {
        "station": "Orbital Archive Station L-9",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sections": sections,
    }


def main():
    manifest = build_manifest()
    OUTPUT_PATH.write_text(
        f"window.archiveManifest = {json.dumps(manifest, indent=2)};\n",
        encoding="utf-8",
    )
    print(f"Generated {OUTPUT_PATH.relative_to(PROJECT_ROOT)} with {len(manifest['sections'])} sections.")


if __name__ == "__main__":
    main()
