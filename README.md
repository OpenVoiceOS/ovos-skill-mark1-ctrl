## Mark1 Enclosure Control

An OVOS skill that controls the Mycroft Mark 1 enclosure by voice.

## Description

The Mycroft Mark 1 has a matrix of eyes that can change color and play
animations. This skill lets you control those eyes and other enclosure
features by voice, including eye color, brightness, and eye movement
animations.

Set the eye color to a named color ("blue", "magenta", "teal", and others)
or to a custom RGB value. See
[ovos-color-parser](https://github.com/OpenVoiceOS/ovos-color-parser) for
the full list of supported colors and formats.

## Install

```bash
pip install ovos-skill-mark1-ctrl
```

## Examples

* "Set your eye color to green"
* "Set a custom eye color" (you'll be prompted for values)
* "Dim to 50%"
* "look up"
* "look down"
* "look left"

* "look right"
* "look left and right"
* "look up and down"
* "reset enclosure"

* "narrow eyes"
* "spin eyes"
* "blink"
* "blink left"

* "smile animation"
* "listen animation"
* "think animation"

## Entity hints

The skill ships `locale/<lang>/color.entity` and `locale/<lang>/brightness.entity`, listing example values ("magenta", "teal", ...; "full", "bright", "half", "dim", "low", "auto", ...) for the `{color}` and `{brightness}` slots. These are hints, not a closed list: a color or brightness word not on the list still fills the slot; listed values simply match with more confidence. `ovos-workshop` (>=9.5.0a1) registers every shipped `.entity` file automatically when the skill's language resources are loaded, so nothing needs to be configured for this.

Numeric brightness ("50%", "50 percent") is parsed directly from the utterance by the skill's own code rather than from `brightness.entity`: resource files treat any line starting with `#` as a comment, so the file's leading `#`/`##%`-style placeholder lines never reach the matcher.

## Related projects

* [ovos-color-parser](https://github.com/OpenVoiceOS/ovos-color-parser): parses the color names and values this skill accepts
* [ovos-i2c-detection](https://github.com/OpenVoiceOS/ovos-i2c-detection): detects the Mark 1 enclosure hardware this skill controls

## License

Apache-2.0

## Credits

JarbasAI

[MycroftAI](https://github.com/MycroftAI/mycroft-mark-1)
