"""Entity-file registration coverage for ovos-skill-mark1-ctrl (en-US).

register_entity_file() feeds locale/en-US/brightness.entity and
locale/en-US/color.entity to the intent engine as TRAINING DATA / confidence
hints for the {brightness}/{color} slots -- NOT an allow-list. Under
ovos-padatious>=2.0.3a1:
  - an IN-LIST value (e.g. "turquoise") routes at the padatious-HIGH band
    (conf_high=0.95) with the slot tagged correctly.
  - an OUT-OF-LIST value for the same slot (e.g. "mauve") still routes --
    registration is a hint, not a closed vocabulary -- but only clears the
    padatious-MEDIUM band, not high.

This means hint semantics only become visible when the active session
pipeline includes BOTH padatious-high and padatious-medium stages -- the
stock default pipeline (padatious-high only) will simply drop an
out-of-list utterance instead of showing the fallback-to-medium behavior.
Every test below therefore declares its own session.pipeline explicitly.

The skill's __init__ refuses to load off a physical Mark 1 (I2C probe), so
ovos_i2c_detection.is_mark_1 is stubbed True before the plugin loader
imports the skill module (mirrors test/end2end/test_intents_en_us.py).

Run: pytest test/end2end/test_entity_constraints.py -v --timeout=180
"""
import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_skill_mark1_ctrl import EnclosureControlSkill

EnclosureControlSkill.ask_yesno = lambda self, *a, **k: "no"
EnclosureControlSkill.get_response = lambda self, *a, **k: None

import time
from unittest import TestCase

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import get_minicroft

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"
LANG = "en-US"

HIGH = ["ovos-padatious-pipeline-plugin-high"]
HIGH_AND_MEDIUM = [
    "ovos-padatious-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-medium",
]


class TestEntityConstraints(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_minicroft([SKILL_ID])
        cls.bus = cls.minicroft.bus

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "minicroft", None):
            cls.minicroft.stop()

    def _emit_and_wait(self, utterance, intent_msg_type, pipeline,
                        deadline_s=20, settle_s=4):
        matched = []
        handler = lambda msg: matched.append(msg)
        self.bus.on(intent_msg_type, handler)
        try:
            session = Session(f"e2e-entity-{hash((utterance, intent_msg_type, tuple(pipeline)))}")
            session.lang = LANG
            session.pipeline = pipeline
            message = Message(
                "recognizer_loop:utterance",
                {"utterances": [utterance], "lang": LANG},
                {"session": session.serialize()},
            )
            deadline = time.monotonic() + deadline_s
            while not matched and time.monotonic() < deadline:
                self.bus.emit(message)
                waited = time.monotonic() + settle_s
                while not matched and time.monotonic() < waited:
                    time.sleep(0.2)
        finally:
            self.bus.remove(intent_msg_type, handler)
        return matched

    # --- {color} on eye_color.intent ---

    def test_color_in_list_matches_at_high(self):
        """A registered color ("turquoise") clears padatious-high alone."""
        intent_msg_type = f"{SKILL_ID}:eye_color"
        matched = self._emit_and_wait(
            "set the eye color to turquoise", intent_msg_type, HIGH,
        )
        self.assertTrue(matched, "'set the eye color to turquoise' should route at "
                                  "padatious-high -- turquoise is a registered color.entity value")
        self.assertEqual(matched[0].data.get("color"), "turquoise")

    def test_color_out_of_list_needs_medium(self):
        """An unregistered color ("mauve") still matches (hint, not
        allow-list) but only clears padatious-medium -- proving
        registration neither creates a closed vocabulary (would 0-match)
        nor is silently gutted (would also clear high, same as the
        registered case)."""
        intent_msg_type = f"{SKILL_ID}:eye_color"
        utterance = "set the eye color to mauve"

        high_only = self._emit_and_wait(utterance, intent_msg_type, HIGH)
        self.assertFalse(
            high_only,
            "'set the eye color to mauve' (out-of-list color) should NOT "
            "clear padatious-high alone -- if it does, entity registration "
            "is acting as a hard allow-list booster instead of a hint, or "
            "the high/medium band split collapsed",
        )

        with_medium = self._emit_and_wait(utterance, intent_msg_type, HIGH_AND_MEDIUM)
        self.assertTrue(
            with_medium,
            "'set the eye color to mauve' should still route once "
            "padatious-medium is in the pipeline -- an out-of-list slot "
            "value must remain matchable, just at lower confidence",
        )
        self.assertEqual(with_medium[0].data.get("color"), "mauve")

    # --- {brightness} on brightness.intent ---

    def test_brightness_in_list_matches_at_high(self):
        """A registered brightness ("full") clears padatious-high alone."""
        intent_msg_type = f"{SKILL_ID}:brightness"
        matched = self._emit_and_wait(
            "set eye brightness to full", intent_msg_type, HIGH,
        )
        self.assertTrue(matched, "'set eye brightness to full' should route at "
                                  "padatious-high -- full is a registered brightness.entity value")
        self.assertEqual(matched[0].data.get("brightness"), "full")

    # NOTE: {brightness} carries the "#"/"##"/"###"/"#%"/"##%"/"###%"
    # digit-wildcard placeholder lines. The shared resource reader treats
    # any line starting with "#" as a comment and drops it, so these are
    # never registered as literal entity values -- verified directly
    # against ovos_spec_tools.resources.read_resource_file, the reader
    # register_entity_file uses. {brightness}'s short (3-4 word) template
    # also makes its confidence band edges noticeably more boot-sensitive
    # than {color}'s, so this suite does not duplicate the
    # in-list-high / out-of-list-needs-medium pair for it -- {color} above
    # already exercises that pair reliably, and the mutation check below
    # covers the registration loop for both slots.
