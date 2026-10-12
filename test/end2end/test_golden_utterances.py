"""Golden rows in every locale route to their intent on the m2v pipeline.

For each ``golden_utterances_<lang>.jsonl`` in this directory, one MiniCroft
loads the real skill in that language on the m2v prototype pipeline, the
model2vec engine built at boot from the skill's own ``.intent`` files. Each
row's utterance goes through that pipeline's high, medium and low tiers in
order, and the row passes when the first tier to match names its
``intent_label``. The engine embeds the utterance, so a row that no template
spells out word for word still matches when it means the same thing. Only the
match is computed: no row is dispatched.

Each ``negative_utterances_<lang>.jsonl`` holds requests for other skills
(weather, timers, the time, jokes, music, questions). They run in the same
MiniCroft and must match no intent of this skill.

Each locale must match at least ``MIN_MATCH_RATE`` of its golden rows, and at
least ``MIN_MATCHED_ROWS_PER_INTENT`` rows of each intent. A locale listed in
``GOLDEN_LOCALE_GAPS`` reports a lower rate as an xfail, but still fails on
the per-intent floor or on a rate far below its measured gap rate. A negative row that
matches this skill fails the locale, unless ``NEGATIVE_KNOWN_CLAIMS`` lists
that claim. All rows run, including rows marked ``needs_manual`` or
``machine_generated``, and the test prints every row that misses with the
intent that matched instead, and a confusion count of expected -> got.

The skill refuses to load off a physical Mark 1 (I2C probe), so
``ovos_i2c_detection.is_mark_1`` is stubbed True before the skill loads.
"""
import json
from collections import Counter
from functools import cache
from pathlib import Path

import ovos_i2c_detection
import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import SessionManager
from ovoscope import M2V_PUBLISHED_MODEL, get_m2v_minicroft
from ovoscope.golden_minicroft import warm_m2v_models

ovos_i2c_detection.is_mark_1 = lambda: True

