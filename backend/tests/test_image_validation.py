from io import BytesIO

import pytest
from PIL import Image

from app.core.errors import AppError
from app.services.image_validation import validate_image


def make_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (1, 1), color=(220, 80, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


PNG_1X1 = make_png()


def test_valid_png() -> None:
    assert validate_image(PNG_1X1, "image/png", 1024) == "image/png"


def test_rejects_wrong_mime() -> None:
    with pytest.raises(AppError) as caught:
        validate_image(PNG_1X1, "text/plain", 1024)
    assert caught.value.code == "unsupported_image"


def test_rejects_oversized_image() -> None:
    with pytest.raises(AppError) as caught:
        validate_image(PNG_1X1, "image/png", 10)
    assert caught.value.code == "image_too_large"

