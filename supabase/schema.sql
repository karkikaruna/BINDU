
create table if not exists units (
    id serial primary key,
    name text not null,          
    order_index int not null,
    color_theme text           
);

create table if not exists lessons (
    id serial primary key,
    unit_id int references units(id) on delete cascade,
    name text not null,
    order_index int not null
);

create table if not exists exercises (
    id serial primary key,
    lesson_id int references lessons(id) on delete cascade,
    type text not null check (type in ('multiple_choice', 'word_bank')),
    prompt text not null,
    options jsonb,              
    tokens jsonb,               
    answer jsonb not null,
    audio_url text,
    order_index int not null
);

create table if not exists user_progress (
    user_id uuid references auth.users(id) on delete cascade,
    lesson_id int references lessons(id) on delete cascade,
    completed boolean default false,
    stars int default 0,
    primary key (user_id, lesson_id)
);

create table if not exists user_stats (
    user_id uuid primary key references auth.users(id) on delete cascade,
    hearts int default 5,
    xp int default 0,
    streak int default 0,
    last_active date,
    hearts_last_refill timestamptz default now()
);


alter table units enable row level security;
alter table lessons enable row level security;
alter table exercises enable row level security;
alter table user_progress enable row level security;
alter table user_stats enable row level security;

create policy "curriculum readable by authenticated users" on units
    for select using (auth.role() = 'authenticated');
create policy "curriculum readable by authenticated users" on lessons
    for select using (auth.role() = 'authenticated');
create policy "curriculum readable by authenticated users" on exercises
    for select using (auth.role() = 'authenticated');

create policy "users manage their own progress" on user_progress
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "users manage their own stats" on user_stats
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create or replace function public.handle_new_user()
returns trigger as $$
begin
    insert into public.user_stats (user_id, hearts, xp, streak, hearts_last_refill)
    values (new.id, 5, 0, 0, now());
    return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();
