import time

from src.greenhouse.client import (
    get_jobs,
)

from src.filtering.job_filter import (
    filter_by_role,
)

from src.filtering.location_filter import (
    filter_by_location,
)

from src.filtering.experience_filter import (
    filter_by_experience,
    clean_job_content,
)

from src.matching.resume_loader import (
    load_all_resumes,
)

from src.matching.matcher import (
    prepare_resume_cache,
    rank_resumes,
)

from src.database.repository import (
    JobRepository,
)


def pretty_name(
    name: str,
) -> str:

    return (
        name
        .replace("_", " ")
        .title()
    )


def main():

    total_start = (
        time.perf_counter()
    )

    board_token = "stripe"

    print()
    print("=" * 90)
    print(
        "GREENHOUSE JOB AGENT — "
        "SUPABASE PERSISTENCE RUN"
    )
    print("=" * 90)

    # ========================================================
    # FETCH
    # ========================================================

    fetch_start = (
        time.perf_counter()
    )

    print()
    print(
        f"Fetching jobs from: "
        f"{board_token}",
        flush=True,
    )

    jobs = get_jobs(
        board_token
    )

    fetch_time = (
        time.perf_counter()
        - fetch_start
    )

    if not jobs:

        print(
            "No jobs found."
        )

        return

    # ========================================================
    # ELIGIBILITY FILTERS
    # ========================================================

    filter_start = (
        time.perf_counter()
    )

    role_jobs = filter_by_role(
        jobs
    )

    (
        us_jobs,
        unknown_location_jobs,
        non_us_jobs,
    ) = filter_by_location(
        role_jobs
    )

    (
        accepted_jobs,
        review_jobs,
        rejected_jobs,
    ) = filter_by_experience(
        us_jobs
    )

    # 4-year review jobs remain eligible.
    eligible_jobs = (
        accepted_jobs
        + review_jobs
    )

    filter_time = (
        time.perf_counter()
        - filter_start
    )

    print()
    print("ELIGIBILITY")
    print("-" * 90)

    print(
        f"All jobs:                     "
        f"{len(jobs)}"
    )

    print(
        f"Target-role jobs:             "
        f"{len(role_jobs)}"
    )

    print(
        f"US-compatible jobs:           "
        f"{len(us_jobs)}"
    )

    print(
        f"Experience accepted:          "
        f"{len(accepted_jobs)}"
    )

    print(
        f"Experience review / eligible: "
        f"{len(review_jobs)}"
    )

    print(
        f"Experience rejected / SKIP:   "
        f"{len(rejected_jobs)}"
    )

    print(
        f"Unknown location:             "
        f"{len(unknown_location_jobs)}"
    )

    print(
        f"TOTAL TO SCORE:               "
        f"{len(eligible_jobs)}"
    )

    if not eligible_jobs:

        print(
            "No eligible jobs to score."
        )

        return

    # ========================================================
    # LOAD + CACHE RESUMES
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
    # CONNECT DATABASE
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
            board_token
        )
    )

    print(
        f"Agent run created: "
        f"{run_id[:8]}...",
        flush=True,
    )

    # ========================================================
    # SCORE + SAVE ALL JOBS
    # ========================================================

    scoring_start = (
        time.perf_counter()
    )

    scored_jobs = []

    print()
    print("=" * 90)
    print(
        "SCORING + SAVING ELIGIBLE JOBS"
    )
    print("=" * 90)

    for index, result in enumerate(
        eligible_jobs,
        start=1,
    ):

        job = result[
            "job"
        ]

        experience_mentions = (
            result[
                "experience_mentions"
            ]
        )

        title = job.get(
            "title",
            "Unknown title",
        )

        location = (
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

        content = job.get(
            "content",
            "",
        )

        job_text = (
            clean_job_content(
                content
            )
        )

        print(
            f"[{index:02}/"
            f"{len(eligible_jobs):02}] "
            f"{title}",
            flush=True,
        )

        job_start = (
            time.perf_counter()
        )

        match_result = (
            rank_resumes(
                job_title=title,

                job_content=content,

                job_text=job_text,

                experience_mentions=(
                    experience_mentions
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

        # ----------------------------------------------------
        # COMPANY
        # ----------------------------------------------------

        company = (
            job.get(
                "company_name"
            )
            or board_token.title()
        )

        # ----------------------------------------------------
        # SAVE JOB
        # ----------------------------------------------------

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
                    company
                ),

                title=(
                    title
                ),

                location=(
                    location
                ),

                url=job.get(
                    "absolute_url",
                    "",
                ),

                detected_profile=(
                    match_result[
                        "job_profile"
                    ]
                ),
            )
        )

        # ----------------------------------------------------
        # SAVE SCORE
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CREATE TRACKER ENTRY
        # ----------------------------------------------------

        application_id = (
            repository
            .ensure_application(
                job_id=(
                    database_job_id
                ),

                route=(
                    best[
                        "route"
                    ]
                ),
            )
        )

        job_time = (
            time.perf_counter()
            - job_start
        )

        print(
            f"     → "
            f"{pretty_name(best['resume_name'])}"
            f" | "
            f"{best['final_score']:.2f}"
            f" | "
            f"{best['route']}"
            f" | "
            f"saved"
            f" | "
            f"{job_time:.2f}s",
            flush=True,
        )

        scored_jobs.append(
            {
                "database_job_id": (
                    database_job_id
                ),

                "application_id": (
                    application_id
                ),

                "job_id": job.get(
                    "id"
                ),

                "title": (
                    title
                ),

                "company": (
                    company
                ),

                "location": (
                    location
                ),

                "url": job.get(
                    "absolute_url",
                    "",
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

                "resume_file": (
                    best[
                        "filename"
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
            }
        )

    scoring_time = (
        time.perf_counter()
        - scoring_start
    )

    # ========================================================
    # QUEUES
    # ========================================================

    manual_jobs = [
        job
        for job in scored_jobs
        if job["route"]
        == "MANUAL_PRIORITY"
    ]

    agent_jobs = [
        job
        for job in scored_jobs
        if job["route"]
        == "AGENT_APPLY"
    ]

    manual_jobs.sort(
        key=lambda job: (
            job["score"]
        ),
        reverse=True,
    )

    agent_jobs.sort(
        key=lambda job: (
            job["score"]
        ),
        reverse=True,
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
            len(jobs)
        ),

        target_role_jobs=(
            len(role_jobs)
        ),

        us_compatible_jobs=(
            len(us_jobs)
        ),

        jobs_eligible=(
            len(eligible_jobs)
        ),

        manual_priority_count=(
            len(manual_jobs)
        ),

        agent_apply_count=(
            len(agent_jobs)
        ),

        experience_rejected_count=(
            len(rejected_jobs)
        ),

        unknown_location_count=(
            len(
                unknown_location_jobs
            )
        ),

        fetch_seconds=(
            fetch_time
        ),

        filtering_seconds=(
            filter_time
        ),

        resume_cache_seconds=(
            resume_time
        ),

        scoring_seconds=(
            scoring_time
        ),

        total_seconds=(
            total_time
        ),
    )

    # ========================================================
    # OUTPUT QUEUES
    # ========================================================

    print()
    print()
    print("=" * 90)
    print(
        f"⭐ MANUAL PRIORITY — "
        f"{len(manual_jobs)} JOBS"
    )
    print("=" * 90)

    for index, job in enumerate(
        manual_jobs,
        start=1,
    ):

        print()

        print(
            f"{index}. "
            f"[{job['score']:.2f}] "
            f"{job['title']}"
        )

        print(
            f"   Company:  "
            f"{job['company']}"
        )

        print(
            f"   Location: "
            f"{job['location']}"
        )

        print(
            f"   Resume:   "
            f"{pretty_name(job['resume'])}"
        )

        print(
            f"   URL:      "
            f"{job['url']}"
        )

    print()
    print()
    print("=" * 90)
    print(
        f"🤖 AGENT APPLY — "
        f"{len(agent_jobs)} JOBS"
    )
    print("=" * 90)

    for index, job in enumerate(
        agent_jobs,
        start=1,
    ):

        print()

        print(
            f"{index}. "
            f"[{job['score']:.2f}] "
            f"{job['title']}"
        )

        print(
            f"   Company:  "
            f"{job['company']}"
        )

        print(
            f"   Location: "
            f"{job['location']}"
        )

        print(
            f"   Resume:   "
            f"{pretty_name(job['resume'])}"
        )

        print(
            f"   URL:      "
            f"{job['url']}"
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 90)
    print(
        "SUPABASE RUN SAVED SUCCESSFULLY"
    )
    print("=" * 90)

    print(
        f"Run ID:                     "
        f"{run_id}"
    )

    print(
        f"Jobs discovered:            "
        f"{len(jobs)}"
    )

    print(
        f"Jobs saved/tracked:         "
        f"{len(scored_jobs)}"
    )

    print(
        f"Manual priority:            "
        f"{len(manual_jobs)}"
    )

    print(
        f"Agent apply:                "
        f"{len(agent_jobs)}"
    )

    print(
        f"Total runtime:              "
        f"{total_time:.2f}s"
    )

    print()
    print(
        "You can now verify the rows "
        "inside Supabase."
    )

    print("=" * 90)


if __name__ == "__main__":
    main()
