import hashlib
import re
from pathlib import Path


def _compute_hash(path: Path):
    sh256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 13):
            sh256.update(chunk)

    return sh256.hexdigest()


def _get_stored_hash(path: Path):
    if not path.exists():
        return None
    text = path.read_text()

    match = re.search(r'_xml_hash\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None
