"""End-to-end intent routing tests for the en-US locale.

The Mark 1 enclosure skill is hardware-bound: its handlers drive the faceplate
via the enclosure bus API. Each canonical utterance is fired through a real
MiniCroft and asserted to route to the expected ADAPT intent handler. No live
hardware is required -- the enclosure messages are emitted onto the bus and the
assertions cover the intent binding only.
"""
import unittest

import ovos_i2c_detection
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"
LANG = "en-US"


class TestMark1IntentsEnUS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The skill refuses to load unless it detects Mark 1 hardware; force the
        # detection so intent routing can be exercised on a headless runner.
        cls._real_is_mark_1 = ovos_i2c_detection.is_mark_1
        ovos_i2c_detection.is_mark_1 = lambda: True
        cls.minicroft = get_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        cls.minicroft.stop()
        ovos_i2c_detection.is_mark_1 = cls._real_is_mark_1

    def _run(self, text):
        session = Session("test-session")
        session.lang = LANG
        session.pipeline = [
            "ovos-adapt-pipeline-plugin-high",
            "ovos-adapt-pipeline-plugin-medium",
            "ovos-adapt-pipeline-plugin-low",
        ]
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        capture = CaptureSession(self.minicroft)
        capture.capture(utterance, timeout=30)
        return capture.finish()

    def _assert_intent(self, text, intent_label):
        messages = self._run(text)
        types = [m.msg_type for m in messages]
        self.assertIn(f"{SKILL_ID}:{intent_label}", types)

    def test_look_right(self):
        self._assert_intent("look right", "EnclosureLookRight")

    def test_look_right_enclosure(self):
        self._assert_intent("look right enclosure", "EnclosureLookRight")

    def test_look_left(self):
        self._assert_intent("look left", "EnclosureLookLeft")

    def test_spin_eyes(self):
        self._assert_intent("spin eyes", "EnclosureEyesSpin")

    def test_narrow_eyes(self):
        self._assert_intent("narrow eyes", "EnclosureEyesNarrow")
