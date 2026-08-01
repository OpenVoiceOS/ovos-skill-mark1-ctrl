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

* "narrow your eyes"
* "spin your eyes"
* "blink your eyes"

* "smile animation"
* "listen animation"
* "think animation"

## Related projects

* [ovos-color-parser](https://github.com/OpenVoiceOS/ovos-color-parser): parses the color names and values this skill accepts
* [ovos-i2c-detection](https://github.com/OpenVoiceOS/ovos-i2c-detection): detects the Mark 1 enclosure hardware this skill controls

## License

Apache-2.0

## Credits

JarbasAI

[MycroftAI](https://github.com/MycroftAI/mycroft-mark-1)
