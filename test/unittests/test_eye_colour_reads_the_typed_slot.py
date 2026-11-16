"""The eye colour comes from the typed slot when the transformer read one.

eye_color.intent declares ``{color:color}``. The typed-slots transformer puts
the colour it read, with its hex value, in ``data.typed_slots``
(OVOS-INTENT-1 §5.6). The handler sets the eyes from that hex. An engine that
binds no slot value, such as the m2v pipeline, leaves the slot empty and the
entries in place, and the handler reads the entries. Without a map the
handler looks the slot text up in the same name table, so it sets the same
colour.
"""
import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_skill_mark1_ctrl import EnclosureControlSkill

import unittest
from unittest.mock import Mock, patch

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovos_typed_slots_transformer import TypedSlotsTransformer
from ovos_utils.messagebus import FakeBus

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"
UTTERANCE = "set the eyes to dark blue"
DARK_BLUE = {"span": [16, 25], "surface": "dark blue",
             "value": {"hex": "#47576f", "name": "Dark Blue"}}


class TestEyeColourReadsTheTypedSlot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skill = EnclosureControlSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def _eyes(self, data):
        """The (r, g, b) the enclosure was set to, or None."""
        self.skill._enclosure = Mock()
        with patch.object(self.skill, "ask_yesno", return_value="no"), \
                patch.object(self.skill, "get_response", return_value=None), \
                patch.object(self.skill, "speak_dialog"):
            self.skill.handle_eye_color(Message(
                "test", {"utterance": UTTERANCE, "lang": "en-US", **data},
                {"lang": "en-US"}))
        call = self.skill._enclosure.eyes_color.call_args
        return tuple(call.args) if call else None

    def test_the_bound_slot_takes_the_typed_hex(self):
        self.assertEqual(self._eyes({"color": "dark blue",
                                     "typed_slots": {"color": [DARK_BLUE]}}),
                         (0x47, 0x57, 0x6f))

    def test_an_unbound_slot_takes_the_transformer_entry(self):
        self.assertEqual(self._eyes({"typed_slots": {"color": [DARK_BLUE]}}),
                         (0x47, 0x57, 0x6f))

    def test_without_a_map_the_slot_text_gives_the_typed_colour(self):
        typed = TypedSlotsTransformer().transform(
            [UTTERANCE], frozenset({"color"}), Session(lang="en-US"))
        hex_code = typed["color"][0]["value"]["hex"]
        rgb = tuple(int(hex_code[i:i + 2], 16) for i in (1, 3, 5))
        self.assertEqual(self._eyes({"color": "dark blue"}), rgb)

    def test_without_a_map_a_basic_colour_is_the_pure_colour(self):
        self.assertEqual(self._eyes({"color": "red"}), (255, 0, 0))
