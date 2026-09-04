begin;

create table if not exists public.browser_queue_runs (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    run_key text not null,
    runner_version integer not null default 1,
    status text not null default 'COMPLETED',
    persist_handoffs boolean not null default false,
    board_token_filter text,
    queue_order text not null default 'oldest',
    queue_limit integer not null default 1,
    include_in_progress boolean not null default false,
    started_at timestamptz,
    completed_at timestamptz,
    total_seconds double precision not null default 0,
    selected_count integer not null default 0,
    completed_count integer not null default 0,
    needs_assistance_count integer not null default 0,
    ready_no_submit_count integer not null default 0,
    blocked_count integer not null default 0,
    error_count integer not null default 0,
    challenge_count integer not null default 0,
    browser_modified_count integer not null default 0,
    submitted_count integer not null default 0,
    submit_clicked_by_agent boolean not null default false,
    application_submitted boolean not null default false,
    results jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint browser_queue_runs_owner_run_unique
        unique (owner_id, run_key),

    constraint browser_queue_runs_status_check
        check (status in ('COMPLETED')),

    constraint browser_queue_runs_order_check
        check (queue_order in ('oldest', 'newest', 'fit')),

    constraint browser_queue_runs_limit_check
        check (queue_limit between 1 and 50),

    constraint browser_queue_runs_nonnegative_counts_check
        check (
            selected_count >= 0
            and completed_count >= 0
            and needs_assistance_count >= 0
            and ready_no_submit_count >= 0
            and blocked_count >= 0
            and error_count >= 0
            and challenge_count >= 0
            and browser_modified_count >= 0
            and submitted_count >= 0
            and total_seconds >= 0
        ),

    constraint browser_queue_runs_no_submission_check
        check (
            submitted_count = 0
            and submit_clicked_by_agent = false
            and application_submitted = false
        )
);

create index if not exists
    browser_queue_runs_owner_started_idx
on public.browser_queue_runs (
    owner_id,
    started_at desc
);

alter table public.browser_queue_runs
    enable row level security;

drop policy if exists
    browser_queue_runs_select_own
on public.browser_queue_runs;

create policy browser_queue_runs_select_own
on public.browser_queue_runs
for select
to authenticated
using (
    auth.uid() = owner_id
);

drop policy if exists
    browser_queue_runs_insert_own
on public.browser_queue_runs;

create policy browser_queue_runs_insert_own
on public.browser_queue_runs
for insert
to authenticated
with check (
    auth.uid() = owner_id
);

drop policy if exists
    browser_queue_runs_update_own
on public.browser_queue_runs;

create policy browser_queue_runs_update_own
on public.browser_queue_runs
for update
to authenticated
using (
    auth.uid() = owner_id
)
with check (
    auth.uid() = owner_id
);

commit;
