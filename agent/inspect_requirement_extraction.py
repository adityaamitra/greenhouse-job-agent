from src.greenhouse.client import get_jobs

from src.matching.requirement_extractor import (
    extract_requirements,
)


# ============================================================
# JOBS WE WANT TO INSPECT
# ============================================================

TARGETS = {
    "figma": {
        "Software Engineer - Full Stack",
        "Software Engineer - Growth & Monetization",
        "Software Engineer - Mobile Web",
    },

    "scaleai": {
        "Software Engineer, Platform",
        "Software Engineer - AI Enablement",
        "Software Engineer, Enterprise AI",
        "Software Engineer, Gen AI",
    },

    "stripe": {
        "AI Engineer",
        "Backend Engineer, Financial Connections",
        "Machine Learning Engineer, Radar",
        "Full Stack Engineer, Link",
    },
}


# ============================================================
# DISPLAY HELPERS
# ============================================================

def print_section(
    title: str,
    values: list[str],
):

    print()
    print(title)

    if not values:

        print("  None")
        return

    for value in values:

        print(
            f"  • {value}"
        )


def print_groups(
    groups: list[dict],
    section: str,
):

    matching_groups = [
        group
        for group
        in groups
        if (
            group.get(
                "section"
            )
            == section
        )
    ]

    print()
    print(
        f"{section.upper()} ALTERNATIVE GROUPS"
    )

    if not matching_groups:

        print("  None")
        return

    for index, group in enumerate(
        matching_groups,
        start=1,
    ):

        print(
            f"  {index}. "
            f"{' OR '.join(group.get('skills', []))}"
        )

        print(
            f"     Text: "
            f"{group.get('text', '')}"
        )


def print_evidence(
    evidence: list[dict],
):

    print()
    print("EXTRACTION EVIDENCE")
    print("-" * 90)

    if not evidence:

        print("  No technical evidence extracted.")
        return

    for index, item in enumerate(
        evidence,
        start=1,
    ):

        section = (
            item.get(
                "section",
                "unknown",
            )
        )

        reason = (
            item.get(
                "classification_reason",
                "unknown",
            )
        )

        skills = (
            item.get(
                "skills",
                [],
            )
        )

        alternative = (
            item.get(
                "alternative",
                False,
            )
        )

        text = (
            item.get(
                "text",
                "",
            )
        )

        print()

        print(
            f"{index}. "
            f"Section: {section.upper()}"
        )

        print(
            f"   Reason: "
            f"{reason}"
        )

        print(
            f"   Skills: "
            f"{', '.join(skills) if skills else 'None'}"
        )

        print(
            f"   Alternative: "
            f"{alternative}"
        )

        print(
            f"   Text:"
        )

        print(
            f"   {text}"
        )


def print_headings(
    headings: list[dict],
):

    print()
    print("RECOGNIZED HEADINGS")
    print("-" * 90)

    if not headings:

        print(
            "  None"
        )
        return

    for heading in headings:

        print(
            f"  • "
            f"[{heading.get('section', '').upper()}] "
            f"{heading.get('text', '')}"
        )


# ============================================================
# INSPECT ONE JOB
# ============================================================

def inspect_job(
    board_token: str,
    job: dict,
):

    title = (
        job.get(
            "title",
            "Unknown title",
        )
    )

    content = (
        job.get(
            "content",
            "",
        )
    )

    result = (
        extract_requirements(
            content
        )
    )

    print()
    print()
    print("=" * 90)

    print(
        f"{board_token.upper()} — "
        f"{title}"
    )

    print("=" * 90)

    print(
        f"URL: "
        f"{job.get('absolute_url', '')}"
    )

    stats = (
        result.get(
            "extraction_stats",
            {},
        )
    )

    print()
    print("EXTRACTION STATS")
    print("-" * 90)

    for key, value in (
        stats.items()
    ):

        print(
            f"  {key}: "
            f"{value}"
        )

    print_headings(
        result.get(
            "recognized_headings",
            [],
        )
    )

    print_section(
        "REQUIRED SKILLS",
        result.get(
            "required_skills",
            [],
        ),
    )

    print_section(
        "PREFERRED SKILLS",
        result.get(
            "preferred_skills",
            [],
        ),
    )

    print_section(
        "GENERAL SKILLS",
        result.get(
            "general_skills",
            [],
        ),
    )

    print_groups(
        result.get(
            "alternative_groups",
            [],
        ),
        "required",
    )

    print_groups(
        result.get(
            "alternative_groups",
            [],
        ),
        "preferred",
    )

    print_evidence(
        result.get(
            "evidence",
            [],
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)
    print(
        "REQUIREMENT EXTRACTION INSPECTOR"
    )
    print("=" * 90)

    total_found = 0

    for board_token, target_titles in (
        TARGETS.items()
    ):

        print()
        print(
            f"Fetching {board_token}..."
        )

        try:

            jobs = (
                get_jobs(
                    board_token
                )
            )

        except Exception as error:

            print(
                f"FAILED: {error}"
            )

            continue

        jobs_by_title = {
            job.get(
                "title",
                ""
            ): job
            for job
            in jobs
        }

        for title in sorted(
            target_titles
        ):

            job = (
                jobs_by_title.get(
                    title
                )
            )

            if not job:

                print()
                print(
                    f"⚠️ NOT FOUND: "
                    f"{board_token} — "
                    f"{title}"
                )

                continue

            total_found += 1

            inspect_job(
                board_token,
                job,
            )

    print()
    print()
    print("=" * 90)

    print(
        f"TOTAL INSPECTED: "
        f"{total_found}"
    )

    print("=" * 90)


if __name__ == "__main__":

    main()
