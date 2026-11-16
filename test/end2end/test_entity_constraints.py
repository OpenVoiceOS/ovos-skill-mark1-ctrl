"""Entity-file registration coverage for ovos-skill-mark1-ctrl (en-US).

register_entity_file() feeds locale/en-US/brightness.entity and
locale/en-US/color.entity to the intent engine as TRAINING DATA / confidence
hints for the {brightness}/{color} slots -- NOT an allow-list:
  - an IN-LIST value (e.g. "turquoise") routes with the slot tagged
    correctly.
  - an OUT-OF-LIST value for the same slot (e.g. "mauve") still routes --
    registration is a hint, not a closed vocabulary.

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

from unittest import TestCase

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession
from ovoscope.routing import PIPELINE, TALLY, get_prototype_minicroft

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"
LANG = "en-US"


class TestEntityConstraints(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_prototype_minicroft([SKILL_ID], lang=LANG)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "minicroft", None):
            cls.minicroft.stop()

    def _routed_data(self, utterance, intent_msg_type):
        """Emit ``utterance``, record its routing, and return the data of
        the ``intent_msg_type`` message."""
        session = Session(f"e2e-entity-{abs(hash((utterance, intent_msg_type)))}")
        session.lang = LANG
        session.pipeline = PIPELINE
        capture = CaptureSession(self.minicroft)
        capture.capture(Message(
            "recognizer_loop:utterance",
            {"utterances": [utterance], "lang": LANG},
            {"session": session.serialize()},
        ), timeout=20)
        messages = capture.finish()
        TALLY.assert_routed(utterance, intent_msg_type, [m.msg_type for m in messages])
        return next(m.data for m in messages if m.msg_type == intent_msg_type)

    # --- {color} on eye_color.intent ---

    def test_color_in_list_matches(self):
        """A registered color ("turquoise") routes with the slot tagged."""
        data = self._routed_data("set the eye color to turquoise", f"{SKILL_ID}:eye_color")
        self.assertEqual(data.get("color"), "turquoise")

    def test_color_out_of_list_still_matches(self):
        """An unregistered color ("mauve") still matches: registration is a
        hint, not a closed vocabulary."""
        data = self._routed_data("set the eye color to mauve", f"{SKILL_ID}:eye_color")
        self.assertEqual(data.get("color"), "mauve")

    # --- {brightness} on brightness.intent ---

    def test_brightness_in_list_matches(self):
        """A registered brightness ("full") routes with the slot tagged."""
        data = self._routed_data("set eye brightness to full", f"{SKILL_ID}:brightness")
        self.assertEqual(data.get("brightness"), "full")

    # NOTE: {brightness} carries the "#"/"##"/"###"/"#%"/"##%"/"###%"
    # digit-wildcard placeholder lines. The shared resource reader treats
    # any line starting with "#" as a comment and drops it, so these are
    # never registered as literal entity values -- verified directly
    # against ovos_spec_tools.resources.read_resource_file, the reader
    # register_entity_file uses. {color} above exercises the
    # in-list / out-of-list pair, so this suite does not duplicate it for
    # {brightness}.
