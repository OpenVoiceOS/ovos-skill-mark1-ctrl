"""End-to-end intent-routing tests for ovos-skill-mark1-ctrl (en-US).

Each case boots an in-process MiniCroft with the skill loaded and feeds a real
utterance through it, asserting where it routes and how the ``{color}`` /
``{brightness}`` slots are filled.

The skill's ``__init__`` refuses to load off a physical Mark 1 (I2C probe), so
``ovos_i2c_detection.is_mark_1`` is stubbed True before the plugin loader
imports the skill module.

Run: pytest test/end2end/ -v
"""
import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

# The skill's __init__ refuses to load off a physical Mark 1; import it only
# after is_mark_1 is stubbed. The colour handler follows up with a blocking
# get_response/ask_yesno prompt that never resolves in a headless MiniCroft, so
# short-circuit those to keep the routed handler from hanging the test.
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


class _RoutingTest(TestCase):
    """Shared MiniCroft harness for intent routing."""

    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_prototype_minicroft([SKILL_ID], lang=LANG)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "minicroft", None):
            cls.minicroft.stop()

    def _run(self, utterance, intent_name):
        """Emit ``utterance``, record its routing, and return the data of
        the ``intent_name`` message."""
        topic = f"{SKILL_ID}:{intent_name}"
        session = Session(f"e2e-en_us-{abs(hash(utterance))}")
        session.lang = LANG
        session.pipeline = PIPELINE
        capture = CaptureSession(self.minicroft)
        capture.capture(Message(
            "recognizer_loop:utterance",
            {"utterances": [utterance], "lang": LANG},
            {"session": session.serialize()},
        ), timeout=15)
        messages = capture.finish()
        TALLY.assert_routed(utterance, topic, [m.msg_type for m in messages])
        return [m.data for m in messages if m.msg_type == topic]


class TestIntentRouting(_RoutingTest):
    """Routing for the eye-colour and brightness intents."""

    def test_set_the_eye_color_to_red(self):
        routed = self._run("set the eye color to red", "eye_color")
        self.assertEqual(routed[0].get("color"), "red")

    def test_set_eye_brightness_to_50(self):
        routed = self._run("set eye brightness to 50", "brightness")
        self.assertEqual(routed[0].get("brightness"), "50")
