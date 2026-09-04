from src.config.company_loader import (
    load_companies,
)

from src.greenhouse.client import (
    get_jobs,
)

from src.filtering.job_filter import (
    filter_by_role,
)

from src.filtering.employment_filter import (
    filter_by_employment_type,
)

from src.filtering.location_filter import (
    filter_by_location,
)

from src.filtering.experience_filter import (
    filter_by_experience,
    clean_job_content,
)

from src.filtering.eligibility_filter import (
    evaluate_hard_eligibility,
)

from src.matching.resume_loader import (
    load_all_resumes,
)

from src.matching.matcher import (
    MANUAL_PRIORITY_THRESHOLD,
    prepare_resume_cache,
    rank_resumes,
)


# ============================================================
# PROPOSED SCORE CALIBRATION V2
# ============================================================
#
# IMPORTANT:
#
# This script is READ-ONLY.
#
# It does NOT:
#
#   - write to Supabase
#   - modify applications
#   - change routes
#   - alter matcher.py
#
# We are comparing the existing scoring model against a
# proposed model before changing production behavior.
#
#
# CURRENT MODEL:
#
#   Role         25
#   Required     35
#   Preferred    10
#   Semantic     20
#   Experience   10
#
#
# PROPOSED JOB-FIT MODEL:
#
#   Required     45
#   Preferred    10
#   Semantic     30
#   Experience   15
#
#   Role alignment is REMOVED from final job-fit scoring.
#
#
# Missing structured evidence gets a neutral score of 50,
# rather than a perfect 100.
#
# This is equivalent to pulling low-confidence scores toward
# the middle rather than pretending missing information is
# evidence of a perfect match.
# ============================================================

NEUTRAL_UNKNOWN_SCORE = (
    50.0
)

PROPOSED_FIT_WEIGHTS = {
    "required": 45.0,
    "preferred": 10.0,
    "semantic": 30.0,
    "experience": 15.0,
}


# ============================================================
# RESUME-SELECTION MODEL
# ============================================================
#
# Role alignment is still useful for deciding WHICH resume
# should be used.
#
# It simply should not automatically contribute 25 points
# toward whether the job itself is a strong fit.
#
# Proposed resume selection:
#
#   Role alignment       55%
#   Semantic similarity  25%
#   Required coverage    20%
#
# Missing required extraction is neutral (50) for selection.
# ============================================================

RESUME_SELECTION_WEIGHTS = {
    "role": 0.55,
    "semantic": 0.25,
    "required": 0.20,
}


# ============================================================
# HELPERS
# ============================================================

def pretty_name(
    name: str,
) -> str:

    return (
        name
        .replace(
            "_",
            " ",
        )
        .title()
    )


def get_job_location(
    job: dict,
) -> str:

    return (
        job
        .get(
            "location",
            {},
        )
        .get(
            "name",
            "Unknown location",
        )
    )


def get_component_availability(
    candidate: dict,
) -> dict:

    explanation = (
        candidate[
            "explanation"
        ]
    )

    required_available = (
        explanation.get(
            "required_units",
            0,
        )
        > 0
    )

    preferred_available = (
        explanation.get(
            "preferred_units",
            0,
        )
        > 0
    )

    experience_available = (
        explanation.get(
            "required_minimum_years"
        )
        is not None
    )

    # Semantic matching is available for every scored job
    # because the scanner has a non-empty job description.
    semantic_available = (
        True
    )

    return {
        "required": (
            required_available
        ),

        "preferred": (
            preferred_available
        ),

        "semantic": (
            semantic_available
        ),

        "experience": (
            experience_available
        ),
    }


def effective_score(
    *,
    score: float,
    available: bool,
) -> float:

    if available:

        return float(
            score
        )

    return (
        NEUTRAL_UNKNOWN_SCORE
    )


# ============================================================
# PROPOSED RESUME SELECTION
# ============================================================

def calculate_resume_selection_score(
    candidate: dict,
) -> float:

    availability = (
        get_component_availability(
            candidate
        )
    )

    required_effective = (
        effective_score(
            score=(
                candidate[
                    "required_score"
                ]
            ),

            available=(
                availability[
                    "required"
                ]
            ),
        )
    )

    score = (
        candidate[
            "role_score"
        ]
        * RESUME_SELECTION_WEIGHTS[
            "role"
        ]

        + candidate[
            "semantic_score"
        ]
        * RESUME_SELECTION_WEIGHTS[
            "semantic"
        ]

        + required_effective
        * RESUME_SELECTION_WEIGHTS[
            "required"
        ]
    )

    return round(
        score,
        2,
    )


