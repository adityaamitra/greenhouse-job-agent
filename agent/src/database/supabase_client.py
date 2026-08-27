import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


# ============================================================
# ENVIRONMENT
# ============================================================

AGENT_DIRECTORY = Path(__file__).resolve().parents[2]
ENV_FILE = AGENT_DIRECTORY / ".env"

load_dotenv(
    dotenv_path=ENV_FILE
)


# ============================================================
# CONFIGURATION
# ============================================================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY"
)

SUPABASE_OWNER_ID = os.getenv(
    "SUPABASE_OWNER_ID"
)


def validate_environment() -> None:
    """
    Verify all required Supabase environment variables exist.
    """

    missing = []

    if not SUPABASE_URL:
        missing.append(
            "SUPABASE_URL"
        )

    if not SUPABASE_SECRET_KEY:
        missing.append(
            "SUPABASE_SECRET_KEY"
        )

    if not SUPABASE_OWNER_ID:
        missing.append(
            "SUPABASE_OWNER_ID"
        )

    if missing:

        variables = ", ".join(
            missing
        )

        raise RuntimeError(
            "Missing required environment variables: "
            f"{variables}. "
            f"Expected .env file at: {ENV_FILE}"
        )


def get_supabase_client() -> Client:
    """
    Create a Supabase client for the local Python agent.

    The secret key must only exist in trusted backend/local code.
    """

    validate_environment()

    client: Client = create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY,
    )

    return client


def get_owner_id() -> str:
    """
    Return the Supabase user UUID that owns the job data.
    """

    validate_environment()

    return SUPABASE_OWNER_ID
