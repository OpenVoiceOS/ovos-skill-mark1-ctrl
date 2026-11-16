"""Locale resources use the seven OVOS-INTENT-2 roles; `.value` and `.list` are not among them."""
from pathlib import Path
from unittest import TestCase

LOCALE = Path(__file__).resolve().parents[2] / "locale"


class TestNoDeprecatedResourceFiles(TestCase):
    def test_no_value_or_list_files_ship(self):
        shipped = sorted(
            str(p.relative_to(LOCALE))
            for p in LOCALE.rglob("*")
            if p.is_file() and p.suffix in (".value", ".list")
        )
        self.assertEqual(shipped, [])
