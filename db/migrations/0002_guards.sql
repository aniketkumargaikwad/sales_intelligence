-- Guarantees that hold even if the Python code has a bug (docs/design.md §5.9, §5.10).

-- 1. Suppression is append-only and normalised.
create function si_internal.suppression_normalise() returns trigger
language plpgsql as $$
begin
  new.value := lower(btrim(new.value));
  if new.kind = 'domain' then
    new.value := regexp_replace(new.value, '^@', '');
  end if;
  return new;
end
$$;

create function si_internal.suppression_append_only() returns trigger
language plpgsql as $$
begin
  raise exception 'suppression is append-only: % is not allowed', tg_op
    using errcode = 'P0001', hint = 'Suppression rows are never edited or removed.';
end
$$;

create trigger suppression_normalise before insert on suppression
  for each row execute function si_internal.suppression_normalise();
create trigger suppression_no_update before update or delete on suppression
  for each row execute function si_internal.suppression_append_only();
create trigger suppression_no_truncate before truncate on suppression
  for each statement execute function si_internal.suppression_append_only();

-- 2. Message lifecycle: allowed transitions, approval required to send, frozen content.
create table si_internal.message_transitions (
  from_status text not null,
  to_status   text not null,
  primary key (from_status, to_status)
);

insert into si_internal.message_transitions (from_status, to_status) values
  ('drafted',  'draft'), ('drafted', 'blocked'), ('drafted', 'cancelled'),
  ('blocked',  'drafted'), ('blocked', 'rejected'), ('blocked', 'cancelled'),
  ('draft',    'drafted'), ('draft', 'blocked'), ('draft', 'approved'),
  ('draft',    'rejected'), ('draft', 'cancelled'),
  ('approved', 'sending'), ('approved', 'held'), ('approved', 'blocked'),
  ('approved', 'draft'), ('approved', 'cancelled'),
  ('held',     'approved'), ('held', 'draft'), ('held', 'cancelled'),
  ('sending',  'sent'), ('sending', 'failed'),
  ('failed',   'approved'), ('failed', 'dead'), ('failed', 'cancelled'),
  ('sent',     'bounced');

create function si_internal.messages_guard() returns trigger
language plpgsql as $$
declare
  frozen constant text[] := array['approved', 'held', 'sending', 'sent', 'failed', 'bounced', 'dead'];
begin
  if tg_op = 'INSERT' then
    if new.status not in ('drafted', 'draft', 'blocked') then
      raise exception 'a new message must start as drafted, draft or blocked, not %', new.status
        using errcode = 'P0001';
    end if;
    new.approved_by := null;
    new.approved_at := null;
    return new;
  end if;

  if new.status is distinct from old.status then
    if not exists (
      select 1 from si_internal.message_transitions
      where from_status = old.status and to_status = new.status
    ) then
      raise exception 'message % cannot move from % to %', old.id, old.status, new.status
        using errcode = 'P0001';
    end if;
  end if;

  -- Going back for edits always throws away the approval.
  if new.status in ('drafted', 'draft', 'blocked') then
    new.approved_by := null;
    new.approved_at := null;
  end if;

  if new.status in ('approved', 'held', 'sending', 'sent') then
    if new.approved_by is null or new.approved_at is null then
      raise exception 'message % needs approved_by and approved_at to be %', old.id, new.status
        using errcode = 'P0001';
    end if;
  end if;

  if old.status = any (frozen) and new.status = any (frozen) and (
       new.subject   is distinct from old.subject
    or new.body      is distinct from old.body
    or new.body_html is distinct from old.body_html
    or new.to_address is distinct from old.to_address
    or new.offer_id  is distinct from old.offer_id
  ) then
    raise exception 'message % is approved; move it back to draft before editing', old.id
      using errcode = 'P0001';
  end if;

  if new.status = 'sent' and new.sent_at is null then
    new.sent_at := now();
  end if;
  new.updated_at := now();
  return new;
end
$$;

create trigger messages_guard before insert or update on messages
  for each row execute function si_internal.messages_guard();
