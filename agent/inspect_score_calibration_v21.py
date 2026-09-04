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
# SCORE CALIBRATION V2.1
# ============================================================
#
# READ-ONLY SIMULATION.
#
# No Supabase writes.
# No application updates.
# No production routing changes.
#
#
# FINAL JOB-FIT WEIGHTS
#
# Required      45
# Preferred     10
# Semantic      30
# Experience    15
#
#
# CRITICAL CHANGE FROM V2
#
# Missing evidence is NOT scored as 50.
#
# Instead:
#
#   1. Missing component is excluded.
#   2. Remaining component weights are renormalized.
#   3. Evidence coverage is reported separately as confidence.
#
#
# Example:
#
# Required     100 / 45
# Preferred    missing
# Semantic      70 / 30
# Experience   100 / 15
#
# Fit:
#
#   (100*45 + 70*30 + 100*15)
#   --------------------------------
#              45 + 30 + 15
#
# Confidence:
#
#   45 + 30 + 15 = 90%
#
# ============================================================


FIT_WEIGHTS = {
    "required": 45.0,
    "preferred": 10.0,
    "semantic": 30.0,
    "experience": 15.0,
}


# ============================================================
# MANUAL-PRIORITY EVIDENCE GATE
# ============================================================
#
# Manual priority requires:
#
#   fit >= 85
#
# AND
#
#   confidence >= 75
#
# AND
#
#   real required-skill evidence
#
#
# Why 75?
#
# Required + Semantic:
#
#   45 + 30 = 75
#
# Therefore a job cannot become Manual Priority purely from
# semantic similarity, optional skills, or unknown fields.
#
# ============================================================

MANUAL_MIN_CONFIDENCE = (
    75.0
)


# ============================================================
# RESUME SELECTION
# ============================================================
#
# Role alignment is useful for selecting WHICH resume.
#
# It is not part of the final job-fit score.
#
#
# Resume selection:
#
# Role        55
# Semantic    25
# Required    20
#
#
# Missing required extraction is also excluded and weights are
# renormalized.
# ============================================================

RESUME_SELECTION_WEIGHTS = {
    "role": 55.0,
    "semantic": 25.0,
    "required": 20.0,
}


# ============================================================
# DISPLAY HELPERS
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


# ============================================================
# EVIDENCE AVAILABILITY
# ============================================================

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

    # Every ranked job has semantic evidence because
    # rank_resumes() calculated a semantic score from the JD.
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


# ============================================================
# DYNAMIC WEIGHTED AVERAGE
# ============================================================

def calculate_dynamic_weighted_score(
    *,
    scores: dict,
    availability: dict,
    weights: dict,
) -> dict:
    """
    Calculate an evidence-normalized weighted score.

    Missing components contribute NO score and NO denominator.

    Example:

        required = 100 @ 45
        preferred = missing
        semantic = 70 @ 30
        experience = 100 @ 15

    becomes:

        weighted_sum =
            100*45 +
             70*30 +
            100*15

        active_weight =
            45 + 30 + 15

        final =
            weighted_sum / active_weight
    """

    weighted_sum = (
        0.0
    )

    active_weight = (
        0.0
    )

    component_details = {}

    for component, weight in (
        weights.items()
    ):

        available = bool(
            availability.get(
                component,
                False,
            )
        )

        raw_score = (
            float(
                scores.get(
                    component,
                    0.0,
                )
            )
        )

        if available:

            weighted_value = (
                raw_score
                * weight
            )

            weighted_sum += (
                weighted_value
            )

            active_weight += (
                weight
            )

        else:

            weighted_value = (
                None
            )

        component_details[
            component
        ] = {
            "score": (
                raw_score
                if available
                else None
            ),

            "available": (
                available
            ),

            "weight": (
                weight
            ),

            "weighted_value": (
                weighted_value
            ),
        }

    if active_weight <= 0:

        final_score = (
            0.0
        )

    else:

        final_score = (
            weighted_sum
            / active_weight
        )

    total_possible_weight = (
        sum(
            weights.values()
        )
    )

    if total_possible_weight <= 0:

        confidence = (
            0.0
        )

    else:

        confidence = (
            active_weight
            / total_possible_weight
            * 100.0
        )

    return {
        "score": round(
            final_score,
            2,
        ),

        "confidence": round(
            confidence,
            2,
        ),

        "active_weight": round(
            active_weight,
            2,
        ),

        "weighted_sum": round(
            weighted_sum,
            2,
        ),

        "components": (
            component_details
        ),
    }


