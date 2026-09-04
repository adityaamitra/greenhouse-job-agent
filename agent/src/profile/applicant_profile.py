from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


class ApplicantProfileError(ValueError):
    """Raised when the local applicant profile is invalid."""


def _get_nested(
    data: dict,
    path: tuple[str, ...],
) -> Any:
    current: Any = data

    for key in path:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


@dataclass(frozen=True)
class ApplicantProfile:
    """
    Local source of truth for deterministic applicant facts.

    This object intentionally contains no company-specific
    application answers such as "Why us?" or salary expectations.
    """

    data: dict
    source_path: Path

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> "ApplicantProfile":
        source = Path(path)

        if not source.exists():
            raise ApplicantProfileError(
                f"Applicant profile not found: {source}"
            )

        try:
            raw = json.loads(
                source.read_text(
                    encoding="utf-8",
                )
            )
        except json.JSONDecodeError as exc:
            raise ApplicantProfileError(
                f"Invalid JSON in applicant profile: {exc}"
            ) from exc

        if not isinstance(raw, dict):
            raise ApplicantProfileError(
                "Applicant profile must be a JSON object."
            )

        version = raw.get(
            "profile_version"
        )

        if version != 1:
            raise ApplicantProfileError(
                "Unsupported applicant profile version. "
                "Expected profile_version = 1."
            )

        return cls(
            data=raw,
            source_path=source,
        )

    def get(
        self,
        *path: str,
    ) -> Any:
        return _get_nested(
            self.data,
            tuple(path),
        )

    def full_name(self) -> str | None:
        first = self.get(
            "identity",
            "first_name",
        )

        last = self.get(
            "identity",
            "last_name",
        )

        if not first or not last:
            return None

        return (
            f"{first} {last}"
            .strip()
        )
