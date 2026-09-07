"""Fast, offline unit tests for ovos-skill-mark1-ctrl resources.

These do not boot a MiniCroft; they validate that the en-US locale ships the
padatious eye/brightness intents and their slot entities. The heavy routing
lives in test/end2end/.
"""
from os.path import dirname, isfile, join
from unittest import TestCase

SKILL_ROOT = dirname(dirname(dirname(__file__)))
EN_US = join(SKILL_ROOT, "locale", "en-US")


def _read(name):
    path = join(EN_US, name)
    assert isfile(path), f"missing resource: {path}"
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestLocaleResources(TestCase):
    def test_intent_files_present(self):
        for name in ("eye_color.intent",
                     "custom_eye_color.intent",
                     "brightness.intent"):
            self.assertTrue(_read(name).strip(), f"{name} is empty")

    def test_eye_color_intent_uses_color_slot(self):
        self.assertIn("{color}", _read("eye_color.intent"))

    def test_brightness_intent_uses_brightness_slot(self):
        self.assertIn("{brightness}", _read("brightness.intent"))

    def test_color_entity_lists_named_colors(self):
        entity = _read("color.entity").lower()
        for color in ("red", "blue", "green"):
            self.assertIn(color, entity)
