"""A translated direction must steer the eyes, not only match the intent.

`handle_blink_eyes` compared the `{direction}` slot with the English words
"left" and "right". The slot arrives in the session language, so a German
"rechts" fell through to the `else` and blinked BOTH eyes: the intent
matched, the skill answered, and the answer ignored the direction.

The sibling file `test_direction_is_resolved_per_locale.py` reads the
resources and proves every `direction.entity` value is carried by one of
the two vocabularies. That is a check on the files. This file drives the
handler itself and reads back the letter the enclosure was asked to blink,
because a resource can be right while the caller never reaches it.
"""
import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_skill_mark1_ctrl import EnclosureControlSkill

import unittest
from unittest.mock import Mock

from ovos_bus_client.apis.enclosure import EnclosureAPI
from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"


class TestBlinkDirectionReachesTheEnclosure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skill = EnclosureControlSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def _blinked(self, direction, lang):
        """The distinct letters the enclosure was asked to blink."""
        self.skill._enclosure = Mock(spec=EnclosureAPI)
        data = {"lang": lang}
        if direction is not None:
            data["direction"] = direction
        self.skill.handle_blink_eyes(Message("test", data, {"lang": lang}))
        return {call.args[0] for call in self.skill.enclosure.eyes_blink.call_args_list}

    def test_the_english_control(self):
        # The locale that worked before this change, so a failure here says
        # the change broke what already worked rather than that the German
        # case is unsupported.
        self.assertEqual(self._blinked("right", "en-US"), {"r"})
        self.assertEqual(self._blinked("left", "en-US"), {"l"})

    def test_a_german_direction_blinks_the_same_eye(self):
        self.assertEqual(self._blinked("rechts", "de-DE"), {"r"})
        self.assertEqual(self._blinked("links", "de-DE"), {"l"})

    def test_the_two_locales_that_gained_the_template(self):
        # el-GR and ru-RU shipped direction.entity, left.voc and right.voc
        # and no blink.intent template that placed the slot, so the slot
        # never arrived. The template is in place now, and the handler must
        # read the Greek and the Russian word the same way.
        self.assertEqual(self._blinked("δεξιά", "el-GR"), {"r"})
        self.assertEqual(self._blinked("αριστερά", "el-GR"), {"l"})
        self.assertEqual(self._blinked("направо", "ru-RU"), {"r"})
        self.assertEqual(self._blinked("налево", "ru-RU"), {"l"})

    def test_the_locale_selects_the_vocabulary(self):
        # The control for the case above. "rechts" is carried by de-DE's
        # right.voc and by no en-US file, so under en-US the handler must
        # fall through to both eyes. Without this, a German word blinking
        # the right eye would also be explained by a search that reads
        # every locale rather than the session language.
        self.assertEqual(self._blinked("rechts", "en-US"), {"b"})

    def test_no_direction_blinks_both_eyes(self):
        self.assertEqual(self._blinked(None, "en-US"), {"b"})

    def test_a_word_neither_vocabulary_carries_blinks_both_eyes(self):
        # The handler must not guess. "purple" is in no direction file.
        self.assertEqual(self._blinked("purple", "en-US"), {"b"})

    def test_the_handler_asks_for_ten_blinks(self):
        self.skill._enclosure = Mock(spec=EnclosureAPI)
        self.skill.handle_blink_eyes(
            Message("test", {"direction": "rechts", "lang": "de-DE"},
                    {"lang": "de-DE"}))
        self.assertEqual(self.skill.enclosure.eyes_blink.call_count, 10)
