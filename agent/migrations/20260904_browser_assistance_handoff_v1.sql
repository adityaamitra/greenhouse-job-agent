begin;

alter table public.assistance_requests
    add column if not exists source text
    not null default 'ELIGIBILITY';

alter table public.assistance_requests
    add column if not exists handoff jsonb
    not null default '{}'::jsonb;

alter table public.assistance_requests
    add column if not exists handoff_version integer
    not null default 0;

alter table public.assistance_requests
    add column if not exists updated_at timestamptz
    not null default now();

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'assistance_requests_source_check'
          and conrelid = 'public.assistance_requests'::regclass
    ) then
        alter table public.assistance_requests
            add constraint assistance_requests_source_check
            check (source in ('ELIGIBILITY', 'BROWSER'));
    end if;
end
$$;

create unique index if not exists
    assistance_requests_one_open_browser_per_application
on public.assistance_requests (
    owner_id,
    application_id
)
where
    source = 'BROWSER'
    and resolved = false;

commit;
