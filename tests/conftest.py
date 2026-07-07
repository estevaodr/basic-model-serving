import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), color=(128, 64, 32))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()
