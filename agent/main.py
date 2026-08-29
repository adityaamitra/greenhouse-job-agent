import time

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
    MANUAL_MIN_CONFIDENCE,
    MANUAL_PRIORITY_THRESHOLD,
    prepare_resume_cache,
    rank_resumes,
)

from src.matching.profile_classifier import (
    classify_job_profile,
)

from src.database.repository import (
    JobRepository,
)

from src.config.company_loader import (
    load_companies,
)


# ============================================================
# DISPLAY CONFIGURATION
# ============================================================

SKILL_DISPLAY_LIMIT = 10

CALIBRATION_TOP_COUNT = 3
CALIBRATION_BOTTOM_COUNT = 3
CALIBRATION_THRESHOLD_COUNT = 5
CALIBRATION_WARNING_COUNT = 5
CALIBRATION_LOW_CONFIDENCE_COUNT = 5


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


def format_skills(
    skills: list[str],
    limit: int = SKILL_DISPLAY_LIMIT,
) -> str:

    if not skills:

        return (
            "None"
        )

    displayed = (
        skills[
            :limit
        ]
    )

    result = (
        ", ".join(
            displayed
        )
    )

    remaining = (
        len(
            skills
        )
        - len(
            displayed
        )
    )

    if remaining > 0:

        result += (
            f" (+{remaining} more)"
        )

    return (
        result
    )


def format_group(
    group: dict,
) -> str:

    skills = (
        group.get(
            "skills",
            [],
        )
    )

    min_matches = max(
        1,
        int(
            group.get(
                "min_matches",
                1,
            )
        ),
    )

    if skills:

        if min_matches <= 1:

            requirement_text = (
                "one of: "
                + ", ".join(
                    skills
                )
            )

        else:

            requirement_text = (
                f"at least {min_matches} of: "
                + ", ".join(
                    skills
                )
            )

        matching_options = (
            group.get(
                "matching_options",
                [],
            )
        )

        if matching_options:

            requirement_text += (
                " | matched: "
                + ", ".join(
                    matching_options
                )
            )

        return (
            requirement_text
        )

    text = (
        group.get(
            "text",
            "",
        )
    )

    if text:

        return (
            text
        )

    return (
        "Unknown grouped requirement"
    )


def get_component_availability(
    best: dict,
    component: str,
) -> bool:

    explanation = (
        best[
            "explanation"
        ]
    )

    availability = (
        explanation.get(
            "component_availability",
            {},
        )
    )

    return bool(
        availability.get(
            component,
            component == "semantic",
        )
    )


def format_component_score(
    best: dict,
    component: str,
    score_key: str,
) -> str:

    if not get_component_availability(
        best,
        component,
    ):

        return (
            "N/A"
        )

    return (
        f"{best[score_key]:.2f}"
    )


def print_fit_component(
    best: dict,
    *,
    label: str,
    component: str,
    score_key: str,
) -> None:

    explanation = (
        best[
            "explanation"
        ]
    )

    available = (
        get_component_availability(
            best,
            component,
        )
    )

    base_weight = (
        explanation[
            "weights"
        ].get(
            component,
            0.0,
        )
    )

    contribution = (
        explanation[
            "weighted_contributions"
        ].get(
            component,
            0.0,
        )
    )

    if available:

        score_text = (
            f"{best[score_key]:6.2f}"
        )

        status = (
            "REAL"
        )

    else:

        score_text = (
            "   N/A"
        )

        status = (
            "MISSING"
        )

    print(
        f"  {label:<12}"
        f"{score_text} "
        f"[{status:<7}] "
        f"→ {contribution:5.2f} pts "
        f"(base weight {base_weight:.0f})"
    )


# ============================================================
# SCORE EXPLAINABILITY
# ============================================================

def print_compact_score_breakdown(
    best: dict,
) -> None:

    explanation = (
        best[
            "explanation"
        ]
    )

    contributions = (
        explanation[
            "weighted_contributions"
        ]
    )

    availability = (
        explanation[
            "component_availability"
        ]
    )

    def compact_component(
        component: str,
        score_key: str,
    ) -> str:

        if not availability.get(
            component,
            False,
        ):

            return (
                "N/A"
            )

        return (
            f"{best[score_key]:.2f}"
        )

    print(
        f"       Selection {best['selection_score']:.2f}"
        f" | Fit {best['final_score']:.2f}"
        f" | Confidence {best['confidence']:.0f}%"
    )

    print(
        "       Fit → "
        f"Req {compact_component('required', 'required_score')} "
        f"({contributions['required']:.2f} pts)"
    )

    print(
        "             "
        f"Pref {compact_component('preferred', 'preferred_score')} "
        f"({contributions['preferred']:.2f} pts)"
    )

    print(
        "             "
        f"Sem {compact_component('semantic', 'semantic_score')} "
        f"({contributions['semantic']:.2f} pts)"
    )

    print(
        "             "
        f"Exp {compact_component('experience', 'experience_score')} "
        f"({contributions['experience']:.2f} pts)"
    )

    if not explanation[
        "manual_ready"
    ]:

        gate_failures = (
            explanation[
                "gate_failures"
            ]
        )

        if gate_failures:

            print(
                "       Manual gate → "
                + "; ".join(
                    gate_failures
                )
            )

    warnings = (
        explanation[
            "warnings"
        ]
    )

    if warnings:

        print(
            f"       ⚑ Calibration flags: "
            f"{len(warnings)}"
        )


