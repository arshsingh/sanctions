-- The following changes apply on a cluster level and not on the database level,
-- hence they're not included in migrations. These changes must be deployed manually
create role sanctions with login password '$POSTGRES_PASSWORD';
create database sanctions with owner sanctions;

-- create api role that will own things like views
-- if a superuser owns the views, row-level security will be bypassed
create role api nologin noinherit;

-- unauthenticated user
create role anon nologin noinherit;

grant api to sanctions;
grant anon to sanctions;
