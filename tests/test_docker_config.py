from pathlib import Path

from app.core.config import Settings


def _env_name(field_name: str) -> str:
    return field_name.upper()


def test_env_example_matches_settings_fields():
    example_path = Path(".env.example")
    lines = [
        line.strip()
        for line in example_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    keys = {line.split("=", 1)[0] for line in lines}
    expected = {_env_name(name) for name in Settings.model_fields}
    assert keys == expected


def test_pydantic_settings_auto_mapping():
    settings = Settings(_env_file=None, torch_num_threads=4, log_level="DEBUG")
    assert settings.torch_num_threads == 4
    assert settings.log_level == "DEBUG"
