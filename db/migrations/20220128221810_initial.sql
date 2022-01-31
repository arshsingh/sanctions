-- migrate:up
create extension pg_trgm;

-- important to revoke permissions to call functions
alter default privileges revoke execute on functions from public;

-- separate schemas for internal data and
-- publicly accessible views / procedures
create schema internal;
create schema api;

grant all on schema api to api;
grant usage on schema api to anon;

-- TODO: add more data
create table internal.sanctions (
  id uuid default gen_random_uuid() primary key,
  target_type text not null check (
    target_type in ('individual', 'entity', 'aircraft', 'vessel')
  ),
  source text not null check (source in ('ofac', 'unsc', 'eu')),
  source_id text not null,
  names text[] default '{}',
  positions text[] default '{}',
  remarks text,
  listed_on date,
  created_at timestamp with time zone default now(),

  unique(source, source_id)
);
grant select on internal.sanctions to api;

create view api.sanctions as select * from internal.sanctions;
alter view api.sanctions owner to api;
grant select on api.sanctions to anon;

-- TODO: can't index on text[] directly; restructure later
create function api.search_sanctions(name text) returns setof api.sanctions as $$
  select * from api.sanctions
  where name % any(names);
$$ language sql stable;
grant execute on function api.search_sanctions(text) to anon;
-- migrate:down
