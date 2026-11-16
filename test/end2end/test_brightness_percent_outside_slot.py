"""The intent engine can leave the percent word out of the brightness slot.

"dim the eye down to twenty percent" routes with the slot "twenty". Without
the percent word, 20 reads as level 20 of 30. The handler finds the percent
word in the utterance, so 20 % is level 6 of the 30 levels of the eyes.
"""
import ovos_i2c_detection
import pytest

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_skill_mark1_ctrl import EnclosureControlSkill

EnclosureControlSkill.ask_yesno = lambda self, *a, **k: "no"
EnclosureControlSkill.get_response = lambda self, *a, **k: None

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession
from ovoscope.routing import PIPELINE, get_prototype_minicroft

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"

# level = percent / 100 * 30, rounded down: 10 % is 3, 20 % is 6
CASES = [
    ("en-US", "dim the eye down to twenty percent", "twenty", 6),
    ("en-US", "change the eye brightness level to ten percent", "ten", 3),
    ("de-DE", "ein wenig heller auf zehn Prozent", "zehn", 3),
    ("de-DE", "ändere die Augen Helligkeit Stufe auf zwanzig Prozent", "zwanzig", 6),
    ("pt-PT", "mude para dez por cento o brilho dos olhos", "dez", 3),
    ("pt-PT", "mudar o nível de brilho do olho para vinte por cento", "vinte", 6),
    ("pt-BR", "mude para dez porcento o brilho dos olhos", "dez", 3),
    ("gl-ES", "cambia o brillo ata o dez por cento", "dez", 3),
    ("gl-ES", "escurecer ata o vinte por cento", "vinte", 6),
    ("es-ES", "bajar el brillo a un diez por ciento", "diez", 3),
    ("es-ES", "cambiar el nivel del brillo a un veinte por ciento", "veinte", 6),
    ("fr-FR", "change à dix pour cent la luminosité des yeux", "dix", 3),
    ("el-GR", "χαμήλωσε την φωτεινότητα στο είκοσι τοις εκατό", "είκοσι", 6),
]
_booted = {}


@pytest.fixture(scope="module")
def minicroft_for():
    def minicroft(lang):
        if lang not in _booted:
            for booted in _booted.values():
                booted.stop()
            _booted.clear()
            _booted[lang] = get_prototype_minicroft([SKILL_ID], lang=lang, max_wait=180)
        return _booted[lang]
    yield minicroft
    for booted in _booted.values():
        booted.stop()


@pytest.mark.parametrize("lang, utterance, slot, level", CASES)
def test_a_percent_word_outside_the_slot_makes_a_percentage(minicroft_for, lang, utterance,
                                                            slot, level):
    session = Session(f"percent-outside-slot-{lang}")
    session.lang = lang
    session.pipeline = PIPELINE
    capture = CaptureSession(minicroft_for(lang), ignore_messages=[])
    capture.capture(Message("recognizer_loop:utterance", {"utterances": [utterance], "lang": lang},
                            {"session": session.serialize()}), timeout=30)
    messages = capture.finish()

    routed = [m for m in messages if m.msg_type == f"{SKILL_ID}:brightness"]
    assert [m.data.get("brightness") for m in routed] == [slot]
    assert [m.data.get("level") for m in messages
            if m.msg_type == "enclosure.eyes.level"] == [level]
