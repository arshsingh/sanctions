-- migrate:up
create table internal.source_status (
  source text primary key,
  synced_at timestamptz not null
);
grant select on internal.source_status to api;

create view api.sources as select * from internal.source_status;
alter view api.sources owner to api;
grant select on api.sources to anon;
-- migrate:down
drop view if exists api.sources;
drop table if exists internal.source_status;