# ============================================================
# RESUME SELECTION
# ============================================================

def calculate_resume_selection_score(
    candidate: dict,
) -> float:

    availability = (
        get_component_availability(
            candidate
        )
    )

    selection_availability = {
        "role": (
            True
        ),

        "semantic": (
            True
        ),

        "required": (
            availability[
                "required"
            ]
        ),
    }

    selection_scores = {
        "role": (
            candidate[
                "role_score"
            ]
        ),

        "semantic": (
            candidate[
                "semantic_score"
            ]
        ),

        "required": (
            candidate[
                "required_score"
            ]
        ),
    }

    result = (
        calculate_dynamic_weighted_score(
            scores=(
                selection_scores
            ),

            availability=(
                selection_availability
            ),

            weights=(
                RESUME_SELECTION_WEIGHTS
            ),
        )
    )

    return (
        result[
            "score"
        ]
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
# FINAL JOB-FIT SCORE
# ============================================================

def calculate_proposed_fit(
    candidate: dict,
) -> dict:

    availability = (
        get_component_availability(
            candidate
        )
    )

    scores = {
        "required": (
            candidate[
                "required_score"
            ]
        ),

        "preferred": (
            candidate[
                "preferred_score"
            ]
        ),

        "semantic": (
            candidate[
                "semantic_score"
            ]
        ),

        "experience": (
            candidate[
                "experience_score"
            ]
        ),
    }

    score_result = (
        calculate_dynamic_weighted_score(
            scores=(
                scores
            ),

            availability=(
                availability
            ),

            weights=(
                FIT_WEIGHTS
            ),
        )
    )

    final_score = (
        score_result[
            "score"
        ]
    )

    confidence = (
        score_result[
            "confidence"
        ]
    )

    # ========================================================
    # MANUAL PRIORITY GATES
    # ========================================================

    score_gate = (
        final_score
        >= MANUAL_PRIORITY_THRESHOLD
    )

    confidence_gate = (
        confidence
        >= MANUAL_MIN_CONFIDENCE
    )

    required_evidence_gate = (
        availability[
            "required"
        ]
    )

    manual_ready = (
        score_gate
        and confidence_gate
        and required_evidence_gate
    )

    if manual_ready:

        route = (
            "MANUAL_PRIORITY"
        )

    else:

        route = (
            "AGENT_APPLY"
        )

    gate_failures = []

    if not score_gate:

        gate_failures.append(
            (
                f"fit below "
                f"{MANUAL_PRIORITY_THRESHOLD:.0f}"
            )
        )

    if not confidence_gate:

        gate_failures.append(
            (
                f"confidence below "
                f"{MANUAL_MIN_CONFIDENCE:.0f}%"
            )
        )

    if not required_evidence_gate:

        gate_failures.append(
            "no required-skill evidence"
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

        "components": (
            score_result[
                "components"
            ]
        ),

        "active_weight": (
            score_result[
                "active_weight"
            ]
        ),

        "weighted_sum": (
            score_result[
                "weighted_sum"
            ]
        ),

        "score_gate": (
            score_gate
        ),

        "confidence_gate": (
            confidence_gate
        ),

        "required_evidence_gate": (
            required_evidence_gate
        ),

        "manual_ready": (
            manual_ready
        ),

        "gate_failures": (
            gate_failures
        ),
    }


# ============================================================
# COMPONENT DISPLAY
# ============================================================

def print_component(
    name: str,
    component: dict,
) -> None:

    if not component[
        "available"
    ]:

        print(
            f"  {name:<11}"
            f"N/A     "
            f"[MISSING] "
            f"weight {component['weight']:.0f} "
            f"→ excluded"
        )

        return

    print(
        f"  {name:<11}"
        f"{component['score']:6.2f} "
        f"[REAL   ] "
        f"weight {component['weight']:.0f}"
    )


# ============================================================
# DETAILED JOB DISPLAY
# ============================================================

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

    print()
    print(
        "-" * 100
    )

    print(
        f"{index}. "
        f"{item['company']} — "
        f"{item['title']}"
    )

    print(
        "-" * 100
    )

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
        f"Evidence-fit score:   "
        f"{fit['final_score']:.2f}"
    )

    print(
        f"Evidence confidence:  "
        f"{fit['confidence']:.0f}%"
    )

    print(
        f"Proposed route:       "
        f"{fit['route']}"
    )

    print()

    print(
        "Evidence components:"
    )

    components = (
        fit[
            "components"
        ]
    )

    print_component(
        "Required:",
        components[
            "required"
        ],
    )

    print_component(
        "Preferred:",
        components[
            "preferred"
        ],
    )

    print_component(
        "Semantic:",
        components[
            "semantic"
        ],
    )

    print_component(
        "Experience:",
        components[
            "experience"
        ],
    )

    print()

    print(
        f"Active weight:        "
        f"{fit['active_weight']:.0f}/100"
    )

    print()

    print(
        "Manual gates:"
    )

    print(
        f"  Fit >= "
        f"{MANUAL_PRIORITY_THRESHOLD:.0f}:     "
        f"{'PASS' if fit['score_gate'] else 'FAIL'}"
    )

    print(
        f"  Confidence >= "
        f"{MANUAL_MIN_CONFIDENCE:.0f}%: "
        f"{'PASS' if fit['confidence_gate'] else 'FAIL'}"
    )

    print(
        f"  Required evidence: "
        f"{'PASS' if fit['required_evidence_gate'] else 'FAIL'}"
    )

    if fit[
        "gate_failures"
    ]:

        print()

        print(
            "Held from Manual because: "
            + "; ".join(
                fit[
                    "gate_failures"
                ]
            )
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
    print(
        "=" * 100
    )

    print(
        "SCORE CALIBRATION V2.1 — "
        "EVIDENCE-NORMALIZED READ-ONLY SIMULATION"
    )

    print(
        "=" * 100
    )

    # ========================================================
    # RESUMES
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
    # COMPANIES
    # ========================================================

    companies = (
        load_companies()
    )

    comparisons = []

    skipped_assistance = (
        0
    )

    skipped_blocked = (
        0
    )

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
        # SAME FILTER PIPELINE
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

                skipped_assistance += (
                    1
                )

                continue

            if (
                decision
                == "SKIP"
            ):

                skipped_blocked += (
                    1
                )

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
    # SORT
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
    # COUNTS
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

    fit_above_threshold = sum(
        1
        for item
        in comparisons
        if (
            item[
                "proposed_fit"
            ][
                "final_score"
            ]
            >= MANUAL_PRIORITY_THRESHOLD
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

    evidence_held = [
        item
        for item
        in comparisons
        if (
            item[
                "proposed_fit"
            ][
                "final_score"
            ]
            >= MANUAL_PRIORITY_THRESHOLD

            and item[
                "proposed_fit"
            ][
                "route"
            ]
            != "MANUAL_PRIORITY"
        )
    ]

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
            < MANUAL_MIN_CONFIDENCE
        )
    ]

    # ========================================================
    # SCORE TABLE
    # ========================================================

    print()
    print()
    print(
        "=" * 100
    )

    print(
        f"EVIDENCE-NORMALIZED SCORE TABLE — "
        f"{len(comparisons)} JOBS"
    )

    print(
        "=" * 100
    )

    print()

    print(
        "Fit     Old     Conf   Req?  "
        "New Route          "
        "Company / Job"
    )

    print(
        "-" * 100
    )

    for item in (
        comparisons
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

        required_marker = (
            "YES"
            if fit[
                "required_evidence_gate"
            ]
            else "NO "
        )

        print(
            f"{fit['final_score']:6.2f}  "
            f"{current['final_score']:6.2f}  "
            f"{fit['confidence']:4.0f}%   "
            f"{required_marker}   "
            f"{fit['route']:<18} "
            f"{item['company']} — "
            f"{item['title']}"
        )

    # ========================================================
    # FIT >= 85 BUT HELD BY EVIDENCE
    # ========================================================

    print()
    print()
    print(
        "=" * 100
    )

    print(
        f"FIT >= "
        f"{MANUAL_PRIORITY_THRESHOLD:.0f} "
        f"BUT HELD BY EVIDENCE GATE — "
        f"{len(evidence_held)}"
    )

    print(
        "=" * 100
    )

    if not evidence_held:

        print()
        print(
            "None"
        )

    for index, item in enumerate(
        evidence_held,
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
            f"   Confidence: "
            f"{fit['confidence']:.0f}%"
        )

        print(
            f"   Required evidence: "
            f"{fit['required_evidence_gate']}"
        )

        print(
            f"   Held because: "
            + "; ".join(
                fit[
                    "gate_failures"
                ]
            )
        )

    # ========================================================
    # ROUTE CHANGES
    # ========================================================

    print()
    print()
    print(
        "=" * 100
    )

    print(
        f"ROUTE CHANGES — "
        f"{len(route_changes)}"
    )

    print(
        "=" * 100
    )

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
    # RESUME CHANGES
    # ========================================================

    print()
    print()
    print(
        "=" * 100
    )

    print(
        f"RESUME SELECTION CHANGES — "
        f"{len(resume_changes)}"
    )

    print(
        "=" * 100
    )

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
    # DETAILED REVIEW
    # ========================================================

    review_jobs = []

    # Changed routes.
    review_jobs.extend(
        route_changes
    )

    # Add evidence-held jobs.
    for item in evidence_held:

        if item not in review_jobs:

            review_jobs.append(
                item
            )

    # Add top five jobs.
    for item in comparisons[
        :5
    ]:

        if item not in review_jobs:

            review_jobs.append(
                item
            )

    print()
    print()
    print(
        "=" * 100
    )

    print(
        f"DETAILED REVIEW — "
        f"{len(review_jobs)} JOBS"
    )

    print(
        "=" * 100
    )

    for index, item in enumerate(
        review_jobs,
        start=1,
    ):

        print_job_comparison(
            item,
            index,
        )

    # ========================================================
    # LOW CONFIDENCE
    # ========================================================

    print()
    print()
    print(
        "=" * 100
    )

    print(
        f"LOW-CONFIDENCE JOBS "
        f"(<{MANUAL_MIN_CONFIDENCE:.0f}%) — "
        f"{len(low_confidence)}"
    )

    print(
        "=" * 100
    )

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
            f"   Confidence: "
            f"{fit['confidence']:.0f}%"
        )

        print(
            f"   Required evidence: "
            f"{fit['required_evidence_gate']}"
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print()
    print(
        "=" * 100
    )

    print(
        "SCORE CALIBRATION V2.1 SUMMARY"
    )

    print(
        "=" * 100
    )

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
        f"Fit >= "
        f"{MANUAL_PRIORITY_THRESHOLD:.0f}:               "
        f"{fit_above_threshold}"
    )

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
        f"Held by evidence gate:      "
        f"{len(evidence_held)}"
    )

    print(
        f"Route changes:              "
        f"{len(route_changes)}"
    )

    print(
        f"Resume-selection changes:   "
        f"{len(resume_changes)}"
    )

    print(
        f"Confidence < "
        f"{MANUAL_MIN_CONFIDENCE:.0f}%:          "
        f"{len(low_confidence)}"
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":

    main()
