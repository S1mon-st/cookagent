from __future__ import annotations

from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.errors import AppError


ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_image(data: bytes, content_type: str | None, max_bytes: int) -> str:
    if not data:
        raise AppError("empty_image", "请选择一张食材图片。")
    if len(data) > max_bytes:
        raise AppError("image_too_large", f"图片不能超过 {max_bytes // 1024 // 1024} MB。")
    if content_type not in ALLOWED_MIME_TYPES:
        raise AppError("unsupported_image", "仅支持 JPG、PNG 或 WebP 图片。")
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise AppError("invalid_image", "图片文件已损坏或不是有效图片。") from exc
    return content_type

