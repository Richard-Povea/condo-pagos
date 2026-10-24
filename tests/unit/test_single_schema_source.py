"""Ensure the repository has a single authoritative SQL schema directory."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_sql_schema_files_live_only_under_db() -> None:
    """Fail if a second schema/seed SQL file is added outside db/."""
    unexpected = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.sql")
        if "db" not in path.relative_to(ROOT).parts
        and not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
    )

    assert not unexpected, (
        "SQL files must live under db/; db/01-schema.sql is the sole schema source. "
        f"Found: {unexpected}"
    )
