"""Stage unique class-1 photos from the Drive ZIPs for expert review.

The numeric source label is retained as provenance. The script never treats it
as a confirmed phytosanitary diagnosis; staged images remain review candidates.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

from PIL import Image, UnidentifiedImageError


MODEL_DIR = Path(__file__).resolve().parents[1]
ZIP_DIR = MODEL_DIR / "PORCLASIFICAR" / "DRIVE"
DEST_DIR = MODEL_DIR / "PEDUNCULO" / "DRIVE_CANDIDATAS"
MANIFEST = MODEL_DIR / "PEDUNCULO" / "drive_candidates.csv"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def main() -> None:
    archives = sorted(ZIP_DIR.glob("*.zip"))
    if not archives:
        raise SystemExit(f"No ZIP files found in {ZIP_DIR}")
    if DEST_DIR.exists() or MANIFEST.exists():
        raise SystemExit(
            f"Output already exists; inspect before rerunning: {DEST_DIR} / {MANIFEST}"
        )

    by_digest: dict[str, list[dict[str, object]]] = defaultdict(list)
    for archive_path in archives:
        with zipfile.ZipFile(archive_path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise SystemExit(f"Corrupt ZIP member in {archive_path.name}: {bad_member}")
            for entry in archive.infolist():
                if entry.is_dir() or Path(entry.filename).suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                parts = entry.filename.split("/")
                if len(parts) < 3 or parts[-2] not in {"0", "1"}:
                    continue
                data = archive.read(entry)
                digest = hashlib.sha256(data).hexdigest()
                by_digest[digest].append(
                    {
                        "zip": archive_path.name,
                        "entry": entry.filename,
                        "source_class": parts[-2],
                        "source_split": parts[-3],
                        "filename": Path(entry.filename).name,
                        "data": data,
                    }
                )

    DEST_DIR.mkdir(parents=True)
    rows: list[dict[str, object]] = []
    copied = 0
    conflicts = 0
    unreadable = 0
    for digest, occurrences in sorted(by_digest.items()):
        class_ids = sorted({str(item["source_class"]) for item in occurrences})
        if "1" not in class_ids:
            continue

        references = [f"{item['zip']}::{item['entry']}" for item in occurrences]
        splits = sorted({str(item["source_split"]) for item in occurrences})
        source_files = sorted({str(item["filename"]) for item in occurrences})
        representative = occurrences[0]
        data = bytes(representative["data"])
        candidate_id = f"ring_{digest[:12]}"
        copy_path = ""
        width = height = ""
        image_format = ""

        if len(class_ids) > 1:
            status = "excluded_label_conflict"
            conflicts += 1
        else:
            try:
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
                with Image.open(io.BytesIO(data)) as image:
                    width, height = image.size
                    image_format = image.format or ""
            except (UnidentifiedImageError, OSError, ValueError):
                status = "excluded_unreadable_image"
                unreadable += 1
            else:
                original_name = str(representative["filename"])
                staged_name = f"{candidate_id}__{original_name}"
                (DEST_DIR / staged_name).write_bytes(data)
                copy_path = (DEST_DIR / staged_name).relative_to(MODEL_DIR).as_posix()
                status = (
                    "candidate_multiple_splits_pending_review"
                    if len(splits) > 1
                    else "candidate_pending_expert_review"
                )
                copied += 1

        rows.append(
            {
                "candidate_id": candidate_id,
                "sha256": digest,
                "source_class_ids": ";".join(class_ids),
                "proposed_project_class": "peduncle_ring_compatible"
                if len(class_ids) == 1
                else "",
                "review_status": status,
                "source_splits": ";".join(splits),
                "source_occurrence_count": len(occurrences),
                "source_references_json": json.dumps(references, ensure_ascii=False),
                "original_filenames": ";".join(source_files),
                "copy_relative_path": copy_path,
                "width": width,
                "height": height,
                "format": image_format,
            }
        )

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"ZIP archives scanned: {len(archives)}")
    print(f"Unique class-1 content groups: {sum('1' in row['source_class_ids'].split(';') for row in rows)}")
    print(f"Staged readable candidates: {copied}")
    print(f"Excluded label conflicts: {conflicts}")
    print(f"Excluded unreadable images: {unreadable}")
    print(f"Manifest: {MANIFEST}")
    print(f"Copies: {DEST_DIR}")


if __name__ == "__main__":
    main()
