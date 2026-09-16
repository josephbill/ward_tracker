"""
Template + variable rendering, not hand-translated prose per project. Every
project statement is built from ONE template per language (locales/*.json)
with variables substituted in — so adding a new ward or a new project never
requires touching translation strings, only the source data.

Numbers, currency and dates are formatted the same locale-consistent way
(Ksh with thousands separators, ISO-ish dates) regardless of UI language, per
Section 4 of the spec — money should look like money in every language.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"

# Sector/department names as they appear verbatim in the source PDF. Small,
# fixed set (new counties would add their own department names here) — kept
# as a code-level lookup rather than a DB table since, unlike project names,
# these repeat across many records and never change per-project. Swahili
# translations are direct; Kikamba is a best-effort draft, same caveat as
# backend/app/locales/kam.json.
_SECTOR_TRANSLATIONS: dict[str, dict[str, str]] = {
    "Agriculture": {"sw": "Kilimo", "kam": "Ũlĩmi"},
    "Agriculture, Livestock, Fisheries & Cooperative Development": {
        "sw": "Kilimo, Mifugo, Uvuvi na Maendeleo ya Ushirika",
        "kam": "Ũlĩmi, Indo, Ũvuvi na Ũthũkũmi wa Ushirika",
    },
    "County Attorney": {"sw": "Wakili wa Kaunti", "kam": "Loya wa Kaunti"},
    "Emali-Sultan Municipality": {"sw": "Manispaa ya Emali-Sultan Hamud", "kam": "Manispaa ya Emali-Sultan Hamud"},
    "Gender": {"sw": "Jinsia", "kam": "Ũlũmũ"},
    "Gender, Children, Youth, Sports and Social Services": {
        "sw": "Jinsia, Watoto, Vijana, Michezo na Huduma za Kijamii",
        "kam": "Ũlũmũ, Syana, Ethaka, Masugua na Ũtethyo wa Andũ",
    },
    "Health": {"sw": "Afya", "kam": "Ũima"},
    "Health Services": {"sw": "Huduma za Afya", "kam": "Ũtethyo wa Ũima"},
    "ICT, Education & Internship": {"sw": "TEHAMA, Elimu na Mafunzo kwa Vitendo", "kam": "ICT, Ũmanyi na Mathomo ma Wĩa"},
    "Infrastracture": {"sw": "Miundombinu", "kam": "Mĩako"},
    "Infrastructure, Transport, Public Works, Housing & Energy": {
        "sw": "Miundombinu, Usafiri, Kazi za Umma, Makazi na Nishati",
        "kam": "Mĩako, Ũthiĩi, Wĩa wa Andũ Onthe, Nyũmba na Ũkw'ũ",
    },
    "Lands, Urban Development & Environment and Climate Change": {
        "sw": "Ardhi, Maendeleo ya Mijini, Mazingira na Mabadiliko ya Tabianchi",
        "kam": "Mathaka, Ũthũkũmi wa Matauni, Mawĩthĩo na Ũalyũku wa Nzeve",
    },
    "Water": {"sw": "Maji", "kam": "Kĩw'ũ"},
    "Water Sanitation and Irrigation": {"sw": "Maji, Usafi wa Mazingira na Umwagiliaji", "kam": "Kĩw'ũ, Ũtheu na Ũnyũsyo"},
}

# "Cross-cutting" (a project not tied to one subward) is the only recurring
# subward value that's actual English needing translation — "Kasikeu" and
# "Kiou" are place names and are deliberately never translated.
_SUBWARD_TRANSLATIONS: dict[str, dict[str, str]] = {
    "Cross-cutting": {"sw": "Mtambuka (wadi nzima)", "kam": "Wadi yonthe"},
}


@lru_cache(maxsize=None)
def _load_locale(lang: str) -> dict:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        raise ValueError(f"Unsupported language: {lang}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_ksh(amount: int) -> str:
    """Locale-consistent currency formatting: 'Ksh 1,234,567' in every language."""
    return f"Ksh {amount:,.0f}"


def format_fy(financial_year: str) -> str:
    return financial_year  # already "2022/23" style, kept as-is across locales


def t(lang: str, key: str, **variables) -> str:
    """Look up `key` in `lang`'s locale file and substitute `variables`.
    Falls back to English if the language is unsupported or the key is
    missing in the requested language (keeps every webhook handler from
    ever 500ing on a bad/unrecognized `lang` value)."""
    try:
        locale = _load_locale(lang)
    except ValueError:
        locale = _load_locale("en")
    template = locale.get(key)
    if template is None:
        template = _load_locale("en").get(key, key)
    try:
        return template.format(**variables)
    except (KeyError, IndexError):
        return template


def resolve_project_name(project: dict, lang: str) -> str:
    """The project name in `lang` — expects a dict from Project.to_dict(),
    which carries project_name_sw/project_name_kam alongside the English
    project_name. Falls back to English when no translation exists for this
    specific project (e.g. a gap in Kikamba's best-effort coverage)."""
    if lang == "en":
        return project["project_name"]
    return project.get(f"project_name_{lang}") or project["project_name"]


def translate_sector(sector: str, lang: str) -> str:
    if lang == "en":
        return sector
    return _SECTOR_TRANSLATIONS.get(sector, {}).get(lang) or sector


def translate_subward(subward: str, lang: str) -> str:
    if lang == "en":
        return subward
    return _SUBWARD_TRANSLATIONS.get(subward, {}).get(lang) or subward


def render_project_statement(project: dict, lang: str) -> str:
    """Build the plain-language, translated statement for one project record."""
    county_status_key = f"county_status_{project['county_claimed_status']}"
    verification_status_key = f"verification_status_{project['verification_status']}"
    return t(
        lang,
        "project_statement",
        project_name=resolve_project_name(project, lang),
        ward=project["ward"],
        subward=translate_subward(project["subward"], lang),
        amount=format_ksh(project["allocated_amount_ksh"]),
        financial_year=format_fy(project["financial_year"]),
        sector=translate_sector(project["sector"], lang),
        county_status=t(lang, county_status_key),
        verification_status=t(lang, verification_status_key),
    )


def supported_languages() -> list[str]:
    return sorted(p.stem for p in LOCALES_DIR.glob("*.json"))
