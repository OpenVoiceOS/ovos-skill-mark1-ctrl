"""A colour said in the session language must resolve.

`handle_eye_color` called `color_from_description(color_str)`. The parser's
signature is `color_from_description(description, lang="en", ...)`, so every
locale's colour was read as English: the intent matched, the parser answered
`None`, and the skill spoke `color_not_exist`. That is the defect the
`{direction}` slot lost in this same branch, one function away.

This file drives the handler and reads back the colour the eyes were set
to, because a call site is what the user meets.
"""
import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_skill_mark1_ctrl import EnclosureControlSkill

import unittest
from unittest.mock import Mock, patch

from ovos_bus_client.message import Message
from ovos_color_parser import color_from_description
from ovos_utils.messagebus import FakeBus

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"


class TestEyeColourReadsTheSessionLanguage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skill = EnclosureControlSkill()
        cls.skill._startup(FakeBus(), SKILL_ID)

    def _set_colour(self, colour, lang):
        """The colour handed to set_eye_color, or None when none was."""
        self.skill._enclosure = Mock()
        with patch.object(type(self.skill), "lang", property(lambda s: lang)), \
                patch.object(self.skill, "ask_yesno", return_value="no"), \
                patch.object(self.skill, "set_eye_color") as set_eye_color, \
                patch.object(self.skill, "speak_dialog") as speak_dialog:
            self.skill.handle_eye_color(
                Message("test", {"color": colour, "lang": lang}, {"lang": lang}))
        if set_eye_color.called:
            return set_eye_color.call_args.kwargs["color"]
        self.assertTrue(
            speak_dialog.called,
            "the handler neither set a colour nor spoke: it answered nothing")
        return None

    def test_the_english_control(self):
        # The locale that worked before this change.
        self.assertIsNotNone(self._set_colour("blue", "en-US"))

    def test_a_colour_in_the_session_language_resolves(self):
        for lang, word in (("de-DE", "blau"), ("da-DK", "blå"),
                           ("nl-NL", "blauw"), ("sv-SE", "blå")):
            with self.subTest(lang=lang, word=word):
                self.assertIsNotNone(
                    self._set_colour(word, lang),
                    "%r in %s resolved to nothing, so the skill speaks "
                    "color_not_exist on an intent it matched" % (word, lang))

    def test_the_parser_really_needs_the_language(self):
        # The control for the case above. Read against the library itself:
        # if these resolved without a lang, the test would pass whether or
        # not the call site passes one.
        for word in ("blau", "blå", "blauw"):
            with self.subTest(word=word):
                self.assertIsNone(color_from_description(word))

    def test_a_word_that_is_no_colour_speaks_instead_of_setting(self):
        self.assertIsNone(self._set_colour("dishwasher", "en-US"))
