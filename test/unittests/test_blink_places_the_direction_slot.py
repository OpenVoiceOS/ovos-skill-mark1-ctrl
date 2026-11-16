"""An entity no intent places is never matched.

`direction.entity` and the `left.voc`/`right.voc` pair ship in every locale,
and `handle_blink_eyes` resolves the slot against the pair. None of that
reaches a user until the locale's own `blink.intent` places `{direction}` in
at least one template: Padatious fills a slot only for the templates that
name it. el-GR and ru-RU shipped the three resources and no template that
placed the slot, so one-eye blinking was impossible in those two languages
while every file-level parity check read clean.

The sibling files cover the other two halves: `test_resources.py` checks the
files exist, and `test_blink_direction_reaches_the_enclosure.py` drives the
handler. This file checks the one link between them.
"""
from pathlib import Path

LOCALES = Path(__file__).resolve().parents[2] / "locale"
SLOT = "{direction}"


def places_the_slot(blink: Path) -> bool:
    """True when at least one template in the file names the slot."""
    return any(SLOT in line for line in
               blink.read_text(encoding="utf-8").splitlines())


def test_every_locale_that_ships_the_entity_places_the_slot():
    missing = []
    checked = []
    for locale in sorted(LOCALES.iterdir()):
        if not (locale / "direction.entity").is_file():
            continue
        blink = locale / "blink.intent"
        assert blink.is_file(), f"{locale.name} ships direction.entity, no blink.intent"
        checked.append(locale.name)
        if not places_the_slot(blink):
            missing.append(locale.name)
    assert checked, f"no locale under {LOCALES} ships direction.entity"
    assert not missing, (
        "these locales ship direction.entity, left.voc and right.voc, and no "
        "blink.intent template places {direction}, so a user of that language "
        "cannot blink one eye:\n  " + "\n  ".join(missing))


def test_the_check_reports_a_file_that_does_not_place_the_slot(tmp_path):
    # The control for the test above. Without it, a reader cannot tell a
    # clean sweep from a helper that answers True for every input.
    with_slot = tmp_path / "with.intent"
    with_slot.write_text("blink [{direction}] [<eyes>]\n", encoding="utf-8")
    without = tmp_path / "without.intent"
    without.write_text("blink [<eyes>]\nblink your <eyes>\n", encoding="utf-8")
    assert places_the_slot(with_slot)
    assert not places_the_slot(without)
