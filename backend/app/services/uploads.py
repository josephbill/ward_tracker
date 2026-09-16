import uuid
from pathlib import Path

from werkzeug.utils import secure_filename


def save_photo(file_storage, upload_dir: Path) -> str | None:
    if file_storage is None or file_storage.filename == "":
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else "jpg"
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    file_storage.save(dest)
    return str(dest)
