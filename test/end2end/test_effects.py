"""Effect assertions for ovos-skill-mark1-ctrl's eye-color and brightness intents.

``test_intents_en_us.py``, ``test_golden_utterances.py`` and
``test_entity_constraints.py`` all assert routing only: the golden suite's
``_IGNORE`` list explicitly drops every ``enclosure.eyes.*`` message before
asserting, and the routing test asserts only the routed intent's slot data,
never the enclosure command the handler is supposed to send. A handler that
routes, fills the slot correctly, and then never talks to the enclosure
passes all three suites unchanged.

This asserts the specific enclosure bus message and its payload for both
intents, with the expected RGB/level values computed independently (via
``ovos_color_parser.color_from_description`` and the skill's own documented
percent-to-level formula), never read back from the handler under test.
"""
import unittest

import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_color_parser import color_from_description  # noqa: E402
from ovos_skill_mark1_ctrl import EnclosureControlSkill  # noqa: E402

EnclosureControlSkill.ask_yesno = lambda self, *a, **k: "no"
EnclosureControlSkill.get_response = lambda self, *a, **k: None

from ovos_bus_client.message import Message  # noqa: E402
from ovos_bus_client.session import Session  # noqa: E402
from ovoscope import CaptureSession, get_minicroft  # noqa: E402

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"
LANG = "en-US"

_PIPELINE = [
    "ovos-padatious-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-medium",
]


class TestMark1CtrlEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        cls.minicroft.stop()

    def _session(self, session_id):
        session = Session(session_id)
        session.lang = LANG
        session.pipeline = list(_PIPELINE)
        return session

    def _fire(self, text, session_id):
        session = self._session(session_id)
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        capture = CaptureSession(self.minicroft, ignore_messages=[])
        capture.capture(utterance, timeout=30)
        return capture.finish()

    def test_set_eye_color_emits_enclosure_color_command(self):
        """The real effect of 'set the eye color to red' is telling the
        Mark 1 enclosure to change its eye colour -- assert the
        enclosure.eyes.color message and its r/g/b payload, matching the
        RGB triple 'red' independently resolves to via
        ovos_color_parser, not whatever the handler happened to emit."""
        expected = color_from_description("red")
        messages = self._fire("set the eye color to red", "effects-eye-color")

        color_msgs = [m for m in messages if m.msg_type == "enclosure.eyes.color"]
        self.assertEqual(
            len(color_msgs), 1,
            f"expected exactly one enclosure.eyes.color message, got {[m.msg_type for m in messages]!r}",
        )
        self.assertEqual(
            (color_msgs[0].data.get("r"), color_msgs[0].data.get("g"), color_msgs[0].data.get("b")),
            (expected.r, expected.g, expected.b),
            "enclosure.eyes.color payload did not carry the RGB triple for 'red'",
        )

    def test_set_eye_brightness_emits_enclosure_level_command(self):
        """The real effect of 'set eye brightness to 50' is telling the
        enclosure to change its brightness LEVEL (0-30 scale), not the
        50% the user said -- the skill's own percent_to_level formula
        (level = percent / 100 * 30) computes 15 for 50%, matching what
        real Mark 1 hardware expects."""
        messages = self._fire("set eye brightness to 50", "effects-brightness")

        level_msgs = [m for m in messages if m.msg_type == "enclosure.eyes.level"]
        self.assertEqual(
            len(level_msgs), 1,
            f"expected exactly one enclosure.eyes.level message, got {[m.msg_type for m in messages]!r}",
        )
        self.assertEqual(
            level_msgs[0].data.get("level"), 15,
            "enclosure.eyes.level payload did not carry the converted 0-30 level for 50%",
        )


if __name__ == "__main__":
    unittest.main()
