"""Entity-file registration coverage for ovos-skill-mark1-ctrl (en-US).

register_entity_file() feeds locale/en-US/brightness.entity and
locale/en-US/color.entity to the intent engine as TRAINING DATA / hints for
the {brightness}/{color} slots -- NOT an allow-list. On the padacioso
pipeline:
  - an IN-LIST value (e.g. "turquoise") routes with the slot tagged.
  - an OUT-OF-LIST value for the same slot (e.g. "mauve") still routes with
    the slot tagged, because registration is a hint, not a closed
    vocabulary.

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

PIPELINE = ["ovos-padacioso-pipeline-plugin"]


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

    def test_color_in_list_routes_with_the_slot(self):
        """A registered color ("turquoise") routes with the slot filled."""
        matched = self._emit_and_wait("set the eye color to turquoise",
                                      f"{SKILL_ID}:eye_color", PIPELINE)
        self.assertTrue(matched, "'set the eye color to turquoise' should route to eye_color "
                                 "-- turquoise is a registered color.entity value")
        self.assertEqual(matched[0].data.get("color"), "turquoise")

    def test_color_out_of_list_still_routes(self):
        """An unregistered color ("mauve") still routes with the slot filled:
        the entity file is a hint, not an allow-list."""
        matched = self._emit_and_wait("set the eye color to mauve",
                                      f"{SKILL_ID}:eye_color", PIPELINE)
        self.assertTrue(matched, "'set the eye color to mauve' (out-of-list color) should still "
                                 "route -- an out-of-list slot value must remain matchable")
        self.assertEqual(matched[0].data.get("color"), "mauve")

    # --- {brightness} on brightness.intent ---

    def test_brightness_in_list_routes_with_the_slot(self):
        """A registered brightness ("full") routes with the slot filled."""
        matched = self._emit_and_wait("set eye brightness to full",
                                      f"{SKILL_ID}:brightness", PIPELINE)
        self.assertTrue(matched, "'set eye brightness to full' should route to brightness "
                                 "-- full is a registered brightness.entity value")
        self.assertEqual(matched[0].data.get("brightness"), "full")
