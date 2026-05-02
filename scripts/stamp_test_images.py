"""Stamp data/images/TC*.jpg with progressive EXIF DateTimeOriginal values.

Why: iOS Photos sorts album thumbnails by EXIF capture date. When AirDropped together,
all images get the same import timestamp and the displayed order becomes undefined,
which breaks the contract that picker cell [N] == TC<N>.jpg in the on-device album.

After running this script and re-importing to the phone, cell [1] == TC01, ..., cell [31] == TC31
in NutriSnapTests album.

Usage:
    python scripts/stamp_test_images.py
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import piexif

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "data" / "images"

BASE_DATETIME = datetime(2026, 1, 1, 12, 0, 0)
INCREMENT = timedelta(minutes=10)


def _format_exif_datetime(dt: datetime) -> bytes:
    return dt.strftime("%Y:%m:%d %H:%M:%S").encode("ascii")


# Tags that confuse iOS Photos when present without matching the new naive timestamp.
# Stripping OffsetTime* avoids the bug where a non-Pacific OffsetTime shifts the displayed date.
# Stripping SubSec* avoids fractional-second sort surprises when timestamps are 10 min apart.
_EXIF_TZ_TAGS_TO_REMOVE = (
    piexif.ExifIFD.OffsetTime,
    piexif.ExifIFD.OffsetTimeOriginal,
    piexif.ExifIFD.OffsetTimeDigitized,
    piexif.ExifIFD.SubSecTime,
    piexif.ExifIFD.SubSecTimeOriginal,
    piexif.ExifIFD.SubSecTimeDigitized,
)


def _stamp_one(jpg_path: Path, dt: datetime) -> None:
    """Write DateTimeOriginal/DateTimeDigitized/DateTime to a JPEG in place.

    Also wipes OffsetTime*/SubSec* fields so iOS Photos interprets the new timestamp
    as the device's local time (no surprise timezone shifts).
    """
    try:
        exif_dict = piexif.load(str(jpg_path))
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    stamp = _format_exif_datetime(dt)
    exif_dict.setdefault("Exif", {})[piexif.ExifIFD.DateTimeOriginal] = stamp
    exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = stamp
    exif_dict.setdefault("0th", {})[piexif.ImageIFD.DateTime] = stamp

    for tag in _EXIF_TZ_TAGS_TO_REMOVE:
        exif_dict["Exif"].pop(tag, None)

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, str(jpg_path))


def main() -> int:
    if not IMAGES_DIR.is_dir():
        print(f"ERROR: images dir not found: {IMAGES_DIR}", file=sys.stderr)
        return 1

    pattern = re.compile(r"^TC(\d{2})\.(?:jpg|jpeg|png)$", re.IGNORECASE)
    jpgs = sorted(
        (p for p in IMAGES_DIR.iterdir() if pattern.match(p.name)),
        key=lambda p: int(pattern.match(p.name).group(1)),
    )

    if not jpgs:
        print(f"ERROR: no TCNN.jpg files matched in {IMAGES_DIR}", file=sys.stderr)
        return 1

    print(f"Found {len(jpgs)} test images. Writing progressive EXIF dates...")
    for idx, jpg in enumerate(jpgs):
        dt = BASE_DATETIME + idx * INCREMENT
        try:
            _stamp_one(jpg, dt)
            print(f"  {jpg.name:>10}  ->  {dt:%Y-%m-%d %H:%M:%S}")
        except Exception as exc:
            print(f"  {jpg.name:>10}  -> FAILED ({exc!r})", file=sys.stderr)
            return 2

    print("\nDone. Now on the phone:")
    print("  1. Photos -> Albums -> NutriSnapTests -> select all -> Delete from album")
    print("     (or delete the album entirely and let it re-create on import).")
    print("  2. AirDrop the freshly-stamped data/images/ folder back to the phone.")
    print("  3. Re-create the NutriSnapTests album with the imported photos.")
    print("  4. Photos will now show TC01 first, TC31 last (ascending capture date).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
