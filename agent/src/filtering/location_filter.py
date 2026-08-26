import re
from enum import Enum


class LocationStatus(Enum):
    US = "US"
    NON_US = "NON_US"
    UNKNOWN = "UNKNOWN"


# Exact values that clearly identify a US location.
US_EXACT_VALUES = {
    "us",
    "usa",
    "u.s.",
    "u.s.a.",
    "united states",
    "united states of america",
}


# Phrases that clearly indicate US availability.
US_KEYWORDS = [
    "united states",
    "united states of america",
    "us-remote",
    "us remote",
    "remote - us",
    "remote, us",
    "remote us",
    "us locations",
]


# Common US city names and office abbreviations.
US_CITY_ALIASES = {
    "nyc",
    "new york",
    "san francisco",
    "sf",
    "seattle",
    "sea",
    "chicago",
    "chi",
    "boston",
    "los angeles",
    "la",
    "austin",
    "denver",
    "atlanta",
    "miami",
    "washington dc",
    "washington, dc",
    "dc",
    "portland",
    "dallas",
    "houston",
    "philadelphia",
    "phoenix",
    "san diego",
    "south san francisco",
}


US_STATE_NAMES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
}


US_STATE_ABBREVIATIONS = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
}


NON_US_KEYWORDS = [
    "canada",
    "ireland",
    "united kingdom",
    "london",
    "singapore",
    "australia",
    "japan",
    "india",
    "germany",
    "france",
    "netherlands",
    "spain",
    "mexico",
    "brazil",
    "sweden",
    "poland",
    "switzerland",
    "denmark",
    "norway",
    "finland",
    "italy",
    "portugal",
    "belgium",
    "austria",
    "new zealand",
    "hong kong",
    "china",
    "south korea",
]


UNKNOWN_VALUES = {
    "",
    "n/a",
    "na",
    "unknown",
    "-",
    "none",
}


def classify_location_text(location: str) -> LocationStatus:
    """
    Classify a single location string as US, NON_US, or UNKNOWN.
    """

    if not location:
        return LocationStatus.UNKNOWN

    original = str(location).strip()
    normalized = original.lower().strip()

    if normalized in UNKNOWN_VALUES:
        return LocationStatus.UNKNOWN

    # Exact US values such as "US".
    if normalized in US_EXACT_VALUES:
        return LocationStatus.US

    # Explicit US phrases.
    if any(keyword in normalized for keyword in US_KEYWORDS):
        return LocationStatus.US

    # US city aliases.
    for city in US_CITY_ALIASES:
        if re.search(rf"\b{re.escape(city)}\b", normalized):
            return LocationStatus.US

    # Full US state names.
    for state in US_STATE_NAMES:
        if re.search(rf"\b{re.escape(state)}\b", normalized):
            return LocationStatus.US

    # Check comma/slash/pipe-separated state abbreviations.
    pieces = [
        piece.strip().upper()
        for piece in re.split(r"[,/|]", original)
    ]

    if any(piece in US_STATE_ABBREVIATIONS for piece in pieces):
        return LocationStatus.US

    # Only label NON_US when there is clear evidence.
    if any(keyword in normalized for keyword in NON_US_KEYWORDS):
        return LocationStatus.NON_US

    return LocationStatus.UNKNOWN


def extract_office_texts(job: dict) -> list[str]:
    """
    Extract useful location-related text from Greenhouse office metadata.
    """

    office_texts = []

    for office in job.get("offices", []) or []:
        name = office.get("name")

        if name:
            office_texts.append(str(name))

        office_location = office.get("location")

        if isinstance(office_location, str):
            office_texts.append(office_location)

        elif isinstance(office_location, dict):
            for value in office_location.values():
                if value:
                    office_texts.append(str(value))

    return office_texts


def classify_job_location(job: dict) -> LocationStatus:
    """
    Determine whether a Greenhouse job is available in the US.

    Priority:
    1. Main Greenhouse location field
    2. Greenhouse office metadata
    3. UNKNOWN if neither gives reliable evidence
    """

    location_name = (
        job.get("location", {}).get("name", "")
        if isinstance(job.get("location"), dict)
        else ""
    )

    primary_status = classify_location_text(location_name)

    # If the main location already tells us the answer, trust it.
    if primary_status != LocationStatus.UNKNOWN:
        return primary_status

    # Otherwise inspect Greenhouse office metadata.
    office_texts = extract_office_texts(job)

    if not office_texts:
        return LocationStatus.UNKNOWN

    office_statuses = [
        classify_location_text(text)
        for text in office_texts
    ]

    # If at least one office is in the US, the job is US-compatible.
    if LocationStatus.US in office_statuses:
        return LocationStatus.US

    # If we found non-US evidence and no US evidence, reject it.
    if LocationStatus.NON_US in office_statuses:
        return LocationStatus.NON_US

    return LocationStatus.UNKNOWN


def filter_by_location(jobs: list[dict]):
    """
    Split jobs into US-compatible, unknown, and non-US buckets.
    """

    us_jobs = []
    unknown_jobs = []
    non_us_jobs = []

    for job in jobs:
        status = classify_job_location(job)

        if status == LocationStatus.US:
            us_jobs.append(job)

        elif status == LocationStatus.NON_US:
            non_us_jobs.append(job)

        else:
            unknown_jobs.append(job)

    return us_jobs, unknown_jobs, non_us_jobs
