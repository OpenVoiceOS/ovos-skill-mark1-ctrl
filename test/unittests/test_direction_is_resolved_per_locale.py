"""A translated direction must still steer the eyes.

`handle_blink_eyes` used to compare the `{direction}` slot with the English
words "left" and "right". Every locale that carries a translated
`direction.entity` therefore filled the slot correctly and blinked BOTH eyes:
the intent matched, the skill answered, and the answer ignored the direction.

The slot arrives in the session language, so it is resolved against the
locale's own `left.voc` and `right.voc`.
"""
from pathlib import Path

LOCALES = Path(__file__).resolve().parents[2] / "locale"


def words(locale: Path, name: str) -> set:
    """The vocabulary's words, folded the way `voc_match` compares them."""
    p = locale / f"{name}.voc"
    if not p.is_file():
        return set()
    return {l.strip().lower() for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()}


def test_every_direction_value_is_carried_by_one_of_the_two_vocabularies():
    unresolvable = []
    for locale in sorted(LOCALES.iterdir()):
        entity = locale / "direction.entity"
        if not entity.is_file():
            continue
        left, right = words(locale, "left"), words(locale, "right")
        for value in [l.strip() for l in
                      entity.read_text(encoding="utf-8").splitlines() if l.strip()]:
            if value.lower() not in left and value.lower() not in right:
                unresolvable.append(f"{locale.name}: {value!r}")
    assert not unresolvable, (
        "these direction values match neither left.voc nor right.voc, so the "
        "handler blinks both eyes whichever the user asked for:\n  "
        + "\n  ".join(unresolvable))


def test_the_two_vocabularies_never_claim_the_same_word():
    both = []
    for locale in sorted(LOCALES.iterdir()):
        shared = words(locale, "left") & words(locale, "right")
        if shared:
            both.append(f"{locale.name}: {sorted(shared)}")
    assert not both, "a word cannot mean both directions:\n  " + "\n  ".join(both)
