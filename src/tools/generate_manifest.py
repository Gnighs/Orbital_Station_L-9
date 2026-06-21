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
INDEXES_PATH = DOCUMENTS_DIR / "indexes.json"
FILES_CATALOG = "files.json"

VALID_STATUSES = {"Cleared", "InProgress", "Classified"}
STATUS_DETAILS = {
    "Cleared": {
        "className": "cleared",
        "statusLabel": "Current Archive Copy",
        "actionLabel": "View PDF",
    },
    "InProgress": {
        "className": "in-progress",
        "statusLabel": "Work In Progress",
        "actionLabel": "View PDF",
    },
    "Classified": {
        "className": "classified",
        "statusLabel": "Classified",
        "actionLabel": "PDF Unavailable",
    },
}

DEFAULT_EMPTY_WARNING = "INDEX UNDER MAINTENANCE"
DEFAULT_EMPTY_MESSAGE = "No public records are available through this terminal. Index reconstruction is pending curator clearance."


def title_from_slug(value):
    normalized = value.replace("-", " ").replace("_", " ")
    return " ".join(word.capitalize() for word in normalized.split())


def read_json(path, fallback):
    if not path.exists():
        path.write_text(json.dumps(fallback, indent=2) + "\n", encoding="utf-8")
        return fallback

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error


def default_index(folder):
    title = title_from_slug(folder.name)
    return {
        "id": folder.name,
        "title": title,
        "description": "Station records filed under a newly opened archive heading.",
        "emptyWarning": DEFAULT_EMPTY_WARNING,
        "emptyTitle": f"{title} records are not yet available through the public terminal.",
        "emptyMessage": DEFAULT_EMPTY_MESSAGE,
    }


def ensure_indexes():
    folders = sorted(
        (
            path for path in DOCUMENTS_DIR.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ),
        key=lambda folder: folder.name.lower(),
    )

    if not INDEXES_PATH.exists():
        indexes = [default_index(folder) for folder in folders]
        INDEXES_PATH.write_text(json.dumps(indexes, indent=2) + "\n", encoding="utf-8")
        return indexes

    indexes = read_json(INDEXES_PATH, [])
    if not isinstance(indexes, list):
        raise SystemExit(f"{INDEXES_PATH} must contain a JSON list.")

    listed_ids = {
        str(index.get("id"))
        for index in indexes
        if isinstance(index, dict) and index.get("id")
    }
    missing_indexes = [
        default_index(folder)
        for folder in folders
        if folder.name not in listed_ids
    ]

    if missing_indexes:
        indexes.extend(missing_indexes)
        INDEXES_PATH.write_text(json.dumps(indexes, indent=2) + "\n", encoding="utf-8")

    return indexes


def clean_index(raw_index):
    if not isinstance(raw_index, dict) or not raw_index.get("id"):
        raise SystemExit("Every item in documents/indexes.json must be an object with an id.")

    index_id = str(raw_index["id"])
    title = str(raw_index.get("title") or title_from_slug(index_id))

    return {
        "id": index_id,
        "title": title,
        "description": str(raw_index.get("description") or "Station records filed under a newly opened archive heading."),
        "emptyWarning": str(raw_index.get("emptyWarning") or DEFAULT_EMPTY_WARNING),
        "emptyTitle": str(raw_index.get("emptyTitle") or f"{title} records are not yet available through the public terminal."),
        "emptyMessage": str(raw_index.get("emptyMessage") or DEFAULT_EMPTY_MESSAGE),
    }


def ensure_files_catalog(folder):
    path = folder / FILES_CATALOG
    files = read_json(path, [])
    if not isinstance(files, list):
        raise SystemExit(f"{path} must contain a JSON list.")

    return files


def href_for(index_id, relative_path):
    parts = ["..", "documents", index_id, *Path(relative_path).parts]
    return "/".join(part if part == ".." else quote(part) for part in parts)


def normalize_file(raw_file, index_id, folder):
    if not isinstance(raw_file, dict):
        raise SystemExit(f"Every file item in {folder / FILES_CATALOG} must be an object.")

    title = str(raw_file.get("title") or "").strip()
    record_id = str(raw_file.get("id") or "").strip()
    status = str(raw_file.get("status") or "Cleared").strip()
    relative_path = str(raw_file.get("path") or "").strip()

    if not title:
        raise SystemExit(f"A file item in {folder / FILES_CATALOG} is missing title.")
    if not record_id:
        raise SystemExit(f"File '{title}' in {folder / FILES_CATALOG} is missing id.")
    if status not in VALID_STATUSES:
        raise SystemExit(f"File '{title}' in {folder / FILES_CATALOG} has invalid status '{status}'. Use Cleared, InProgress, or Classified.")

    details = STATUS_DETAILS[status]
    linked_file_exists = bool(relative_path) and (folder / relative_path).is_file()
    is_available = linked_file_exists and status != "Classified"

    return {
        "id": record_id,
        "title": title,
        "path": f"documents/{index_id}/{relative_path}" if relative_path else "",
        "href": href_for(index_id, relative_path) if is_available else "",
        "status": status,
        "className": details["className"],
        "statusLabel": details["statusLabel"],
        "actionLabel": details["actionLabel"] if is_available else "PDF Unavailable",
        "isAvailable": is_available,
    }


def build_manifest():
    sections = []

    for raw_index in ensure_indexes():
        index = clean_index(raw_index)
        folder = DOCUMENTS_DIR / index["id"]
        folder.mkdir(exist_ok=True)
        (folder / "files").mkdir(exist_ok=True)
        raw_files = ensure_files_catalog(folder)
        documents = [
            normalize_file(raw_file, index["id"], folder)
            for raw_file in raw_files
        ]

        sections.append({
            "id": index["id"],
            "title": index["title"],
            "description": index["description"],
            "status": "available" if documents else "maintenance",
            "maintenanceLine": index["emptyWarning"],
            "emptyTitle": index["emptyTitle"],
            "emptyMessage": index["emptyMessage"],
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