def print_detailed_score_explanation(
    job: dict,
    index: int,
) -> None:

    best = (
        job[
            "match"
        ]
    )

    explanation = (
        best[
            "explanation"
        ]
    )

    print()
    print("-" * 100)

    print(
        f"{index}. "
        f"{job['company']} — "
        f"{job['title']}"
    )

    print("-" * 100)

    print(
        f"Job-fit score:       "
        f"{best['final_score']:.2f}"
    )

    print(
        f"Score band:          "
        f"{explanation['score_band']}"
    )

    print(
        f"Route:               "
        f"{best['route']}"
    )

    print(
        f"Threshold delta:     "
        f"{explanation['threshold_distance']:+.2f}"
    )

    print(
        f"Evidence confidence: "
        f"{best['confidence']:.0f}%"
    )

    print(
        f"Active evidence:     "
        f"{explanation['active_weight']:.0f}/"
        f"{explanation['total_weight']:.0f}"
    )

    print()

    print(
        f"Job profile:         "
        f"{pretty_name(job['profile'])}"
    )

    print(
        f"Selected resume:     "
        f"{pretty_name(best['resume_name'])}"
    )

    print(
        f"Resume select score: "
        f"{best['selection_score']:.2f}"
    )

    print(
        f"Role alignment:      "
        f"{best['role_score']:.2f} "
        f"(resume selection only)"
    )

    print()
    print(
        "Job-fit components "
        "(role alignment excluded):"
    )

    print_fit_component(
        best,
        label="Required:",
        component="required",
        score_key="required_score",
    )

    print_fit_component(
        best,
        label="Preferred:",
        component="preferred",
        score_key="preferred_score",
    )

    print_fit_component(
        best,
        label="Semantic:",
        component="semantic",
        score_key="semantic_score",
    )

    print_fit_component(
        best,
        label="Experience:",
        component="experience",
        score_key="experience_score",
    )

    print()
    print(
        f"  Renormalized total: "
        f"{best['final_score']:.2f}/100"
    )

    print()

    print(
        "Manual Priority gates:"
    )

    print(
        f"  Fit >= "
        f"{MANUAL_PRIORITY_THRESHOLD:.0f}:          "
        f"{'PASS' if explanation['score_gate'] else 'FAIL'}"
    )

    print(
        f"  Confidence >= "
        f"{MANUAL_MIN_CONFIDENCE:.0f}%: "
        f"{'PASS' if explanation['confidence_gate'] else 'FAIL'}"
    )

    print(
        f"  Required evidence: "
        f"{'PASS' if explanation['required_evidence_gate'] else 'FAIL'}"
    )

    if explanation[
        "gate_failures"
    ]:

        print(
            "  Held because: "
            + "; ".join(
                explanation[
                    "gate_failures"
                ]
            )
        )

    print()
    print(
        "Semantic details:"
    )

    print(
        f"  Raw similarity:     "
        f"{best['semantic_raw']:.2f}"
    )

    print(
        f"  Normalized score:   "
        f"{best['semantic_score']:.2f}"
    )

    print()

    required_units = (
        explanation[
            "required_units"
        ]
    )

    required_satisfied = (
        explanation[
            "required_satisfied"
        ]
    )

    print(
        f"Required requirements: "
        f"{required_satisfied}/"
        f"{required_units}"
    )

    print(
        f"  ✓ Matched standalone: "
        f"{format_skills(best['matched_required'])}"
    )

    print(
        f"  ✗ Missing standalone: "
        f"{format_skills(best['missing_required'])}"
    )

    required_groups = (
        best.get(
            "required_groups",
            [],
        )
    )

    if required_groups:

        print(
            "  Grouped requirements:"
        )

        for group in (
            required_groups[
                :8
            ]
        ):

            marker = (
                "✓"
                if group.get(
                    "satisfied",
                    False,
                )
                else "✗"
            )

            print(
                f"      {marker} "
                f"{format_group(group)}"
            )

    print()

    preferred_units = (
        explanation[
            "preferred_units"
        ]
    )

    preferred_satisfied = (
        explanation[
            "preferred_satisfied"
        ]
    )

    print(
        f"Preferred requirements: "
        f"{preferred_satisfied}/"
        f"{preferred_units}"
    )

    print(
        f"  ✓ Matched standalone: "
        f"{format_skills(best['matched_preferred'])}"
    )

    print(
        f"  ✗ Missing standalone: "
        f"{format_skills(best['missing_preferred'])}"
    )

    preferred_groups = (
        best.get(
            "preferred_groups",
            [],
        )
    )

    if preferred_groups:

        print(
            "  Grouped requirements:"
        )

        for group in (
            preferred_groups[
                :8
            ]
        ):

            marker = (
                "✓"
                if group.get(
                    "satisfied",
                    False,
                )
                else "✗"
            )

            print(
                f"      {marker} "
                f"{format_group(group)}"
            )

    print()

    required_years = (
        explanation[
            "required_minimum_years"
        ]
    )

    if required_years is None:

        required_years_text = (
            "Not extracted"
        )

    else:

        required_years_text = (
            str(
                required_years
            )
        )

    print(
        "Experience:"
    )

    print(
        f"  Applicant years:   "
        f"{explanation['applicant_years']}"
    )

    print(
        f"  Required minimum:  "
        f"{required_years_text}"
    )

    print()

    warnings = (
        explanation[
            "warnings"
        ]
    )

    if warnings:

        print(
            "Calibration flags:"
        )

        for warning in warnings:

            print(
                f"  ⚑ {warning}"
            )

    else:

        print(
            "Calibration flags: None"
        )

    print()
    print(
        f"URL: {job['url']}"
    )


