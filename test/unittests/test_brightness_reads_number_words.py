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


# A percent word of the locale makes the number a percentage, also below
# 30, where a bare number is a level. 10 % is level 3, and 20 % is level 6.
@pytest.mark.parametrize("lang, brightness, level", [
    ("en-US", "ten per cent", 3),
    ("ca-ES", "deu per cent", 3), ("ca-ES", "20 per cent", 6),
    ("da-DK", "ti procent", 3), ("da-DK", "20 procent", 6),
    ("de-DE", "zehn Prozent", 3), ("de-DE", "20 Prozent", 6),
    ("el-GR", "δέκα τοις εκατό", 3), ("el-GR", "20 τοις εκατό", 6),
    ("es-CO", "diez por ciento", 3), ("es-CO", "20 por ciento", 6),
    ("es-ES", "diez por ciento", 3), ("es-ES", "20 por ciento", 6),
    ("eu-ES", "hamar ehuneko", 3), ("eu-ES", "ehuneko 20", 6),
    ("fa-IR", "ده درصد", 3), ("fa-IR", "20 درصد", 6),
    ("fr-FR", "dix pour cent", 3), ("fr-FR", "20 pour cent", 6),
    ("gl-ES", "dez por cento", 3), ("gl-ES", "20 por cento", 6),
    ("it-IT", "dieci per cento", 3), ("it-IT", "20 per cento", 6),
    ("kab", "20 n umeya", 6),
    ("nl-NL", "tien procent", 3), ("nl-NL", "20 procent", 6),
    ("oc-FR", "dètz per cent", 3), ("oc-FR", "20 per cent", 6),
    ("pl-PL", "dziesięć proc.", 3), ("pl-PL", "20 proc.", 6),
    ("pt-BR", "dez por cento", 3), ("pt-BR", "20 por cento", 6),
    ("pt-PT", "dez por cento", 3), ("pt-PT", "20 por cento", 6),
    ("ru-RU", "десять процентов", 3), ("ru-RU", "20 процентов", 6),
    ("sv-SE", "tio procent", 3), ("sv-SE", "20 procent", 6),
])
def test_a_percent_word_of_the_locale_makes_a_percentage(skill, lang, brightness, level):
    assert eye_levels(skill, brightness, lang) == [level]


@pytest.mark.parametrize("lang, brightness", [
    ("en-US", "half"),
    ("pt-PT", "meio"),
    ("de-DE", "halb"),
])
def test_a_fraction_is_no_brightness_level(skill, lang, brightness):
    skill._enclosure = Mock()
    with patch.object(type(skill), "lang", property(lambda s: lang)), \
            patch.object(skill, "speak_dialog") as speak_dialog:
        skill.handle_brightness(Message("test", {"brightness": brightness}, {"lang": lang}))
    assert not skill._enclosure.eyes_brightness.called
    assert [c.args[0] for c in speak_dialog.call_args_list] == ["brightness_not_found_final"]


# "um pouco" and "un poco" mean "a little": the article is no brightness level.
@pytest.mark.parametrize("lang, brightness", [
    ("pt-PT", "um pouco"),
    ("es-ES", "un poco"),
])
def test_an_article_is_no_brightness_level(skill, lang, brightness):
    skill._enclosure = Mock()
    with patch.object(type(skill), "lang", property(lambda s: lang)), \
            patch.object(skill, "speak_dialog") as speak_dialog:
        skill.handle_brightness(Message("test", {"brightness": brightness}, {"lang": lang}))
    assert not skill._enclosure.eyes_brightness.called
    assert [c.args[0] for c in speak_dialog.call_args_list] == ["brightness_not_found_final"]


# Spoken forms of the percent word: Polish declines "procent" after a
# numeral, Greek also says "τα εκατό", French also writes "pourcent", and
# Galician also writes "porcento".
@pytest.mark.parametrize("lang, brightness, level", [
    ("pl-PL", "dziesięć procentów", 3),
    ("pl-PL", "dwadzieścia dwa procenty", 6),
    ("el-GR", "είκοσι τα εκατό", 6),
    ("fr-FR", "dix pourcent", 3),
    ("gl-ES", "vinte porcento", 6),
    ("gl-ES", "20 porcento", 6),
])
def test_a_declined_percent_word_makes_a_percentage(skill, lang, brightness, level):
    assert eye_levels(skill, brightness, lang) == [level]


# Level 1 and 1 % are both level 0 on the eyes, so read the percentage.
def test_one_percent_in_the_genitive_is_one_percent(skill):
    with patch.object(type(skill), "lang", property(lambda s: "pl-PL")):
        assert skill.parse_brightness("jeden procenta") == 1


# A percentage above 100 is out of range, as a plain number above 100 is.
@pytest.mark.parametrize("lang, brightness", [
    ("en-US", "200 percent"), ("de-DE", "200 Prozent"), ("pt-PT", "150 %"),
])
def test_a_percentage_above_100_is_no_brightness(skill, lang, brightness):
    skill._enclosure = Mock()
    with patch.object(type(skill), "lang", property(lambda s: lang)), \
            patch.object(skill, "speak_dialog") as speak_dialog:
        skill.handle_brightness(Message("test", {"brightness": brightness}, {"lang": lang}))
    assert not skill._enclosure.eyes_brightness.called
    assert [c.args[0] for c in speak_dialog.call_args_list] == ["brightness_not_found_final"]
