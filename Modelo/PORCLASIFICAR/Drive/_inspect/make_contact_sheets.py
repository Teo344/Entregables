from __future__ import annotations

import glob
import hashlib
import io
import os
import zipfile

from PIL import Image, ImageDraw


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT = os.path.dirname(__file__)
by_class: dict[str, dict[str, tuple[str, bytes]]] = {"0": {}, "1": {}}

for zip_path in glob.glob(os.path.join(ROOT, "*.zip")):
    with zipfile.ZipFile(zip_path) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or not entry.filename.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            ):
                continue
            parts = entry.filename.split("/")
            if len(parts) < 3 or parts[-2] not in by_class:
                continue
            data = archive.read(entry)
            digest = hashlib.sha256(data).hexdigest()
            by_class[parts[-2]].setdefault(digest, (entry.filename, data))

for class_id, records in by_class.items():
    ordered = sorted(records.values(), key=lambda item: item[0])
    step = max(1, len(ordered) // 20)
    samples = ordered[::step][:20]
    width, height, columns = 220, 190, 5
    rows = (len(samples) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * width, rows * height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (name, data) in enumerate(samples):
        image = Image.open(io.BytesIO(data)).convert("RGB")
        image.thumbnail((width - 12, height - 45))
        x, y = (index % columns) * width, (index // columns) * height
        sheet.paste(image, (x + (width - image.width) // 2, y + 3))
        draw.text((x + 5, y + height - 38), f"class {class_id} | {name[:28]}", fill="black")
    output_path = os.path.join(OUTPUT, f"contact_class_{class_id}.jpg")
    sheet.save(output_path, quality=88)
    print(f"class {class_id}: {len(records)} unique images, {len(samples)} sampled -> {output_path}")
