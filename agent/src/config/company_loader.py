import json
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

AGENT_DIRECTORY = (
    Path(__file__)
    .resolve()
    .parents[2]
)

COMPANIES_FILE = (
    AGENT_DIRECTORY
    / "config"
    / "companies.json"
)


# ============================================================
# COMPANY LOADER
# ============================================================

def load_companies() -> list[dict]:
    """
    Load enabled Greenhouse companies from companies.json.

    Expected JSON format:

    [
        {
            "name": "Stripe",
            "board_token": "stripe",
            "enabled": true
        }
    ]
    """

    # --------------------------------------------------------
    # FILE CHECK
    # --------------------------------------------------------

    if not COMPANIES_FILE.exists():

        raise FileNotFoundError(
            "Company configuration file "
            f"not found: {COMPANIES_FILE}"
        )

    # --------------------------------------------------------
    # READ JSON
    # --------------------------------------------------------

    with open(
        COMPANIES_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        companies = json.load(
            file
        )

    # --------------------------------------------------------
    # VALIDATE ROOT STRUCTURE
    # --------------------------------------------------------

    if not isinstance(
        companies,
        list,
    ):

        raise ValueError(
            "companies.json must contain "
            "a JSON array."
        )

    # --------------------------------------------------------
    # FILTER ENABLED COMPANIES
    # --------------------------------------------------------

    enabled_companies = []

    seen_tokens = set()

    for company in companies:

        if not isinstance(
            company,
            dict,
        ):
            continue

        enabled = company.get(
            "enabled",
            True,
        )

        if not enabled:
            continue

        name = (
            company
            .get(
                "name",
                "",
            )
            .strip()
        )

        board_token = (
            company
            .get(
                "board_token",
                "",
            )
            .strip()
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name:

            raise ValueError(
                "Every enabled company "
                "must have a name."
            )

        if not board_token:

            raise ValueError(
                f"{name} does not have "
                "a board_token."
            )

        # ----------------------------------------------------
        # DEDUPLICATE BOARD TOKENS
        # ----------------------------------------------------

        normalized_token = (
            board_token.lower()
        )

        if normalized_token in seen_tokens:
            continue

        seen_tokens.add(
            normalized_token
        )

        # ----------------------------------------------------
        # STORE
        # ----------------------------------------------------

        enabled_companies.append(
            {
                "name": name,
                "board_token": board_token,
            }
        )

    # --------------------------------------------------------
    # FINAL VALIDATION
    # --------------------------------------------------------

    if not enabled_companies:

        raise ValueError(
            "No enabled companies were "
            "found in companies.json."
        )

    return enabled_companies