def select_proposed_resume(
    rankings: list[dict],
) -> tuple[
    dict,
    float,
]:

    scored = []

    for candidate in rankings:

        selection_score = (
            calculate_resume_selection_score(
                candidate
            )
        )

        scored.append(
            (
                selection_score,
                candidate,
            )
        )

    scored.sort(
        key=lambda item: (
            item[
                0
            ]
        ),
        reverse=True,
    )

    return (
        scored[
            0
        ][
            1
        ],

        scored[
            0
        ][
            0
        ],
    )


# ============================================================
# PROPOSED JOB-FIT SCORE
# ============================================================

def calculate_proposed_fit(
    candidate: dict,
) -> dict:

    availability = (
        get_component_availability(
            candidate
        )
    )

    required_effective = (
        effective_score(
            score=(
                candidate[
                    "required_score"
                ]
            ),

            available=(
                availability[
                    "required"
                ]
            ),
        )
    )

    preferred_effective = (
        effective_score(
            score=(
                candidate[
                    "preferred_score"
                ]
            ),

            available=(
                availability[
                    "preferred"
                ]
            ),
        )
    )

    semantic_effective = (
        effective_score(
            score=(
                candidate[
                    "semantic_score"
                ]
            ),

            available=(
                availability[
                    "semantic"
                ]
            ),
        )
    )

    experience_effective = (
        effective_score(
            score=(
                candidate[
                    "experience_score"
                ]
            ),

            available=(
                availability[
                    "experience"
                ]
            ),
        )
    )

    contributions = {
        "required": round(
            required_effective
            * PROPOSED_FIT_WEIGHTS[
                "required"
            ]
            / 100.0,
            2,
        ),

        "preferred": round(
            preferred_effective
            * PROPOSED_FIT_WEIGHTS[
                "preferred"
            ]
            / 100.0,
            2,
        ),

        "semantic": round(
            semantic_effective
            * PROPOSED_FIT_WEIGHTS[
                "semantic"
            ]
            / 100.0,
            2,
        ),

        "experience": round(
            experience_effective
            * PROPOSED_FIT_WEIGHTS[
                "experience"
            ]
            / 100.0,
            2,
        ),
    }

    final_score = round(
        sum(
            contributions.values()
        ),
        2,
    )

    # --------------------------------------------------------
    # EVIDENCE CONFIDENCE
    # --------------------------------------------------------
    #
    # Confidence is NOT part of routing yet.
    #
    # It simply tells us how much of the 100-point model was
    # supported by actual extracted evidence.
    #
    # Semantic is always available → baseline 30%.
    # --------------------------------------------------------

    evidence_weight = 0.0

    for component, weight in (
        PROPOSED_FIT_WEIGHTS.items()
    ):

        if availability[
            component
        ]:

            evidence_weight += (
                weight
            )

    confidence = round(
        evidence_weight,
        2,
    )

    route = (
        "MANUAL_PRIORITY"
        if (
            final_score
            >= MANUAL_PRIORITY_THRESHOLD
        )
        else "AGENT_APPLY"
    )

    return {
        "final_score": (
            final_score
        ),

        "route": (
            route
        ),

        "confidence": (
            confidence
        ),

        "availability": (
            availability
        ),

        "effective_scores": {
            "required": (
                required_effective
            ),

            "preferred": (
                preferred_effective
            ),

            "semantic": (
                semantic_effective
            ),

            "experience": (
                experience_effective
            ),
        },

        "contributions": (
            contributions
        ),
    }


# ============================================================
# DISPLAY
# ============================================================

def availability_marker(
    available: bool,
) -> str:

    if available:

        return (
            "REAL"
        )

    return (
        "NEUTRAL"
    )


