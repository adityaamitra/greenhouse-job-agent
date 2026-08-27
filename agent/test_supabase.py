from src.database.supabase_client import (
    get_owner_id,
    get_supabase_client,
)


def main():

    print()
    print("=" * 70)
    print("SUPABASE CONNECTION TEST")
    print("=" * 70)

    try:

        print()
        print(
            "Loading Supabase configuration..."
        )

        owner_id = get_owner_id()

        print(
            "Environment variables loaded successfully."
        )

        # Only show a small part of the UUID.
        # Never print secret keys.
        print(
            f"Owner ID loaded: "
            f"{owner_id[:8]}..."
        )

        print()
        print(
            "Creating Supabase client..."
        )

        supabase = get_supabase_client()

        print(
            "Supabase client created."
        )

        print()
        print(
            "Testing database access..."
        )

        response = (
            supabase
            .table("jobs")
            .select(
                "id, title"
            )
            .limit(1)
            .execute()
        )

        print()
        print(
            "Database query successful."
        )

        print(
            f"Rows returned: "
            f"{len(response.data)}"
        )

        print()
        print("=" * 70)
        print(
            "SUPABASE CONNECTION SUCCESSFUL"
        )
        print("=" * 70)

    except Exception as error:

        print()
        print("=" * 70)
        print(
            "SUPABASE CONNECTION FAILED"
        )
        print("=" * 70)

        print()
        print(
            f"Error type: "
            f"{type(error).__name__}"
        )

        print(
            f"Error: {error}"
        )

        print()
        print(
            "Do not paste your Supabase secret key "
            "when sharing this error."
        )


if __name__ == "__main__":
    main()
