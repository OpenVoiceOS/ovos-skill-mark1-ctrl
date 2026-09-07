"""Golden-utterance end-to-end coverage for ovos-skill-mark1-ctrl (en-US).

The golden corpus (``golden_utterances.jsonl``) is a vendored slice of the
shared ovoscope golden-utterance dataset, keyed by
``skill_id == "ovos-skill-mark1-ctrl.openvoiceos"``. One shared
``MiniCroft`` (module-scoped fixture) is booted for the whole suite.

Two corpus-row edits (reported upstream, see below): the shared corpus
labels the two padatious intents ``custom.eye.color.intent`` /
``eye.color.intent`` (dot-separated), but this repo's actual intent files
are ``custom_eye_color.intent`` / ``eye_color.intent`` (underscore --
confirmed against the ``@intent_handler(...)`` decorators in
``__init__.py``). The vendored slice here corrects the ``intent_label``
field for those 9 rows to match the real filenames; the same correction
should be applied to the master corpus.

The skill's ``__init__`` refuses to load off a physical Mark 1 (I2C probe),
so ``ovos_i2c_detection.is_mark_1`` is stubbed True before the plugin loader
imports the skill module, same as ``test_intents_en_us.py``. The colour
handler follows up with a blocking ``get_response``/``ask_yesno`` prompt
that never resolves on a headless MiniCroft, so those are short-circuited
too.
"""
import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_skill_mark1_ctrl import EnclosureControlSkill  # noqa: E402

EnclosureControlSkill.ask_yesno = lambda self, *a, **k: "no"
EnclosureControlSkill.get_response = lambda self, *a, **k: None

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from ovos_bus_client.message import Message  # noqa: E402
from ovos_bus_client.session import Session  # noqa: E402
from ovoscope import CaptureSession, get_minicroft  # noqa: E402

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"
LANG = "en-US"

# Covers both adapt and padatious rows in one pipeline list -- exact
# expansions score conf 1.0 on padatious-high, adapt matches independently
# of pipeline ordering here since there's no cross-skill ambiguity in this
# corpus slice.
_PIPELINE = [
    "ovos-adapt-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-high",
    "ovos-padacioso-pipeline-plugin-high",
    "ovos-adapt-pipeline-plugin-medium",
    "ovos-padatious-pipeline-plugin-medium",
    "ovos-padacioso-pipeline-plugin-medium",
    "ovos-adapt-pipeline-plugin-low",
]

_IGNORE = [
    "speak",
    "ovos.utterance.speak",
    "mycroft.audio.play_sound",
    "enclosure.eyes.brightness",
    "enclosure.eyes.level",
    "enclosure.eyes.look",
    "enclosure.eyes.reset",
    "enclosure.eyes.blink",
    "enclosure.eyes.on",
    "enclosure.eyes.off",
    "enclosure.eyes.narrow",
    "enclosure.eyes.spin",
    "enclosure.eyes.color",
    "enclosure.eyes.timedspin",
    "enclosure.mouth.reset",
    "enclosure.mouth.text",
    "enclosure.mouth.smile",
    "enclosure.mouth.listen",
    "enclosure.mouth.think",
    "gui.value.set",
    "gui.page.show",
]

GOLDEN_PATH = Path(__file__).parent / "golden_utterances.jsonl"

# utterances lifted verbatim from OTHER skills' golden-utterance slices,
# picked for lexical overlap with mark1-ctrl's "look"/"eye"/"blink"/
# "smile"/"color"/"brightness" vocabulary.
NEGATIVE_UTTERANCES = [
    ("what's the weather", "ovos-skill-weather.openvoiceos"),
    ("play some music", "ovos-skill-music.openvoiceos"),
    ("turn up the brightness", "ovos-skill-homeassistant.openvoiceos"),
    ("turn off the living room lights", "ovos-skill-homeassistant.openvoiceos"),
    ("set a timer for 5 minutes", "ovos-skill-alerts.openvoiceos"),
    ("take a screenshot", "ovos-skill-screenshot.openvoiceos"),
    ("go to sleep", "ovos-skill-naptime.openvoiceos"),
]


def _candidates(skill_id: str, intent_label: str) -> set:
    """padatious/padacioso plugin versions register the matched-intent bus
    event under different normalizations of the ``.intent`` filename
    basename -- candidates cover both the suffixed and unsuffixed forms.
    Adapt intent names (eg. "EnclosureLookRight") have no ``.intent``
    suffix to strip."""
    base = intent_label[:-len(".intent")] if intent_label.endswith(".intent") else intent_label
    return {f"{skill_id}:{intent_label}", f"{skill_id}:{base}"}


def _load_golden_rows():
    rows = []
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


GOLDEN_ROWS = [pytest.param(r, id=r["utterance"]) for r in _load_golden_rows()]


@pytest.fixture(scope="module")
def minicroft():
    mc = get_minicroft([SKILL_ID])
    yield mc
    mc.stop()


def _types(mc, text, session_id):
    session = Session(session_id)
    session.lang = LANG
    session.pipeline = list(_PIPELINE)
    # blacklisted_intents defaults to None on a fresh Session, which crashes
    # the padacioso pipeline (NoneType membership test) - force an empty list.
    session.blacklisted_intents = []
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": LANG},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    # End capture right after the intent binding fires (handler start)
    # rather than at ovos.utterance.handled: the colour/animation handlers
    # can hang on a bare FakeBus/MiniCroft (see module docstring) even with
    # the ask_yesno/get_response stubs in place for defense in depth.
    capture = CaptureSession(
        mc,
        eof_msgs=["mycroft.skill.handler.start"],
        ignore_messages=_IGNORE,
    )
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


def _golden_id(row):
    return row["utterance"]


@pytest.mark.timeout(60)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=_golden_id)
def test_golden_utterance(minicroft, row):
    candidates = _candidates(SKILL_ID, row["intent_label"])
    types = _types(minicroft, row["utterance"], f"golden-{_golden_id(row)}")
    assert any(t in candidates for t in types), (
        f"{row['utterance']!r}: expected one of {sorted(candidates)!r}, got {types!r}"
    )


@pytest.mark.timeout(60)
@pytest.mark.parametrize("negative", NEGATIVE_UTTERANCES, ids=lambda n: n[0])
def test_negative_confusable_not_claimed(minicroft, negative):
    text, source_skill = negative
    types = _types(minicroft, text, f"negative-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"{text!r} (from {source_skill}) was incorrectly claimed by {SKILL_ID}"
