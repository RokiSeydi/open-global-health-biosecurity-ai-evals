"""Eval metadata loader — reads eval.yaml files for task versioning.

Mirrors the pattern used in UK AISI's inspect_evals so that each eval
directory contains an ``eval.yaml`` with title, description, version,
and task metadata. The version string follows the ``<comparability>-<interface>``
scheme (e.g. ``"1-A"``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


class TaskVersion:
    """Parsed task version following the ``<int>-<letter>`` scheme.

    Examples: ``"1-A"``, ``"2-B"``.
    """

    _pattern = re.compile(r"^\d+-[A-Z]$")

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("TaskVersion must be a string")
        if not self._pattern.fullmatch(value):
            raise ValueError(
                f"version must be like '1-A', '2-B', got '{value}'"
            )
        comparability, interface = value.split("-")
        self.full_version: str = value
        self.comparability_version: int = int(comparability)
        self.interface_version: str = interface

    def __str__(self) -> str:
        return self.full_version

    def to_metadata(self) -> dict[str, Any]:
        """Return a dict suitable for ``Task(metadata=...)``."""
        return {
            "full_task_version": self.full_version,
            "task_interface_version": self.interface_version,
            "task_comparability_version": self.comparability_version,
        }


class EvalMetadata:
    """Lightweight container for fields parsed from ``eval.yaml``."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.title: str = data["title"]
        self.description: str = data["description"]
        self.version: TaskVersion = TaskVersion(data["version"])
        self.group: str = data.get("group", "")
        self.contributors: list[str] = data.get("contributors", [])
        self.tasks: list[dict[str, Any]] = data.get("tasks", [])
        self._raw: dict[str, Any] = data


def load_eval_metadata(eval_name: str) -> EvalMetadata:
    """Load metadata for a single eval by name.

    Looks for ``<package_dir>/<eval_name>/eval.yaml``.
    """
    package_dir = Path(__file__).resolve().parent
    yaml_path = package_dir / eval_name / "eval.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"No eval.yaml found for '{eval_name}': {yaml_path}"
        )
    with open(yaml_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return EvalMetadata(data)
