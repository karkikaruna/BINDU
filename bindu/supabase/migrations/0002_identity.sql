-- BINDU user identity + automatic per-user rows.
-- Run after 0001_init.sql (Supabase SQL editor, or `supabase db push`). Safe to run more than once.
--
-- What this adds:
--   * profiles.email       copy of the sign-in email, so a user's identity is readable next to their progress
--   * profiles.onboarded   whether the person has finished the first-run questions (lets a fresh device skip them)
--   * profiles.created_at  when the account was made
--   * a trigger that creates the profile + progress row the moment someone registers, using the name typed on the
--     sign-up form (sent as user metadata `display_name`). Every user therefore always has exactly one row of each.
-- The authoritative identity stays in auth.users (id, email, password hash); profiles is the app-level copy.

alter table public.profiles add column if not exists email text;
alter table public.profiles add column if not exists created_at timestamptz not null default now();

-- Accounts that existed before this migration have already been through onboarding.
do $$
begin
  if not exists (select 1 from information_schema.columns
                 where table_schema = 'public' and table_name = 'profiles' and column_name = 'onboarded') then
    alter table public.profiles add column onboarded boolean not null default false;
    update public.profiles set onboarded = true;
  end if;
end $$;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, display_name, email)
  values (new.id, left(coalesce(nullif(btrim(new.raw_user_meta_data ->> 'display_name'), ''), ''), 40), new.email)
  on conflict (user_id) do nothing;

  insert into public.progress (user_id) values (new.id) on conflict (user_id) do nothing;
  return new;
end;
$$;

revoke all on function public.handle_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Backfill accounts that registered before the trigger existed.
insert into public.profiles (user_id, display_name, email)
select u.id, left(coalesce(nullif(btrim(u.raw_user_meta_data ->> 'display_name'), ''), ''), 40), u.email
from auth.users u
on conflict (user_id) do nothing;

update public.profiles p set email = u.email from auth.users u where u.id = p.user_id and p.email is null;

insert into public.progress (user_id) select id from auth.users on conflict (user_id) do nothing;
