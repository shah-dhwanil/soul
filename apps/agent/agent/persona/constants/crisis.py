"""Product-supplied crisis resources by locale and region (spec §16). Never invented."""

DEFAULT_LOCALE = "en-US"

GENERIC_RESOURCE_TEXT = "If you are in immediate danger, contact your local emergency number."

CRISIS_RESOURCES: dict[str, dict[str, str]] = {
    "en-US": {
        "us": (
            "If you are in immediate danger, call your local emergency number. "
            "In the US you can call or text 988 for the Suicide & Crisis Lifeline."
        ),
    },
}


def _first(regions: dict[str, str]) -> str:
    return next(iter(regions.values()))


def resolve_crisis_resources(locale: str | None) -> str:
    """Exact locale -> its region -> DEFAULT_LOCALE (only when no locale given) -> generic.

    An unrecognised locale gets the generic text rather than another country's numbers.
    """
    if not locale:
        locale = DEFAULT_LOCALE
    normalized = locale.replace("_", "-")
    by_region = CRISIS_RESOURCES.get(normalized)
    if by_region:
        return _first(by_region)
    parts = normalized.split("-")
    if len(parts) > 1:
        region = parts[-1].lower()
        for regions in CRISIS_RESOURCES.values():
            if region in regions:
                return regions[region]
    return GENERIC_RESOURCE_TEXT