def select_calibration_examples(
    scored_jobs: list[dict],
) -> list[dict]:

    if not scored_jobs:

        return []

    selected = []
    seen = set()

    def add_job(
        job: dict,
    ) -> None:

        key = (
            job[
                "board_token"
            ],
            str(
                job[
                    "job_id"
                ]
            ),
        )

        if key in seen:

            return

        seen.add(
            key
        )

        selected.append(
            job
        )

    by_score = sorted(
        scored_jobs,
        key=lambda item: (
            item[
                "score"
            ]
        ),
        reverse=True,
    )

    for job in (
        by_score[
            :CALIBRATION_TOP_COUNT
        ]
    ):

        add_job(
            job
        )

    by_threshold = sorted(
        scored_jobs,
        key=lambda item: abs(
            item[
                "score"
            ]
            - MANUAL_PRIORITY_THRESHOLD
        ),
    )

    for job in (
        by_threshold[
            :CALIBRATION_THRESHOLD_COUNT
        ]
    ):

        add_job(
            job
        )

    for job in (
        by_score[
            -CALIBRATION_BOTTOM_COUNT:
        ]
    ):

        add_job(
            job
        )

    warning_jobs = [
        job
        for job
        in scored_jobs
        if (
            job[
                "match"
            ][
                "explanation"
            ][
                "warnings"
            ]
        )
    ]

    warning_jobs.sort(
        key=lambda item: (
            len(
                item[
                    "match"
                ][
                    "explanation"
                ][
                    "warnings"
                ]
            ),
            item[
                "score"
            ],
        ),
        reverse=True,
    )

    for job in (
        warning_jobs[
            :CALIBRATION_WARNING_COUNT
        ]
    ):

        add_job(
            job
        )

    low_confidence_jobs = sorted(
        [
            job
            for job
            in scored_jobs
            if (
                job[
                    "match"
                ][
                    "confidence"
                ]
                < MANUAL_MIN_CONFIDENCE
            )
        ],
        key=lambda item: (
            item[
                "match"
            ][
                "confidence"
            ],
            -item[
                "score"
            ],
        ),
    )

    for job in (
        low_confidence_jobs[
            :CALIBRATION_LOW_CONFIDENCE_COUNT
        ]
    ):

        add_job(
            job
        )

    return (
        selected
    )


