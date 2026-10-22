-- Row-level security by offer membership and role (ADR-0002, ADR-0004).
-- The engine and the web app's server code use the service role (or the table owner on plain
-- Postgres), which bypasses RLS. Browser sessions use the authenticated role and see only the
-- offers they are members of.

create function si_internal.has_role(target_offer uuid, roles text[]) returns boolean
language sql stable security definer set search_path = public, pg_temp
as $$
  select exists (
    select 1 from offer_members m
    where m.offer_id = target_offer and m.user_id = auth.uid() and m.role = any (roles)
  )
$$;
revoke all on function si_internal.has_role(uuid, text[]) from public;
grant execute on function si_internal.has_role(uuid, text[]) to authenticated, service_role;

do $$
declare
  t text;
  member_read constant text[] := array[
    'segments', 'accounts', 'people', 'facts', 'signals', 'fit_scores', 'dossiers',
    'proof_assets', 'mailboxes', 'sequences', 'messages', 'events', 'replies',
    'costs', 'runs', 'settings', 'audit_log', 'suppression'];
begin
  foreach t in array member_read || array['offers', 'offer_members'] loop
    execute format('alter table %I enable row level security', t);
    execute format('revoke all on %I from anon', t);
    execute format('grant select on %I to authenticated', t);
  end loop;

  foreach t in array member_read loop
    execute format($p$
      create policy %I on %I for select to authenticated
      using (offer_id is null or si_internal.has_role(offer_id,
             array['owner', 'approver', 'rep', 'viewer']))
    $p$, t || '_member_read', t);
  end loop;
end
$$;

create policy offers_member_read on offers for select to authenticated
  using (si_internal.has_role(id, array['owner', 'approver', 'rep', 'viewer']));

create policy offer_members_read on offer_members for select to authenticated
  using (user_id = auth.uid() or si_internal.has_role(offer_id, array['owner']));

-- Approvers review the queue: they may update messages (the guard trigger still applies).
grant update (status, subject, body, body_html, slots, approved_by, approved_at,
              edited_by, edited_at) on messages to authenticated;
create policy messages_approver_update on messages for update to authenticated
  using (si_internal.has_role(offer_id, array['owner', 'approver']))
  with check (si_internal.has_role(offer_id, array['owner', 'approver']));

-- Anyone working an offer can add to suppression (never remove: see 0002).
grant insert on suppression to authenticated;
create policy suppression_member_insert on suppression for insert to authenticated
  with check (offer_id is not null
              and si_internal.has_role(offer_id, array['owner', 'approver', 'rep']));

-- Owners flip switches (kill switch, pauses).
grant insert, update on settings to authenticated;
create policy settings_owner_write on settings for insert to authenticated
  with check (offer_id is not null and si_internal.has_role(offer_id, array['owner']));
create policy settings_owner_update on settings for update to authenticated
  using (offer_id is not null and si_internal.has_role(offer_id, array['owner']))
  with check (offer_id is not null and si_internal.has_role(offer_id, array['owner']));

-- The message guard trigger runs as the caller and reads the transition table.
grant select on si_internal.message_transitions to authenticated;
