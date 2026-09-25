"""Coverage that the {brightness}/{color} slots reach the padatious matcher
as registered entities, sourced from locale/*/*.entity.

ovos-workshop>=9.5.0a1 registers every ".entity" file shipped in a skill's
locale resources AUTOMATICALLY (see `OVOSSkill._auto_register_entity_files`)
the first time a language's resources are loaded, during `_startup()` -
there is no more skill-authored `register_entity_file()` call to test.

This test boots the skill with NO manual registration call and listens on
the bus for the `padatious:register_entity` messages workshop's auto
registration emits, asserting the sample values shipped in
locale/en-US/brightness.entity and locale/en-US/color.entity landed on the
bus for the {brightness}/{color} entities respectively.

Mutation check: delete (or rename) locale/en-US/brightness.entity or
color.entity and this test goes red - there is nothing left in the skill to
register it, since the wiring is now entirely workshop's auto-discovery
walking the on-disk locale/ directory.

The skill's __init__ refuses to load off a physical Mark 1 (I2C probe), so
ovos_i2c_detection.is_mark_1 is stubbed True before the plugin loader
imports the skill module (mirrors test/end2end/test_intents_en_us.py).
"""
import ovos_i2c_detection

ovos_i2c_detection.is_mark_1 = lambda: True

from ovos_skill_mark1_ctrl import EnclosureControlSkill

import unittest

from ovos_utils.messagebus import FakeBus


class TestEntityRegistration(unittest.TestCase):

    def test_boot_auto_registers_entity_files_no_manual_call(self):
        bus = FakeBus()
        registered = []
        bus.on("padatious:register_entity", registered.append)

        skill = EnclosureControlSkill()
        skill._startup(bus, "ovos-skill-mark1-ctrl.openvoiceos")

        by_name = {msg.data.get("name"): msg.data for msg in registered}
        skill_id = "ovos-skill-mark1-ctrl.openvoiceos"

        color_name = f"{skill_id}:color"
        brightness_name = f"{skill_id}:brightness"

        self.assertIn(
            color_name, by_name,
            "booting the skill with no manual register_entity_file() call "
            "should still auto-register {color} from locale/en-US/color.entity "
            "(ovos-workshop>=9.5.0a1 auto-registers every shipped .entity file)",
        )
        self.assertIn(
            brightness_name, by_name,
            "booting the skill with no manual register_entity_file() call "
            "should still auto-register {brightness} from "
            "locale/en-US/brightness.entity",
        )

        color_samples = set(by_name[color_name]["samples"])
        self.assertIn("turquoise", color_samples)
        self.assertIn("default", color_samples)

        brightness_samples = set(by_name[brightness_name]["samples"])
        self.assertIn("full", brightness_samples)
        self.assertIn("dim", brightness_samples)
        # bare "#" placeholder lines are dropped as comments, never
        # registered as literal or wildcard values
        self.assertNotIn("#", brightness_samples)
        # brightness.entity must ship real numeric examples, not just word
        # samples, so the {brightness} slot actually hints numeric values
        self.assertIn("50", brightness_samples)