SKILL_ID = "ovos-skill-mark1-ctrl.openvoiceos"
M2V_PROTOTYPE = "ovos-m2v-prototype-pipeline"
TIERS = ("high", "medium", "low")
# m2v gives some rows a different answer on each boot, so the test gates on
# the share of rows that match per locale, not on each row.
MIN_MATCH_RATE = 0.8
# A locale also fails when any of its intents has fewer matched rows than this.
MIN_MATCHED_ROWS_PER_INTENT = 1
# Locales whose rows the published m2v model cannot reach 80% on, even after
# the machine-translated template lines: {lang: (measured rate, reason)}.
# Their rate check is an xfail that prints the rate. The per-intent floor
# still runs, and a rate more than GAP_TOLERANCE below the measured rate fails.
GOLDEN_LOCALE_GAPS = {
    "ca-ES": (0.725, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "de-DE": (0.725, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "el-GR": (0.706, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "es-CO": (0.765, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "es-ES": (0.667, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "eu-ES": (0.667, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "fr-FR": (0.765, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "gl-ES": (0.686, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "it-IT": (0.647, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "kab": (0.529, "no linguonnx route from en; kab templates are unvouched machine drafts"),
    "oc-FR": (0.608, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "pl-PL": (0.510, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "pt-BR": (0.686, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "pt-PT": (0.686, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "ru-RU": (0.569, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
    "sv-SE": (0.784, "machine-drafted templates; linguonnx lines added, still below 80% in two runs"),
}
GAP_TOLERANCE = 0.10
# (lang, intent) pairs that matched 0 rows on m2v in a measured run; the
# per-intent floor skips only these pairs.
GOLDEN_INTENT_GAPS = {
    ("ca-ES", "look_down"): "measured: 0 matched rows on m2v in two runs",
    ("ca-ES", "look_up"): "measured: 0 matched rows on m2v in two runs",
    ("eu-ES", "look_down"): "measured: 0 matched rows on m2v in two runs",
    ("fa-IR", "think"): "measured: 0 matched rows on m2v in two runs",
    ("gl-ES", "narrow_eyes"): "measured: 0 matched rows on m2v in two runs",
    ("it-IT", "custom_eye_color"): "measured: 0 matched rows on m2v in one run",
    ("oc-FR", "custom_eye_color"): "measured: 0 matched rows on m2v in two runs",
    ("oc-FR", "reset"): "measured: 0 matched rows on m2v in two runs",
    ("pl-PL", "look_up"): "measured: 0 matched rows on m2v in two runs",
    ("pl-PL", "think"): "measured: 0 matched rows on m2v in two runs",
    ("pt-PT", "blink"): "measured: 0 matched rows on m2v in two runs",
    ("ru-RU", "look_down"): "measured: 0 matched rows on m2v in two runs",
}
# Locales where the published m2v model cannot keep other skills' requests
# away from this skill. Their negative test is a non-strict xfail.
NEGATIVE_ENGINE_GAPS = {
    "el-GR": "measured: m2v claims all 6 el-GR negative rows in two runs",
    "ru-RU": "measured: m2v claims all 6 ru-RU negative rows in two runs",
}
# Negative rows that m2v claimed for this skill in two separate runs. A listed
# claim is allowed, not required, so a row that flips between boots does not
# fail the test. A tuple lists every intent the row went to across runs. Any
# other claim fails the locale.
NEGATIVE_KNOWN_CLAIMS = {
    "ca-ES": {"posa una mica de música": ("brightness",)},
    "pl-PL": {"włącz jakąś muzykę": ("eye_color", "narrow_eyes")},
}
END2END_DIR = Path(__file__).parent
LOCALE_DIR = END2END_DIR.parents[1] / "locale"
DEFAULT_LANG_AT_IMPORT = SessionManager.get_default_session().lang


def _rows_by_lang(prefix):
    rows = {}
    for path in sorted(END2END_DIR.glob(f"{prefix}_*.jsonl")):
        lang = path.stem.removeprefix(f"{prefix}_")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                row = json.loads(line)
                assert row["lang"] == lang, f"{path.name}:{number} has lang {row['lang']!r}"
                rows.setdefault(lang, []).append(row)
    return rows


ROWS = _rows_by_lang("golden_utterances")
NEGATIVE_ROWS = _rows_by_lang("negative_utterances")


def _matched_intent(engine, utterance, lang):
    message = Message("recognizer_loop:utterance",
                      {"utterances": [utterance], "lang": lang}, {"lang": lang})
    match = next(filter(None, (getattr(engine, f"match_{tier}")([utterance], lang, message)
                               for tier in TIERS)), None)
    return match.match_type if match else None


@cache
def _matches(lang):
    """Boot the skill on m2v in ``lang`` once; return what each golden and negative row matches."""
    minicroft = get_m2v_minicroft([SKILL_ID], model=M2V_PUBLISHED_MODEL,
                                  lang=lang, classifier=False)
    try:
        warm_m2v_models(minicroft)
        engine = minicroft.intents.pipeline_plugins[M2V_PROTOTYPE]
        golden = [_matched_intent(engine, row["utterance"], lang) for row in ROWS[lang]]
        negative = [_matched_intent(engine, row["utterance"], lang)
                    for row in NEGATIVE_ROWS.get(lang, [])]
    finally:
        minicroft.stop()
    return golden, negative


@pytest.mark.timeout(900)
@pytest.mark.parametrize("lang", sorted(ROWS))
def test_golden_rows_match_their_intent(lang):
    rows = ROWS[lang]
    matched, _ = _matches(lang)
    misses = []
    confusion = Counter()
    hits = {row["intent_label"]: 0 for row in rows}
    for row, got in zip(rows, matched):
        if got == f"{SKILL_ID}:{row['intent_label']}":
            hits[row["intent_label"]] += 1
        else:
            misses.append(f"{row['utterance']!r}: expected {row['intent_label']}, got {got}")
            confusion[(row["intent_label"], (got or "None").removeprefix(f"{SKILL_ID}:"))] += 1
    starved = sorted(label for label, count in hits.items()
                     if count < MIN_MATCHED_ROWS_PER_INTENT and (lang, label) not in GOLDEN_INTENT_GAPS)
    rate = 1 - len(misses) / len(rows)
    print(f"[{lang}] {rate:.1%} of {len(rows)} rows match", *misses, sep="\n  ")
    print(f"[{lang}] confusion:", *(f"{want} -> {got}: {n}" for (want, got), n in confusion.most_common()),
          sep="\n  ")
    if starved:
        print(f"[{lang}] intents below {MIN_MATCHED_ROWS_PER_INTENT} matched rows: {starved}")
    assert not starved, (
        f"[{lang}] intents below {MIN_MATCHED_ROWS_PER_INTENT} matched rows: {starved}"
    )
    if lang in GOLDEN_LOCALE_GAPS and rate < MIN_MATCH_RATE:
        measured, reason = GOLDEN_LOCALE_GAPS[lang]
        assert rate >= measured - GAP_TOLERANCE, (
            f"[{lang}] {rate:.1%} of rows match, more than {GAP_TOLERANCE:.0%} below "
            f"the measured gap rate {measured:.1%}"
        )
        pytest.xfail(f"[{lang}] {rate:.1%} of rows match (measured {measured:.1%}): {reason}")
    assert rate >= MIN_MATCH_RATE, (
        f"[{lang}] {rate:.1%} of rows match, below {MIN_MATCH_RATE:.0%}:\n  " + "\n  ".join(misses)
    )


@pytest.mark.timeout(900)
@pytest.mark.parametrize("lang", [
    pytest.param(lang, marks=pytest.mark.xfail(reason=NEGATIVE_ENGINE_GAPS[lang], strict=False))
    if lang in NEGATIVE_ENGINE_GAPS else lang
    for lang in sorted(NEGATIVE_ROWS)
])
def test_negative_rows_match_no_skill_intent(lang):
    rows = NEGATIVE_ROWS[lang]
    known = NEGATIVE_KNOWN_CLAIMS.get(lang, {})
    _, matched = _matches(lang)
    claims = [(row["utterance"], got.removeprefix(f"{SKILL_ID}:"))
              for row, got in zip(rows, matched)
              if got and got.startswith(f"{SKILL_ID}:")]
    unknown = [f"{utterance!r}: matched {intent}" for utterance, intent in claims
               if intent not in known.get(utterance, ())]
    print(f"[{lang}] {len(claims)} of {len(rows)} negative rows claimed, "
          f"{len(unknown)} not in NEGATIVE_KNOWN_CLAIMS", *unknown, sep="\n  ")
    assert not unknown, f"[{lang}] negative rows matched this skill:\n  " + "\n  ".join(unknown)


def test_every_negative_file_has_a_golden_file():
    assert set(NEGATIVE_ROWS) <= set(ROWS), sorted(set(NEGATIVE_ROWS) - set(ROWS))


def test_every_shipping_locale_has_a_golden_file():
    shipping = {d.name for d in LOCALE_DIR.iterdir() if d.is_dir() and any(d.rglob("*.intent"))}
    assert set(ROWS) == shipping, f"golden files {sorted(set(ROWS) ^ shipping)} differ from shipping locales"


def test_every_locale_ships_every_en_us_intent():
    """A deleted .intent file fails here, whatever the golden rows say."""
    reference = {p.name for p in (LOCALE_DIR / "en-US").glob("*.intent")}
    assert reference, "en-US ships no .intent file"
    missing = {d.name: sorted(reference - {p.name for p in d.glob("*.intent")})
               for d in LOCALE_DIR.iterdir() if d.is_dir()}
    missing = {lang: names for lang, names in missing.items() if names}
    assert not missing, f"locales missing en-US intents: {missing}"


def test_every_golden_label_is_a_shipped_intent():
    for lang, rows in ROWS.items():
        shipped = {p.stem for p in (LOCALE_DIR / lang).glob("*.intent")}
        unknown = sorted({row["intent_label"] for row in rows} - shipped)
        assert not unknown, f"[{lang}] rows name intents the locale does not ship: {unknown}"


def test_the_module_leaves_the_process_on_its_default_language():
    """A MiniCroft booted in one locale writes the process default language
    back when it stops. If it did not, every MiniCroft booted later in the
    same pytest process would load the skill in the last locale and route
    nothing. This test runs after every locale and reads that value."""
    assert SessionManager.get_default_session().lang == DEFAULT_LANG_AT_IMPORT