def print_job_comparison(
    item: dict,
    index: int,
) -> None:

    current = (
        item[
            "current_candidate"
        ]
    )

    proposed = (
        item[
            "proposed_candidate"
        ]
    )

    fit = (
        item[
            "proposed_fit"
        ]
    )

    availability = (
        fit[
            "availability"
        ]
    )

    effective = (
        fit[
            "effective_scores"
        ]
    )

    contributions = (
        fit[
            "contributions"
        ]
    )

    print()
    print("-" * 100)

    print(
        f"{index}. "
        f"{item['company']} — "
        f"{item['title']}"
    )

    print("-" * 100)

    print(
        f"Current resume:       "
        f"{pretty_name(current['resume_name'])}"
    )

    print(
        f"Current score:        "
        f"{current['final_score']:.2f}"
    )

    print(
        f"Current route:        "
        f"{current['route']}"
    )

    print()

    print(
        f"Proposed resume:      "
        f"{pretty_name(proposed['resume_name'])}"
    )

    print(
        f"Resume select score:  "
        f"{item['selection_score']:.2f}"
    )

    print(
        f"Proposed fit score:   "
        f"{fit['final_score']:.2f}"
    )

    print(
        f"Proposed route:       "
        f"{fit['route']}"
    )

    print(
        f"Evidence confidence:  "
        f"{fit['confidence']:.0f}%"
    )

    print()

    print(
        "Proposed fit components:"
    )

    print(
        f"  Required:   "
        f"{effective['required']:6.2f} "
        f"[{availability_marker(availability['required']):7}] "
        f"→ {contributions['required']:5.2f}/45"
    )

    print(
        f"  Preferred:  "
        f"{effective['preferred']:6.2f} "
        f"[{availability_marker(availability['preferred']):7}] "
        f"→ {contributions['preferred']:5.2f}/10"
    )

    print(
        f"  Semantic:   "
        f"{effective['semantic']:6.2f} "
        f"[{availability_marker(availability['semantic']):7}] "
        f"→ {contributions['semantic']:5.2f}/30"
    )

    print(
        f"  Experience: "
        f"{effective['experience']:6.2f} "
        f"[{availability_marker(availability['experience']):7}] "
        f"→ {contributions['experience']:5.2f}/15"
    )

    route_changed = (
        current[
            "route"
        ]
        != fit[
            "route"
        ]
    )

    resume_changed = (
        current[
            "resume_name"
        ]
        != proposed[
            "resume_name"
        ]
    )

    print()

    print(
        f"Route changed:        "
        f"{'YES' if route_changed else 'NO'}"
    )

    print(
        f"Resume changed:       "
        f"{'YES' if resume_changed else 'NO'}"
    )

    print()

    print(
        f"URL: "
        f"{item['url']}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 100)

    print(
        "SCORE CALIBRATION V2 — "
        "READ-ONLY SIMULATION"
    )

    print("=" * 100)

    # ========================================================
    # LOAD RESUMES
    # ========================================================

    print()
    print(
        "Loading resumes..."
    )

    resumes = (
        load_all_resumes()
    )

    resume_cache = (
        prepare_resume_cache(
            resumes
        )
    )

    # ========================================================
    # LOAD COMPANIES
    # ========================================================

    companies = (
        load_companies()
    )

    comparisons = []

    skipped_assistance = 0

    skipped_blocked = 0

    # ========================================================
    # COMPANY LOOP
    # ========================================================

    for company_index, company in enumerate(
        companies,
        start=1,
    ):

        company_name = (
            company[
                "name"
            ]
        )

        board_token = (
            company[
                "board_token"
            ]
        )

        print()
        print(
            f"[{company_index}/"
            f"{len(companies)}] "
            f"{company_name}"
        )

        try:

            jobs = (
                get_jobs(
                    board_token
                )
            )

        except Exception as error:

            print(
                f"  FETCH FAILED: "
                f"{error}"
            )

            continue

        # ----------------------------------------------------
        # SAME FILTER PIPELINE AS MAIN.PY
        # ----------------------------------------------------

        role_jobs = (
            filter_by_role(
                jobs
            )
        )

        (
            full_time_jobs,
            _,
        ) = filter_by_employment_type(
            role_jobs
        )

        (
            us_jobs,
            _,
            _,
        ) = filter_by_location(
            full_time_jobs
        )

        (
            accepted_jobs,
            review_jobs,
            _,
        ) = filter_by_experience(
            us_jobs
        )

        pre_eligibility_jobs = (
            accepted_jobs
            + review_jobs
        )

        print(
            f"  Pre-eligibility jobs: "
            f"{len(pre_eligibility_jobs)}"
        )

        # ----------------------------------------------------
        # JOB LOOP
        # ----------------------------------------------------

        for result in (
            pre_eligibility_jobs
        ):

            job = (
                result[
                    "job"
                ]
            )

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

            job_text = (
                clean_job_content(
                    content
                )
            )

            eligibility = (
                evaluate_hard_eligibility(
                    job_title=(
                        title
                    ),

                    job_text=(
                        job_text
                    ),
                )
            )

            decision = (
                eligibility[
                    "decision"
                ]
            )

            if (
                decision
                == "NEEDS_ASSISTANCE"
            ):

                skipped_assistance += 1

                continue

            if (
                decision
                == "SKIP"
            ):

                skipped_blocked += 1

                continue

            # ------------------------------------------------
            # EXISTING MATCHER
            # ------------------------------------------------

            match_result = (
                rank_resumes(
                    job_title=(
                        title
                    ),

                    job_content=(
                        content
                    ),

                    job_text=(
                        job_text
                    ),

                    experience_mentions=(
                        result[
                            "experience_mentions"
                        ]
                    ),

                    resume_cache=(
                        resume_cache
                    ),
                )
            )

            rankings = (
                match_result[
                    "rankings"
                ]
            )

            if not rankings:

                continue

            current_candidate = (
                rankings[
                    0
                ]
            )

            (
                proposed_candidate,
                selection_score,
            ) = select_proposed_resume(
                rankings
            )

            proposed_fit = (
                calculate_proposed_fit(
                    proposed_candidate
                )
            )

            comparisons.append(
                {
                    "company": (
                        company_name
                    ),

                    "board_token": (
                        board_token
                    ),

                    "title": (
                        title
                    ),

                    "location": (
                        get_job_location(
                            job
                        )
                    ),

                    "url": (
                        job.get(
                            "absolute_url",
                            "",
                        )
                    ),

                    "current_candidate": (
                        current_candidate
                    ),

                    "proposed_candidate": (
                        proposed_candidate
                    ),

                    "selection_score": (
                        selection_score
                    ),

                    "proposed_fit": (
                        proposed_fit
                    ),
                }
            )

    # ========================================================
    # SORT BY PROPOSED SCORE
    # ========================================================

    comparisons.sort(
        key=lambda item: (
            item[
                "proposed_fit"
            ][
                "final_score"
            ]
        ),
        reverse=True,
    )

    # ========================================================
    # SUMMARY COUNTS
    # ========================================================

    current_manual = sum(
        1

        for item
        in comparisons

        if (
            item[
                "current_candidate"
            ][
                "route"
            ]
            == "MANUAL_PRIORITY"
        )
    )

    proposed_manual = sum(
        1

        for item
        in comparisons

        if (
            item[
                "proposed_fit"
            ][
                "route"
            ]
            == "MANUAL_PRIORITY"
        )
    )

    route_changes = [
        item

        for item
        in comparisons

        if (
            item[
                "current_candidate"
            ][
                "route"
            ]
            != item[
                "proposed_fit"
            ][
                "route"
            ]
        )
    ]

    resume_changes = [
        item

        for item
        in comparisons

        if (
            item[
                "current_candidate"
            ][
                "resume_name"
            ]
            != item[
                "proposed_candidate"
            ][
                "resume_name"
            ]
        )
    ]

    # ========================================================
    # COMPACT TABLE
    # ========================================================

    print()
    print()
    print("=" * 100)

    print(
        f"PROPOSED SCORE TABLE — "
        f"{len(comparisons)} JOBS"
    )

    print("=" * 100)

    print()

    print(
        "New     Old     Conf   "
        "New Route          "
        "Company / Job"
    )

    print(
        "-" * 100
    )

    for item in comparisons:

        current = (
            item[
                "current_candidate"
            ]
        )

        fit = (
            item[
                "proposed_fit"
            ]
        )

        print(
            f"{fit['final_score']:6.2f}  "
            f"{current['final_score']:6.2f}  "
            f"{fit['confidence']:4.0f}%   "
            f"{fit['route']:<18} "
            f"{item['company']} — "
            f"{item['title']}"
        )

    # ========================================================
    # ROUTE CHANGES
    # ========================================================

    print()
    print()
    print("=" * 100)

    print(
        f"ROUTE CHANGES — "
        f"{len(route_changes)}"
    )

    print("=" * 100)

    if not route_changes:

        print()
        print(
            "None"
        )

    for index, item in enumerate(
        route_changes,
        start=1,
    ):

        current = (
            item[
                "current_candidate"
            ]
        )

        fit = (
            item[
                "proposed_fit"
            ]
        )

        print()

        print(
            f"{index}. "
            f"{item['company']} — "
            f"{item['title']}"
        )

        print(
            f"   "
            f"{current['final_score']:.2f} "
            f"{current['route']}"
        )

        print(
            f"   → "
            f"{fit['final_score']:.2f} "
            f"{fit['route']}"
        )

        print(
            f"   Confidence: "
            f"{fit['confidence']:.0f}%"
        )

    # ========================================================
    # RESUME-SELECTION CHANGES
    # ========================================================

    print()
    print()
    print("=" * 100)

    print(
        f"RESUME SELECTION CHANGES — "
        f"{len(resume_changes)}"
    )

    print("=" * 100)

    if not resume_changes:

        print()
        print(
            "None"
        )

    for index, item in enumerate(
        resume_changes,
        start=1,
    ):

        current = (
            item[
                "current_candidate"
            ]
        )

        proposed = (
            item[
                "proposed_candidate"
            ]
        )

        print()

        print(
            f"{index}. "
            f"{item['company']} — "
            f"{item['title']}"
        )

        print(
            f"   Current:  "
            f"{pretty_name(current['resume_name'])}"
        )

        print(
            f"   Proposed: "
            f"{pretty_name(proposed['resume_name'])}"
        )

        print(
            f"   Selection score: "
            f"{item['selection_score']:.2f}"
        )

    # ========================================================
    # DETAILED EXPLANATIONS FOR CHANGED ROUTES
    # ========================================================

    print()
    print()
    print("=" * 100)

    print(
        "DETAILED CHANGED-ROUTE REVIEW"
    )

    print("=" * 100)

    if not route_changes:

        print()
        print(
            "No route changes to inspect."
        )

    else:

        for index, item in enumerate(
            sorted(
                route_changes,
                key=lambda x: (
                    x[
                        "proposed_fit"
                    ][
                        "final_score"
                    ]
                ),
                reverse=True,
            ),
            start=1,
        ):

            print_job_comparison(
                item,
                index,
            )

    # ========================================================
    # LOW-CONFIDENCE JOBS
    # ========================================================

    low_confidence = [
        item

        for item
        in comparisons

        if (
            item[
                "proposed_fit"
            ][
                "confidence"
            ]
            <= 45
        )
    ]

    print()
    print()
    print("=" * 100)

    print(
        f"LOW-EVIDENCE JOBS — "
        f"{len(low_confidence)}"
    )

    print("=" * 100)

    for index, item in enumerate(
        low_confidence,
        start=1,
    ):

        fit = (
            item[
                "proposed_fit"
            ]
        )

        print()

        print(
            f"{index}. "
            f"[{fit['final_score']:.2f}] "
            f"{item['company']} — "
            f"{item['title']}"
        )

        print(
            f"   Evidence confidence: "
            f"{fit['confidence']:.0f}%"
        )

        print(
            f"   Proposed route: "
            f"{fit['route']}"
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 100)

    print(
        "SCORE CALIBRATION V2 SUMMARY"
    )

    print("=" * 100)

    print(
        f"Jobs compared:              "
        f"{len(comparisons)}"
    )

    print(
        f"Assistance jobs excluded:   "
        f"{skipped_assistance}"
    )

    print(
        f"Hard-blocked jobs excluded: "
        f"{skipped_blocked}"
    )

    print()

    print(
        f"Current manual priority:    "
        f"{current_manual}"
    )

    print(
        f"Current agent apply:        "
        f"{len(comparisons) - current_manual}"
    )

    print()

    print(
        f"Proposed manual priority:   "
        f"{proposed_manual}"
    )

    print(
        f"Proposed agent apply:       "
        f"{len(comparisons) - proposed_manual}"
    )

    print()

    print(
        f"Route changes:              "
        f"{len(route_changes)}"
    )

    print(
        f"Resume-selection changes:   "
        f"{len(resume_changes)}"
    )

    print(
        f"Low-evidence jobs:          "
        f"{len(low_confidence)}"
    )

    print("=" * 100)


if __name__ == "__main__":

    main()
