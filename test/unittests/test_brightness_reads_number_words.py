"""A brightness said in words sets the eyes, in every locale.

The handler reads the `brightness` slot. 50 % is level 15 of the 30 levels
of the Mark 1 eyes.
"""
import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_skill_mark1_ctrl import EnclosureControlSkill

from unittest.mock import Mock, patch

import pytest
from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"


@pytest.fixture(scope="module")
def skill():
    skill = EnclosureControlSkill()
    skill._startup(FakeBus(), SKILL_ID)
    yield skill
    skill.default_shutdown()


def eye_levels(skill, brightness, lang):
    skill._enclosure = Mock()
    with patch.object(type(skill), "lang", property(lambda s: lang)), \
            patch.object(skill, "speak_dialog"):
        skill.handle_brightness(Message("test", {"brightness": brightness}, {"lang": lang}))
    return [c.args[0] for c in skill._enclosure.eyes_brightness.call_args_list]


@pytest.mark.parametrize("lang, brightness, level", [
    ("en-US", "fifty", 15),
    ("en-US", "seventy five", 22),
    ("pt-PT", "cinquenta", 15),
    ("pt-PT", "setenta e cinco", 22),
    ("pt-BR", "cinquenta", 15),
    ("ca-ES", "cinquanta", 15),
    ("da-DK", "halvtreds", 15),
    ("de-DE", "fünfzig", 15),
    ("el-GR", "πενήντα", 15),
    ("es-ES", "cincuenta", 15),
    ("es-CO", "cincuenta", 15),
    ("eu-ES", "berrogeita hamar", 15),
    ("fa-IR", "پنجاه", 15),
    ("fr-FR", "cinquante", 15),
    ("gl-ES", "cincuenta", 15),
    ("it-IT", "cinquanta", 15),
    ("nl-NL", "vijftig", 15),
    ("pl-PL", "pięćdziesiąt", 15),
    ("ru-RU", "пятьдесят", 15),
    ("sv-SE", "femtio", 15),
])
def test_a_number_word_sets_the_eye_brightness(skill, lang, brightness, level):
    assert eye_levels(skill, brightness, lang) == [level]


def test_a_plain_level_below_thirty_is_a_level(skill):
    # "twenty" is level 20 of 30: 66 %, which the hardware gets as level 19
    assert eye_levels(skill, "twenty", "en-US") == [19]
