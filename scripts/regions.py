"""Where a gadget launched. Shared by build.py and check_posts.py.

origin (front matter) -> (name used in "Can you get it outside <name>?", board label, default FROM)
"""
from __future__ import annotations

REGIONS: dict[str, tuple[str, str, str]] = {
    # East Asia
    "cn": ("China", "CHINA", "CN China"),
    "jp": ("Japan", "JAPAN", "JP Japan"),
    "kr": ("South Korea", "KOREA", "KR Korea"),
    "tw": ("Taiwan", "TAIWAN", "TW Taiwan"),
    "hk": ("Hong Kong", "HK", "HK Hong Kong"),
    # Rest of Asia
    "in": ("India", "INDIA", "IN India"),
    "id": ("Indonesia", "INDONESIA", "ID Indonesia"),
    "th": ("Thailand", "THAILAND", "TH Thailand"),
    "vn": ("Vietnam", "VIETNAM", "VN Vietnam"),
    "my": ("Malaysia", "MALAYSIA", "MY Malaysia"),
    "sg": ("Singapore", "SINGAPORE", "SG Singapore"),
    "ph": ("the Philippines", "PHILIPPINES", "PH Philippines"),
    # Europe
    "eu": ("Europe", "EUROPE", "EU Europe"),
    "uk": ("the UK", "UK", "UK Britain"),
    "de": ("Germany", "GERMANY", "DE Germany"),
    "fr": ("France", "FRANCE", "FR France"),
    "it": ("Italy", "ITALY", "IT Italy"),
    "es": ("Spain", "SPAIN", "ES Spain"),
    "nl": ("the Netherlands", "NETHERLANDS", "NL Netherlands"),
    "be": ("Belgium", "BELGIUM", "BE Belgium"),
    "ch": ("Switzerland", "SWITZERLAND", "CH Switzerland"),
    "at": ("Austria", "AUSTRIA", "AT Austria"),
    "se": ("Sweden", "SWEDEN", "SE Sweden"),
    "no": ("Norway", "NORWAY", "NO Norway"),
    "dk": ("Denmark", "DENMARK", "DK Denmark"),
    "fi": ("Finland", "FINLAND", "FI Finland"),
    "pl": ("Poland", "POLAND", "PL Poland"),
    "cz": ("Czechia", "CZECHIA", "CZ Czechia"),
    "pt": ("Portugal", "PORTUGAL", "PT Portugal"),
    "ie": ("Ireland", "IRELAND", "IE Ireland"),
}

DEFAULT = "cn"  # posts written before 2026-11-18 have no origin and are all from China


def region(p: dict) -> tuple[str, str, str]:
    return REGIONS.get(str(p.get("origin") or DEFAULT).lower(), REGIONS[DEFAULT])


def outside_heading(p: dict) -> str:
    return f"## Can you get it outside {region(p)[0]}?"
