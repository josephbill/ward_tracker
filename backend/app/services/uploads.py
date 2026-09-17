import logging
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

logger = logging.getLogger("uploads")


def _strip_exif(dest: Path) -> None:
    """Privacy hardening (gap-fill Section 3): phone photos routinely carry
    GPS coordinates and device info in EXIF, which is far more precise than
    the GPS we deliberately round to neighbourhood-level (see
    report_service.round_gps) — re-saving via Pillow with a fresh image
    buffer (no `exif=` kwarg passed through) drops that metadata rather than
    just the tags we happen to know about. Best-effort: a photo Pillow can't
    parse (a format decode issue, corrupt upload) is still kept as-is rather
    than rejecting the whole report over an image library limitation."""
    try:
        from PIL import Image

        with Image.open(dest) as img:
            data = list(img.getdata())
            clean = Image.new(img.mode, img.size)
            clean.putdata(data)
            clean.save(dest)
    except Exception:
        logger.warning("Could not strip EXIF from %s — keeping original file.", dest, exc_info=True)


def save_photo(file_storage, upload_dir: Path) -> str | None:
    if file_storage is None or file_storage.filename == "":
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else "jpg"
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    file_storage.save(dest)
    if ext in {"jpg", "jpeg", "png", "webp"}:
        _strip_exif(dest)
    return str(dest)
