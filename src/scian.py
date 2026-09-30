"""SCIAN sector names and the retail / service / other grouping used by the KPIs."""

from __future__ import annotations

# SCIAN splits some sectors across several two-digit codes (31-33, 48-49); they share a name.
SECTOR_NAMES = {
    "11": "Agriculture, forestry, fishing and hunting",
    "21": "Mining",
    "22": "Utilities",
    "23": "Construction",
    "31": "Manufacturing",
    "32": "Manufacturing",
    "33": "Manufacturing",
    "43": "Wholesale trade",
    "46": "Retail trade",
    "48": "Transportation and warehousing",
    "49": "Transportation and warehousing",
    "51": "Information",
    "52": "Finance and insurance",
    "53": "Real estate and rental",
    "54": "Professional, scientific and technical services",
    "55": "Management of companies",
    "56": "Business support and waste management services",
    "61": "Educational services",
    "62": "Health care and social assistance",
    "71": "Arts, entertainment and recreation",
    "72": "Accommodation and food services",
    "81": "Other services (except government)",
    "93": "Government and international organisations",
}

RETAIL_SECTORS = {"46"}
SERVICE_SECTORS = {"51", "52", "53", "54", "55", "56", "61", "62", "71", "72", "81"}


def sector_code(scian_code: str) -> str:
    """Two-digit sector of a six-digit SCIAN activity code."""
    return str(scian_code).strip()[:2]


def sector_name(code: str) -> str:
    return SECTOR_NAMES.get(sector_code(code), "Unknown")


def sector_group(code: str) -> str:
    """`retail` (sector 46), `service` (sectors 51 to 81) or `other`."""
    sector = sector_code(code)
    if sector in RETAIL_SECTORS:
        return "retail"
    if sector in SERVICE_SECTORS:
        return "service"
    return "other"
