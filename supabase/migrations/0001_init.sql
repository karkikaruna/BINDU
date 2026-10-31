-- BINDU cloud sync schema. Every table is owned by one user and protected by row-level security:
-- a signed-in user can only read and write rows whose user_id is their own auth.uid().
-- Run in the Supabase SQL editor (or `supabase db push`). Never ship the service-role key in the app.

create table if not exists public.profiles (
  user_id        uuid primary key references auth.users (id) on delete cascade,
  display_name   text not null default '' check (char_length(display_name) <= 40),
  language       text not null default 'English' check (language in ('English', 'नेपाली')),
  nepali_level   text not null default 'Beginner' check (nepali_level in ('Beginner', 'Intermediate', 'Advanced')),
  interests      text[] not null default '{}',
  updated_at     timestamptz not null default now()
);

create table if not exists public.progress (
  user_id            uuid primary key references auth.users (id) on delete cascade,
  xp                 integer not null default 0 check (xp >= 0),
  streak             integer not null default 0 check (streak >= 0),
  last_active        date,
  hearts             integer not null default 5 check (hearts between 0 and 5),
  hearts_last_refill bigint not null default 0,
  completed          jsonb not null default '{}'::jsonb,   -- {"<lessonId>": stars}
  updated_at         timestamptz not null default now()
);

create table if not exists public.discoveries (
  id          text not null,
  user_id     uuid not null references auth.users (id) on delete cascade,
  title       text not null check (char_length(title) <= 160),
  summary     text not null default '' check (char_length(summary) <= 4000),
  phrase      jsonb,
  created_at  timestamptz not null default now(),
  primary key (user_id, id)
);

create table if not exists public.trips (
  id          text not null,
  user_id     uuid not null references auth.users (id) on delete cascade,
  data        jsonb not null,                              -- the saved itinerary document
  created_at  timestamptz not null default now(),
  primary key (user_id, id)
);

alter table public.profiles    enable row level security;
alter table public.progress    enable row level security;
alter table public.discoveries enable row level security;
alter table public.trips       enable row level security;

do $$
declare t text;
begin
  foreach t in array array['profiles', 'progress', 'discoveries', 'trips'] loop
    execute format('drop policy if exists "%1$s_select_own" on public.%1$s', t);
    execute format('drop policy if exists "%1$s_insert_own" on public.%1$s', t);
    execute format('drop policy if exists "%1$s_update_own" on public.%1$s', t);
    execute format('drop policy if exists "%1$s_delete_own" on public.%1$s', t);
    execute format('create policy "%1$s_select_own" on public.%1$s for select to authenticated using (user_id = (select auth.uid()))', t);
    execute format('create policy "%1$s_insert_own" on public.%1$s for insert to authenticated with check (user_id = (select auth.uid()))', t);
    execute format('create policy "%1$s_update_own" on public.%1$s for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()))', t);
    execute format('create policy "%1$s_delete_own" on public.%1$s for delete to authenticated using (user_id = (select auth.uid()))', t);
  end loop;
end $$;

-- No access for the anonymous role at all.
revoke all on public.profiles, public.progress, public.discoveries, public.trips from anon;
