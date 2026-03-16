"""Shared test fixtures and configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env from project root so API keys are available for model resolution.
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip dataset_download tests when --no-dataset flag is used."""
    # This is a no-op for now; markers are registered in pyproject.toml.
    pass
