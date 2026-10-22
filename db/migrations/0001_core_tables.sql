-- Core data model (docs/design.md §6). Every row belongs to an offer.

create function si_internal.touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end
$$;

create table offers (
  id          uuid primary key default gen_random_uuid(),
  slug        text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
  name        text not null,
  status      text not null default 'active' check (status in ('active', 'paused', 'archived')),
  config      jsonb not null default '{}',
  config_hash text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table offer_members (
  offer_id   uuid not null references offers (id) on delete cascade,
  user_id    uuid not null,
  role       text not null check (role in ('owner', 'approver', 'rep', 'viewer')),
  created_at timestamptz not null default now(),
  primary key (offer_id, user_id)
);

create table runs (
  id          uuid primary key default gen_random_uuid(),
  offer_id    uuid references offers (id) on delete cascade,
  task        text not null,
  actor       text not null,
  status      text not null default 'running'
              check (status in ('running', 'ok', 'failed', 'skipped')),
  counts      jsonb not null default '{}',
  error       text,
  started_at  timestamptz not null default now(),
  finished_at timestamptz
);

create table segments (
  id           uuid primary key default gen_random_uuid(),
  offer_id     uuid not null references offers (id) on delete cascade,
  key          text not null,
  industry     text,
  geography    jsonb not null default '{}',
  size         text,
  languages    text,
  target_total integer not null default 0 check (target_total >= 0),
  created_at   timestamptz not null default now(),
  unique (offer_id, key)
);

create table accounts (
  id          uuid primary key default gen_random_uuid(),
  offer_id    uuid not null references offers (id) on delete cascade,
  segment_id  uuid references segments (id) on delete set null,
  name        text not null,
  domain      text,
  phone       text,
  address     text,
  country     char(2) check (country ~ '^[A-Z]{2}$'),
  region      text,
  timezone    text,
  stage       text not null default 'new' check (stage in (
                'new', 'enriched', 'verified', 'scored', 'researched', 'proof_ready',
                'drafted', 'contacted', 'replied', 'meeting', 'won', 'lost', 'disqualified')),
  dedupe_key  text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (offer_id, dedupe_key)
);

create table people (
  id              uuid primary key default gen_random_uuid(),
  offer_id        uuid not null references offers (id) on delete cascade,
  account_id      uuid not null references accounts (id) on delete cascade,
  full_name       text,
  role_title      text,
  email           text check (email = lower(email)),
  email_status    text not null default 'unknown'
                  check (email_status in ('unknown', 'valid', 'risky', 'invalid', 'catch_all')),
  is_role_address boolean not null default false,
  linkedin_url    text,
  consent_basis   text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (offer_id, email)
);

-- Observations with provenance. Append-only by convention; newest non-expired row wins.
create table facts (
  id          uuid primary key default gen_random_uuid(),
  offer_id    uuid not null references offers (id) on delete cascade,
  entity_type text not null check (entity_type in ('account', 'person')),
  entity_id   uuid not null,
  key         text not null,
  value       jsonb not null,
  source_url  text not null check (source_url ~ '^(https?|operator|import)://.+'),
  source_kind text not null
              check (source_kind in ('website', 'listing', 'search', 'api', 'operator', 'import')),
  confidence  numeric(3, 2) not null default 0.5 check (confidence between 0 and 1),
  observed_at timestamptz not null default now(),
  expires_at  timestamptz,
  run_id      uuid references runs (id) on delete set null
);
create index facts_entity_idx on facts (entity_type, entity_id, key, observed_at desc);

create table signals (
  id             uuid primary key default gen_random_uuid(),
  offer_id       uuid not null references offers (id) on delete cascade,
  account_id     uuid not null references accounts (id) on delete cascade,
  kind           text not null,
  strength       numeric(3, 2) not null default 1 check (strength between 0 and 1),
  half_life_days integer not null default 30 check (half_life_days > 0),
  fact_id        uuid references facts (id) on delete set null,
  observed_at    timestamptz not null default now()
);

create table fit_scores (
  id         uuid primary key default gen_random_uuid(),
  offer_id   uuid not null references offers (id) on delete cascade,
  account_id uuid not null references accounts (id) on delete cascade,
  score      integer not null check (score between 0 and 100),
  confidence text not null check (confidence in ('low', 'medium', 'high')),
  reason     text not null,
  inputs     jsonb not null default '{}',
  version    text not null,
  created_at timestamptz not null default now()
);
create index fit_scores_account_idx on fit_scores (account_id, created_at desc);

create table dossiers (
  id         uuid primary key default gen_random_uuid(),
  offer_id   uuid not null references offers (id) on delete cascade,
  account_id uuid not null references accounts (id) on delete cascade,
  body_md    text not null,
  fact_ids   uuid[] not null default '{}',
  model      text,
  cost_usd   numeric(12, 6) not null default 0,
  created_at timestamptz not null default now()
);

create table proof_assets (
  id         uuid primary key default gen_random_uuid(),
  offer_id   uuid not null references offers (id) on delete cascade,
  account_id uuid not null references accounts (id) on delete cascade,
  adapter    text not null,
  asset_url  text,
  demo_url   text,
  slug       text,
  expires_at timestamptz,
  health     text not null default 'unknown' check (health in ('unknown', 'ok', 'failing')),
  created_at timestamptz not null default now(),
  unique (offer_id, slug)
);

create table mailboxes (
  id           uuid primary key default gen_random_uuid(),
  offer_id     uuid not null references offers (id) on delete cascade,
  address      text not null check (address = lower(address)),
  provider     text not null check (provider in ('smtp', 'graph')),
  daily_cap    integer not null default 30 check (daily_cap >= 0),
  warmup_start date,
  health       text not null default 'unknown' check (health in ('unknown', 'ok', 'failing')),
  active       boolean not null default true,
  created_at   timestamptz not null default now(),
  unique (offer_id, address)
);

create table sequences (
  id            uuid primary key default gen_random_uuid(),
  offer_id      uuid not null references offers (id) on delete cascade,
  person_id     uuid not null references people (id) on delete cascade,
  channel       text not null,
  template_set  text not null,
  state         text not null default 'active' check (state in ('active', 'stopped', 'completed')),
  stop_reason   text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create table messages (
  id                uuid primary key default gen_random_uuid(),
  offer_id          uuid not null references offers (id) on delete cascade,
  sequence_id       uuid references sequences (id) on delete cascade,
  person_id         uuid references people (id) on delete set null,
  step              integer not null default 1 check (step >= 1),
  channel           text not null,
  status            text not null default 'drafted' check (status in (
                      'drafted', 'blocked', 'draft', 'rejected', 'approved', 'held',
                      'sending', 'sent', 'failed', 'dead', 'bounced', 'cancelled')),
  to_address        text,
  subject           text,
  body              text,
  body_html         text,
  slots             jsonb not null default '{}',
  fact_ids          uuid[] not null default '{}',
  lint              jsonb not null default '{}',
  message_id_header text unique,
  in_reply_to       text,
  mailbox_id        uuid references mailboxes (id) on delete set null,
  approved_by       text,
  approved_at       timestamptz,
  edited_by         text,
  edited_at         timestamptz,
  sent_at           timestamptz,
  attempts          integer not null default 0,
  last_error        text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index messages_queue_idx on messages (offer_id, status);

create table events (
  id              uuid primary key default gen_random_uuid(),
  offer_id        uuid not null references offers (id) on delete cascade,
  account_id      uuid references accounts (id) on delete set null,
  person_id       uuid references people (id) on delete set null,
  message_id      uuid references messages (id) on delete set null,
  type            text not null check (type in (
                    'page_view', 'cta_open', 'callback_request', 'demo_call', 'reply', 'bounce',
                    'unsubscribe', 'complaint', 'meeting', 'approval', 'send', 'kill_switch')),
  meta            jsonb not null default '{}',
  idempotency_key text unique,
  at              timestamptz not null default now()
);
create index events_offer_type_idx on events (offer_id, type, at desc);

create table replies (
  id               uuid primary key default gen_random_uuid(),
  offer_id         uuid not null references offers (id) on delete cascade,
  message_id       uuid references messages (id) on delete set null,
  person_id        uuid references people (id) on delete set null,
  from_address     text not null,
  raw_ref          text,
  intent           text check (intent in (
                     'interested', 'question', 'not_now', 'referral', 'unsubscribe',
                     'out_of_office', 'bounce', 'hostile', 'injection')),
  confidence       numeric(3, 2) check (confidence between 0 and 1),
  draft_message_id uuid references messages (id) on delete set null,
  received_at      timestamptz not null default now()
);

-- offer_id null = applies to every offer.
create table suppression (
  id         uuid primary key default gen_random_uuid(),
  offer_id   uuid references offers (id) on delete cascade,
  value      text not null,
  kind       text not null check (kind in ('email', 'domain', 'email_sha256')),
  reason     text not null,
  source     text not null,
  created_by text not null,
  created_at timestamptz not null default now()
);
create index suppression_value_idx on suppression (value);

create table costs (
  id       uuid primary key default gen_random_uuid(),
  offer_id uuid not null references offers (id) on delete cascade,
  run_id   uuid references runs (id) on delete set null,
  provider text not null,
  model    text,
  task     text,
  units    jsonb not null default '{}',
  usd      numeric(12, 6) not null check (usd >= 0),
  at       timestamptz not null default now()
);
create index costs_offer_at_idx on costs (offer_id, at);

-- Kill switches, pauses and other switches. offer_id null = global.
create table settings (
  id       uuid primary key default gen_random_uuid(),
  offer_id uuid references offers (id) on delete cascade,
  key      text not null,
  value    jsonb not null,
  set_by   text not null,
  reason   text not null,
  set_at   timestamptz not null default now()
);
create unique index settings_scope_key_idx
  on settings (coalesce(offer_id, '00000000-0000-0000-0000-000000000000'::uuid), key);

-- Who did what, why. Written by the engine for every write and outbound action.
create table audit_log (
  id       uuid primary key default gen_random_uuid(),
  offer_id uuid references offers (id) on delete cascade,
  actor    text not null,
  action   text not null,
  target   text,
  detail   jsonb not null default '{}',
  at       timestamptz not null default now()
);

create trigger offers_touch before update on offers
  for each row execute function si_internal.touch_updated_at();
create trigger accounts_touch before update on accounts
  for each row execute function si_internal.touch_updated_at();
create trigger people_touch before update on people
  for each row execute function si_internal.touch_updated_at();
create trigger sequences_touch before update on sequences
  for each row execute function si_internal.touch_updated_at();
