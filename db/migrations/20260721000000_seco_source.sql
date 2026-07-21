-- migrate:up
alter table internal.sanctions
  drop constraint sanctions_source_check;

alter table internal.sanctions
  add constraint sanctions_source_check check (
    source in ('ofac', 'unsc', 'eu', 'seco')
  );

-- migrate:down
delete from internal.sanctions where source = 'seco';
delete from internal.source_status where source = 'seco';

alter table internal.sanctions
  drop constraint sanctions_source_check;

alter table internal.sanctions
  add constraint sanctions_source_check check (
    source in ('ofac', 'unsc', 'eu')
  );
