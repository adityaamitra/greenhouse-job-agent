import requests


BASE_URL = "https://api.greenhouse.io/v1/boards"


def get_jobs(board_token: str) -> list[dict]:
    """
    Fetch all currently published jobs for a Greenhouse board.
    """

    url = f"{BASE_URL}/{board_token}/jobs"

    params = {
        "content": "true"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        return data.get("jobs", [])

    except requests.exceptions.RequestException as exc:
        print(f"Error fetching Greenhouse jobs: {exc}")
        return []