def calibration_component(
    best: dict,
    component: str,
    score_key: str,
) -> str:

    if not get_component_availability(
        best,
        component,
    ):

        return (
            "  N/A"
        )

    return (
        f"{best[score_key]:5.1f}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    total_start = (
        time.perf_counter()
    )

    print()
    print("=" * 90)

    print(
        "GREENHOUSE JOB AGENT — "
        "MULTI-COMPANY RUN"
    )

    print("=" * 90)

    # ========================================================
    # COMPANIES
    # ========================================================

    companies = (
        load_companies()
    )

    print()

    print(
        f"Enabled companies: "
        f"{len(companies)}"
    )

    for company in companies:

        print(
            f"  • {company['name']} "
            f"[{company['board_token']}]"
        )

    # ========================================================
    # RESUMES
    # ========================================================

    resume_start = (
        time.perf_counter()
    )

    print()

    print(
        "Loading master resumes...",
        flush=True,
    )

    resumes = (
        load_all_resumes()
    )

    resume_cache = (
        prepare_resume_cache(
            resumes
        )
    )

    resume_time = (
        time.perf_counter()
        - resume_start
    )

    # ========================================================
    # DATABASE
    # ========================================================

    print()

    print(
        "Connecting to Supabase...",
        flush=True,
    )

    repository = (
        JobRepository()
    )

    run_id = (
        repository
        .create_agent_run(
            "multi"
        )
    )

    print(
        f"Agent run created: "
        f"{run_id[:8]}...",
        flush=True,
    )

    # ========================================================
    # GLOBAL COUNTERS
    # ========================================================

    total_discovered = 0

    total_target_roles = 0

    total_employment_rejected = 0

    total_us_compatible = 0

    total_experience_rejected = 0

    total_unknown_location = 0

    total_assistance = 0

    total_hard_blocked = 0

    total_fetch_time = 0.0

    total_filter_time = 0.0

    total_scoring_time = 0.0

    scored_jobs = []

    assistance_jobs = []

    blocked_jobs = []

    company_summaries = []

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
        print()
        print("=" * 90)

        print(
            f"[{company_index}/"
            f"{len(companies)}] "
            f"{company_name}"
        )

        print("=" * 90)

        # ====================================================
        # FETCH
        # ====================================================

        fetch_start = (
            time.perf_counter()
        )

        try:

            jobs = (
                get_jobs(
                    board_token
                )
            )

        except Exception as error:

            print(
                f"FAILED TO FETCH "
                f"{company_name}"
            )

            print(
                f"Error: {error}"
            )

            company_summaries.append(
                {
                    "company": company_name,
                    "board_token": board_token,
                    "status": "FETCH_FAILED",
                    "discovered": 0,
                    "target_roles": 0,
                    "employment_filtered": 0,
                    "eligible": 0,
                    "assistance": 0,
                    "blocked": 0,
                    "manual": 0,
                    "agent": 0,
                }
            )

            continue

        fetch_time = (
            time.perf_counter()
            - fetch_start
        )

        total_fetch_time += (
            fetch_time
        )

        if not jobs:

            company_summaries.append(
                {
                    "company": company_name,
                    "board_token": board_token,
                    "status": "NO_JOBS",
                    "discovered": 0,
                    "target_roles": 0,
                    "employment_filtered": 0,
                    "eligible": 0,
                    "assistance": 0,
                    "blocked": 0,
                    "manual": 0,
                    "agent": 0,
                }
            )

            continue

        # ====================================================
        # BASIC FILTERS
        # ====================================================

        filter_start = (
            time.perf_counter()
        )

        role_jobs = (
            filter_by_role(
                jobs
            )
        )

        (
            full_time_jobs,
            employment_rejected_jobs,
        ) = filter_by_employment_type(
            role_jobs
        )

        (
            us_jobs,
            unknown_location_jobs,
            non_us_jobs,
        ) = filter_by_location(
            full_time_jobs
        )

        (
            accepted_jobs,
            review_jobs,
            experience_rejected_jobs,
        ) = filter_by_experience(
            us_jobs
        )

        pre_eligibility_jobs = (
            accepted_jobs
            + review_jobs
        )

        filter_time = (
            time.perf_counter()
            - filter_start
        )

        total_filter_time += (
            filter_time
        )

        # ====================================================
        # COUNTERS
        # ====================================================

        total_discovered += (
            len(
                jobs
            )
        )

        total_target_roles += (
            len(
                role_jobs
            )
        )

        total_employment_rejected += (
            len(
                employment_rejected_jobs
            )
        )

        total_us_compatible += (
            len(
                us_jobs
            )
        )

        total_experience_rejected += (
            len(
                experience_rejected_jobs
            )
        )

        total_unknown_location += (
            len(
                unknown_location_jobs
            )
        )

        # ====================================================
        # COMPANY FILTER SUMMARY
        # ====================================================

        print()

        print(
            f"Discovered:             "
            f"{len(jobs)}"
        )

        print(
            f"Target roles:           "
            f"{len(role_jobs)}"
        )

        print(
            f"Full-time candidates:   "
            f"{len(full_time_jobs)}"
        )

        print(
            f"Employment filtered:    "
            f"{len(employment_rejected_jobs)}"
        )

        print(
            f"US-compatible:          "
            f"{len(us_jobs)}"
        )

        print(
            f"Pre-eligibility jobs:   "
            f"{len(pre_eligibility_jobs)}"
        )

        print(
            f"Experience filtered:    "
            f"{len(experience_rejected_jobs)}"
        )

        if employment_rejected_jobs:

            print()
            print(
                "Employment-type exclusions:"
            )

            for item in (
                employment_rejected_jobs
            ):

                rejected_job = (
                    item[
                        "job"
                    ]
                )

                classification = (
                    item[
                        "classification"
                    ]
                )

                print(
                    f"  ✗ "
                    f"{rejected_job.get('title', 'Unknown')}"
                )

                print(
                    f"      Reason: "
                    f"{classification['reason']}"
                )

        # ====================================================
        # ELIGIBILITY + SCORING
        # ====================================================

        company_manual = 0

        company_agent = 0

        company_assistance = 0

        company_blocked = 0

        company_scored = 0

        scoring_start = (
            time.perf_counter()
        )

        for job_index, result in enumerate(
            pre_eligibility_jobs,
            start=1,
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

            location = (
                get_job_location(
                    job
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

            url = (
                job.get(
                    "absolute_url",
                    "",
                )
            )

            # ================================================
            # HARD ELIGIBILITY
            # ================================================

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

            # ================================================
            # NEEDS ASSISTANCE
            # ================================================

            if (
                decision
                == "NEEDS_ASSISTANCE"
            ):

                detected_profile = (
                    classify_job_profile(
                        title
                    )
                )

                database_job_id = (
                    repository
                    .upsert_job(
                        greenhouse_job_id=(
                            job.get(
                                "id"
                            )
                        ),

                        board_token=(
                            board_token
                        ),

                        company=(
                            company_name
                        ),

                        title=(
                            title
                        ),

                        location=(
                            location
                        ),

                        url=(
                            url
                        ),

                        detected_profile=(
                            detected_profile
                        ),
                    )
                )

                reason = (
                    eligibility[
                        "reason"
                    ]
                    or "Eligibility review required."
                )

                repository.ensure_assistance_application(
                    job_id=(
                        database_job_id
                    ),

                    reason=(
                        reason
                    ),
                )

                company_assistance += 1

                total_assistance += 1

                assistance_jobs.append(
                    {
                        "company": (
                            company_name
                        ),

                        "title": (
                            title
                        ),

                        "location": (
                            location
                        ),

                        "url": (
                            url
                        ),

                        "reason": (
                            reason
                        ),

                        "findings": (
                            eligibility[
                                "findings"
                            ]
                        ),
                    }
                )

                print(
                    f"  [{job_index:02}/"
                    f"{len(pre_eligibility_jobs):02}] "
                    f"{title}"
                )

                print(
                    "       → ⚠️ NEEDS_ASSISTANCE"
                )

                print(
                    f"       → {reason}"
                )

                continue

            # ================================================
            # HARD BLOCK
            # ================================================

            if (
                decision
                == "SKIP"
            ):

                company_blocked += 1

                total_hard_blocked += 1

                blocked_jobs.append(
                    {
                        "company": (
                            company_name
                        ),

                        "title": (
                            title
                        ),

                        "url": (
                            url
                        ),

                        "reason": (
                            eligibility[
                                "reason"
                            ]
                            or "Eligibility blocker"
                        ),
                    }
                )

                print(
                    f"  [{job_index:02}/"
                    f"{len(pre_eligibility_jobs):02}] "
                    f"{title}"
                )

                print(
                    "       → ⛔ SKIP"
                )

                continue

            # ================================================
            # SCORE
            # ================================================

            print(
                f"  [{job_index:02}/"
                f"{len(pre_eligibility_jobs):02}] "
                f"{title}",
                flush=True,
            )

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

            best = (
                match_result[
                    "rankings"
                ][0]
            )

            database_job_id = (
                repository
                .upsert_job(
                    greenhouse_job_id=(
                        job.get(
                            "id"
                        )
                    ),

                    board_token=(
                        board_token
                    ),

                    company=(
                        company_name
                    ),

                    title=(
                        title
                    ),

                    location=(
                        location
                    ),

                    url=(
                        url
                    ),

                    detected_profile=(
                        match_result[
                            "job_profile"
                        ]
                    ),
                )
            )

            repository.save_evaluation(
                run_id=(
                    run_id
                ),

                job_id=(
                    database_job_id
                ),

                best_match=(
                    best
                ),
            )

            repository.ensure_application(
                job_id=(
                    database_job_id
                ),

                route=(
                    best[
                        "route"
                    ]
                ),
            )

            company_scored += 1

            if (
                best[
                    "route"
                ]
                == "MANUAL_PRIORITY"
            ):

                company_manual += 1

            else:

                company_agent += 1

            scored_jobs.append(
                {
                    "company": (
                        company_name
                    ),

                    "board_token": (
                        board_token
                    ),

                    "job_id": (
                        job.get(
                            "id"
                        )
                    ),

                    "title": (
                        title
                    ),

                    "location": (
                        location
                    ),

                    "url": (
                        url
                    ),

                    "profile": (
                        match_result[
                            "job_profile"
                        ]
                    ),

                    "resume": (
                        best[
                            "resume_name"
                        ]
                    ),

                    "score": (
                        best[
                            "final_score"
                        ]
                    ),

                    "route": (
                        best[
                            "route"
                        ]
                    ),

                    # Preserve the complete explanation
                    # for calibration reporting.
                    "match": (
                        best
                    ),
                }
            )

            print(
                f"       → "
                f"{pretty_name(best['resume_name'])}"
                f" | "
                f"{best['final_score']:.2f}"
                f" | "
                f"{best['route']}",
                flush=True,
            )

            print_compact_score_breakdown(
                best
            )

        company_scoring_time = (
            time.perf_counter()
            - scoring_start
        )

        total_scoring_time += (
            company_scoring_time
        )

        # ====================================================
        # COMPANY SUMMARY
        # ====================================================

        company_summaries.append(
            {
                "company": (
                    company_name
                ),

                "board_token": (
                    board_token
                ),

                "status": (
                    "SUCCESS"
                ),

                "discovered": (
                    len(
                        jobs
                    )
                ),

                "target_roles": (
                    len(
                        role_jobs
                    )
                ),

                "employment_filtered": (
                    len(
                        employment_rejected_jobs
                    )
                ),

                "eligible": (
                    company_scored
                ),

                "assistance": (
                    company_assistance
                ),

                "blocked": (
                    company_blocked
                ),

                "manual": (
                    company_manual
                ),

                "agent": (
                    company_agent
                ),
            }
        )

    # ========================================================
    # ROUTE QUEUES
    # ========================================================

    manual_jobs = [
        job
        for job
        in scored_jobs
        if (
            job[
                "route"
            ]
            == "MANUAL_PRIORITY"
        )
    ]

    agent_jobs = [
        job
        for job
        in scored_jobs
        if (
            job[
                "route"
            ]
            == "AGENT_APPLY"
        )
    ]

    manual_jobs.sort(
        key=lambda item: (
            item[
                "score"
            ]
        ),
        reverse=True,
    )

    agent_jobs.sort(
        key=lambda item: (
            item[
                "score"
            ]
        ),
        reverse=True,
    )

    low_confidence_jobs = [
        job
        for job
        in scored_jobs
        if (
            job[
                "match"
            ][
                "confidence"
            ]
            < MANUAL_MIN_CONFIDENCE
        )
    ]

    low_confidence_jobs.sort(
        key=lambda item: (
            item[
                "match"
            ][
                "confidence"
            ],
            -item[
                "score"
            ],
        )
    )

    # ========================================================
    # COMPLETE DATABASE RUN
    # ========================================================

    total_time = (
        time.perf_counter()
        - total_start
    )

    repository.complete_agent_run(
        run_id=(
            run_id
        ),

        jobs_discovered=(
            total_discovered
        ),

        target_role_jobs=(
            total_target_roles
        ),

        us_compatible_jobs=(
            total_us_compatible
        ),

        jobs_eligible=(
            len(
                scored_jobs
            )
        ),

        manual_priority_count=(
            len(
                manual_jobs
            )
        ),

        agent_apply_count=(
            len(
                agent_jobs
            )
        ),

        experience_rejected_count=(
            total_experience_rejected
        ),

        unknown_location_count=(
            total_unknown_location
        ),

        fetch_seconds=(
            total_fetch_time
        ),

        filtering_seconds=(
            total_filter_time
        ),

        resume_cache_seconds=(
            resume_time
        ),

        scoring_seconds=(
            total_scoring_time
        ),

        total_seconds=(
            total_time
        ),
    )

    # ========================================================
    # COMPANY SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 90)
    print(
        "COMPANY SUMMARY"
    )
    print("=" * 90)

    for summary in (
        company_summaries
    ):

        print()

        print(
            f"{summary['company']} "
            f"[{summary['board_token']}]"
        )

        print(
            f"  Status:               "
            f"{summary['status']}"
        )

        print(
            f"  Discovered:           "
            f"{summary['discovered']}"
        )

        print(
            f"  Target roles:         "
            f"{summary['target_roles']}"
        )

        print(
            f"  Employment filtered:  "
            f"{summary['employment_filtered']}"
        )

        print(
            f"  Eligible/scored:      "
            f"{summary['eligible']}"
        )

        print(
            f"  Needs assistance:     "
            f"{summary['assistance']}"
        )

        print(
            f"  Hard blocked:         "
            f"{summary['blocked']}"
        )

        print(
            f"  Manual:               "
            f"{summary['manual']}"
        )

        print(
            f"  Agent:                "
            f"{summary['agent']}"
        )

    # ========================================================
    # ASSISTANCE QUEUE
    # ========================================================

    print()
    print()
    print("=" * 90)

    print(
        f"⚠️ NEEDS ASSISTANCE — "
        f"{len(assistance_jobs)}"
    )

    print("=" * 90)

    for index, job in enumerate(
        assistance_jobs,
        start=1,
    ):

        print()

        print(
            f"{index}. "
            f"{job['company']} — "
            f"{job['title']}"
        )

        print(
            f"   Reason: "
            f"{job['reason']}"
        )

        for finding in (
            job[
                "findings"
            ]
        ):

            print(
                f"   • "
                f"{finding['category']}"
            )

        print(
            f"   URL: "
            f"{job['url']}"
        )

    # ========================================================
    # MANUAL PRIORITY
    # ========================================================

    print()
    print()
    print("=" * 100)

    print(
        f"⭐ MANUAL PRIORITY — "
        f"{len(manual_jobs)}"
    )

    print("=" * 100)

    for index, job in enumerate(
        manual_jobs,
        start=1,
    ):

        best = (
            job[
                "match"
            ]
        )

        print()

        print(
            f"{index}. "
            f"[Fit {job['score']:.2f} | "
            f"Conf {best['confidence']:.0f}%] "
            f"{job['company']} — "
            f"{job['title']}"
        )

        print(
            f"   Resume: "
            f"{pretty_name(job['resume'])} "
            f"(selection {best['selection_score']:.2f})"
        )

        print(
            f"   URL: "
            f"{job['url']}"
        )

    # ========================================================
    # AGENT APPLY
    # ========================================================

    print()
    print()
    print("=" * 100)

    print(
        f"🤖 AGENT APPLY — "
        f"{len(agent_jobs)}"
    )

    print("=" * 100)

    for index, job in enumerate(
        agent_jobs,
        start=1,
    ):

        best = (
            job[
                "match"
            ]
        )

        print()

        print(
            f"{index}. "
            f"[Fit {job['score']:.2f} | "
            f"Conf {best['confidence']:.0f}%] "
            f"{job['company']} — "
            f"{job['title']}"
        )

        print(
            f"   Resume: "
            f"{pretty_name(job['resume'])} "
            f"(selection {best['selection_score']:.2f})"
        )

        if (
            best[
                "explanation"
            ][
                "gate_failures"
            ]
        ):

            print(
                "   Manual gate: "
                + "; ".join(
                    best[
                        "explanation"
                    ][
                        "gate_failures"
                    ]
                )
            )

        print(
            f"   URL: "
            f"{job['url']}"
        )

    # ========================================================
    # SCORE CALIBRATION TABLE
    # ========================================================

    print()
    print()
    print("=" * 120)

    print(
        f"📊 SCORE CALIBRATION TABLE — "
        f"{len(scored_jobs)} JOBS"
    )

    print("=" * 120)

    print()

    print(
        "Fit     Sel     Conf   Req    Pref   Sem    Exp    "
        "Route              Job"
    )

    print(
        "-" * 120
    )

    calibration_table_jobs = sorted(
        scored_jobs,
        key=lambda item: (
            item[
                "score"
            ]
        ),
        reverse=True,
    )

    for job in (
        calibration_table_jobs
    ):

        best = (
            job[
                "match"
            ]
        )

        print(
            f"{best['final_score']:6.2f}  "
            f"{best['selection_score']:6.2f}  "
            f"{best['confidence']:4.0f}%   "
            f"{calibration_component(best, 'required', 'required_score'):>5}  "
            f"{calibration_component(best, 'preferred', 'preferred_score'):>5}  "
            f"{calibration_component(best, 'semantic', 'semantic_score'):>5}  "
            f"{calibration_component(best, 'experience', 'experience_score'):>5}  "
            f"{best['route']:<18} "
            f"{job['company']} — "
            f"{job['title']}"
        )

    # ========================================================
    # EVIDENCE SUMMARY
    # ========================================================

    required_evidence_count = sum(
        1
        for job
        in scored_jobs
        if (
            job[
                "match"
            ][
                "explanation"
            ][
                "required_evidence_gate"
            ]
        )
    )

    fit_above_threshold_count = sum(
        1
        for job
        in scored_jobs
        if (
            job[
                "score"
            ]
            >= MANUAL_PRIORITY_THRESHOLD
        )
    )

    fit_above_but_held = [
        job
        for job
        in scored_jobs
        if (
            job[
                "score"
            ]
            >= MANUAL_PRIORITY_THRESHOLD
            and job[
                "route"
            ]
            != "MANUAL_PRIORITY"
        )
    ]

    print()
    print()
    print("=" * 100)
    print(
        "EVIDENCE / ROUTING SUMMARY"
    )
    print("=" * 100)

    print(
        f"Scored jobs:                   "
        f"{len(scored_jobs)}"
    )

    print(
        f"Jobs with required evidence:   "
        f"{required_evidence_count}"
    )

    print(
        f"Confidence >= "
        f"{MANUAL_MIN_CONFIDENCE:.0f}%:           "
        f"{len(scored_jobs) - len(low_confidence_jobs)}"
    )

    print(
        f"Confidence < "
        f"{MANUAL_MIN_CONFIDENCE:.0f}%:            "
        f"{len(low_confidence_jobs)}"
    )

    print(
        f"Fit >= "
        f"{MANUAL_PRIORITY_THRESHOLD:.0f}:                    "
        f"{fit_above_threshold_count}"
    )

    print(
        f"Fit >= "
        f"{MANUAL_PRIORITY_THRESHOLD:.0f} but evidence-held:  "
        f"{len(fit_above_but_held)}"
    )

    # ========================================================
    # LOW-CONFIDENCE REVIEW
    # ========================================================

    print()
    print()
    print("=" * 100)

    print(
        f"⚠️ LOW-CONFIDENCE SCORED JOBS "
        f"(<{MANUAL_MIN_CONFIDENCE:.0f}%) — "
        f"{len(low_confidence_jobs)}"
    )

    print("=" * 100)

    if not low_confidence_jobs:

        print()
        print(
            "None"
        )

    for index, job in enumerate(
        low_confidence_jobs,
        start=1,
    ):

        best = (
            job[
                "match"
            ]
        )

        availability = (
            best[
                "explanation"
            ][
                "component_availability"
            ]
        )

        missing_components = [
            component
            for component
            in (
                "required",
                "preferred",
                "experience",
            )
            if not availability.get(
                component,
                False,
            )
        ]

        print()

        print(
            f"{index}. "
            f"[Fit {best['final_score']:.2f} | "
            f"Conf {best['confidence']:.0f}%] "
            f"{job['company']} — "
            f"{job['title']}"
        )

        print(
            f"   Missing evidence: "
            f"{', '.join(missing_components) if missing_components else 'None'}"
        )

        print(
            f"   Route: "
            f"{best['route']}"
        )

    # ========================================================
    # DETAILED CALIBRATION REVIEW
    # ========================================================

    calibration_examples = (
        select_calibration_examples(
            scored_jobs
        )
    )

    print()
    print()
    print("=" * 100)

    print(
        f"🔎 DETAILED SCORE CALIBRATION REVIEW — "
        f"{len(calibration_examples)} JOBS"
    )

    print("=" * 100)

    print()

    print(
        "Selected automatically from:"
    )

    print(
        "  • highest scores"
    )

    print(
        "  • lowest scores"
    )

    print(
        f"  • jobs closest to the "
        f"{MANUAL_PRIORITY_THRESHOLD:.0f} threshold"
    )

    print(
        "  • jobs with calibration warnings"
    )

    print(
        f"  • lowest evidence confidence"
    )

    for index, job in enumerate(
        calibration_examples,
        start=1,
    ):

        print_detailed_score_explanation(
            job,
            index,
        )

    # ========================================================
    # HARD BLOCKED
    # ========================================================

    if blocked_jobs:

        print()
        print()
        print("=" * 90)

        print(
            f"⛔ HARD BLOCKED — "
            f"{len(blocked_jobs)}"
        )

        print("=" * 90)

        for index, job in enumerate(
            blocked_jobs,
            start=1,
        ):

            print()

            print(
                f"{index}. "
                f"{job['company']} — "
                f"{job['title']}"
            )

            print(
                f"   Reason: "
                f"{job['reason']}"
            )

            print(
                f"   URL: "
                f"{job['url']}"
            )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 90)
    print(
        "MULTI-COMPANY RUN COMPLETE"
    )
    print("=" * 90)

    print(
        f"Companies scanned:           "
        f"{len(companies)}"
    )

    print(
        f"Jobs discovered:             "
        f"{total_discovered}"
    )

    print(
        f"Target-role jobs:            "
        f"{total_target_roles}"
    )

    print(
        f"Employment filtered:         "
        f"{total_employment_rejected}"
    )

    print(
        f"US-compatible jobs:          "
        f"{total_us_compatible}"
    )

    print(
        f"Jobs eligible/scored:        "
        f"{len(scored_jobs)}"
    )

    print(
        f"Needs assistance:            "
        f"{total_assistance}"
    )

    print(
        f"Hard blocked:                "
        f"{total_hard_blocked}"
    )

    print(
        f"Manual priority:             "
        f"{len(manual_jobs)}"
    )

    print(
        f"Agent apply:                 "
        f"{len(agent_jobs)}"
    )

    print(
        f"Experience filtered:         "
        f"{total_experience_rejected}"
    )

    print(
        f"Unknown location:            "
        f"{total_unknown_location}"
    )

    print(
        f"Low-confidence scored jobs:  "
        f"{len(low_confidence_jobs)}"
    )

    print(
        f"Total runtime:               "
        f"{total_time:.2f}s"
    )

    print("=" * 90)


if __name__ == "__main__":

    main()

