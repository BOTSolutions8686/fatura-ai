"""
Invoice layout fingerprinting — perceptual hash of the first page.
Uses average hash (aHash) on a downscaled thumbnail for robust layout matching.
"""
from PIL import Image
from pdf2image import convert_from_path


_HASH_SIZE = 16


def compute_layout_hash(file_path: str) -> str:
    images = _file_to_image(file_path)
    if not images:
        return ""
    img = images[0].convert("L").resize((_HASH_SIZE, _HASH_SIZE), Image.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = ["1" if p >= avg else "0" for p in pixels]
    return hex(int("".join(bits), 2))[2:].zfill(_HASH_SIZE * _HASH_SIZE // 4)


def _file_to_image(file_path: str):
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    if ext in ("png", "jpg", "jpeg", "webp", "tiff", "tif"):
        return [Image.open(file_path)]
    try:
        return convert_from_path(file_path, dpi=72, first_page=1, last_page=1)
    except Exception:
        return None
