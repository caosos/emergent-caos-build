# CAOS Connector Stack — Blueprint

Last updated: Apr 24, 2026. This is a design document, not shipped code. It
captures the end-to-end architecture for the four large (L-tier) connectors
that remain on the roadmap so future sessions can pick any of them up cleanly.

Shared principles (apply to all four):
- **Self-serve**: user initiates, service provides OAuth consent, CAOS never
  sees raw credentials outside the token store.
- **Scoped**: request the minimum scopes the feature actually uses.
- **Per-user**: tokens stored at `user_profiles.connectors.<service>`. Admins
  cannot read other users' tokens.
- **Revocable**: user can disconnect from inside CAOS and from the service's
  own dashboard (Google Account → Security, GitHub → Tokens, etc.).
- **Aria-aware**: every connector exposes a tool marker (`[TOOL: gmail_list …]`,
  `[TOOL: drive_search …]`) so Aria can use them mid-conversation, same pattern
  as `web_fetch` / `github_fetch`.

---

## 1. Gmail Phase A — Read inbox

### User experience
- Settings → **Connectors** → `Gmail — Not connected` → `Connect Gmail` button.
- Google OAuth consent screen pops (scopes: `gmail.readonly`, `openid`, `email`).
- After consent, Settings row flips to `Connected as alex@example.com` with
  Revoke button.
- New **Inbox** panel available from the account menu (drawer on the right,
  lives next to Admin Dashboard). Shows: list of threads with sender/subject/
  snippet on the left, thread detail on the right.
- Aria gains two tools:
  - `[TOOL: gmail_search query="from:lawyer@" max=10]` → list thread summaries
  - `[TOOL: gmail_thread id="<thread_id>"]` → full thread body
- Pull email into current chat: on any thread, a "Send to Aria" button
  injects the thread text into the composer with a citation chip.

### Scopes
- `https://www.googleapis.com/auth/gmail.readonly`
- `openid`, `email`, `profile` (reuse Emergent Google Auth already in place)

### Backend
- New file `app/routes/gmail.py` — routes:
  - `POST /api/connectors/gmail/oauth/start` → returns Google consent URL
  - `GET /api/connectors/gmail/oauth/callback` → exchanges code → stores token
  - `GET /api/connectors/gmail/threads?q=&max=` → list
  - `GET /api/connectors/gmail/threads/{id}` → detail
  - `DELETE /api/connectors/gmail` → revoke + remove token
- New service `app/services/gmail_service.py` — thin wrapper over
  `google-auth` + `google-api-python-client` (`gmail` v1). Token refresh on
  each call if expired.
- Token storage: `user_profiles.connectors.gmail = {access_token, refresh_token, expires_at, scope, email}`.
- Rate limit: 120 req/min/user on Gmail routes via existing middleware.

### Frontend
- New `ConnectorsDrawer.js` (Settings sub-view or new tab in ProfileDrawer).
  Lists GitHub + Gmail + future connectors; each row has Connect/Revoke.
- New `GmailInboxDrawer.js` — thread list + detail. Re-uses bubble styles.
- Aria tool markers rendered as citation chips in reply bubbles when she used
  `gmail_search` / `gmail_thread`.

### Security
- Refresh tokens encrypted at rest via Fernet with `CAOS_CRYPT_KEY` env.
- `request_uri_ok` check at every redirect — only production domain permitted.
- Logout kills the session cookie but does NOT automatically revoke Gmail;
  user has to click Revoke explicitly.

### Playbook / references
- Emergent integration expert playbook for Google OAuth
- Gmail API v1 docs: https://developers.google.com/gmail/api
- Google verification required for production domain (2–4 weeks lead time)
  if we want external users; internal testing up to 100 users is unverified-OK.

### Credit estimate
~60–80 tool calls end-to-end. **Ship in its own session.**

---

## 2. Gmail Phase B — Compose / send

Builds on Phase A's OAuth. Adds scope `gmail.send`.

### UX
- Inside Inbox thread detail: a `Reply in CAOS` button opens a pane with a
  composer (rich text + attachments).
- Aria gains `[TOOL: gmail_draft to=… subject=… body=…]` — creates a draft,
  shows a confirmation chip to user before send.
- Send flow is always **two-step**: Aria drafts → user clicks "Send".
  No auto-send without explicit user action. This is deliberate: "agents"
  that send mail unreviewed are the #1 way trust gets broken.

### Backend deltas
- `POST /api/connectors/gmail/drafts` — create draft
- `POST /api/connectors/gmail/drafts/{id}/send` — send draft
- Updated scopes on re-consent.

### Credit estimate
~30–40 tool calls (Phase A must be live first).

---

## 3. Google Drive — List / search / open / attach

### UX
- Settings → Connectors → `Drive — Not connected` → OAuth
- Scopes: `drive.readonly` (or `drive.file` for narrower access)
- New `DriveDrawer.js` — file tree / search results / preview.
- Attach Drive file into current thread: becomes a CAOS artifact with a
  "Source: Drive · shared with owner X" chip.
- Aria gains `[TOOL: drive_search query=…]` and `[TOOL: drive_get id=…]`.

### Backend
- `app/routes/drive.py` + `app/services/drive_service.py`
- Token storage: `user_profiles.connectors.drive`
- Drive API v3 `files.list`, `files.get`, `files.export` (for Google Docs →
  markdown), `files.content` for binary types.
- Handle Google Doc → Markdown export mapping table.

### Credit estimate
~55–65 tool calls.

---

## 4. Google Calendar — Read / create events

### UX
- Scopes: `calendar.readonly` to start, optional `calendar.events` for create.
- New `CalendarDrawer.js` — today / week view.
- Aria gains `[TOOL: calendar_list date=YYYY-MM-DD]`, `[TOOL: calendar_create …]`.
- Same two-step pattern as Gmail send: Aria drafts event → user confirms.

### Backend
- `app/routes/calendar.py` + `app/services/calendar_service.py`
- Calendar API v3 `events.list`, `events.insert`.

### Credit estimate
~45–55 tool calls.

---

## 5. Stripe billing — Real subscription tiers

Replaces the mocked 6-tier quota with real billing.

### UX
- Settings → **Billing** (new row, admin-gated initially).
- `Upgrade to Pro`, `Upgrade to Unlimited` buttons → Stripe Checkout.
- Once subscribed, tier flips on `user_profiles.tier` and token quota updates.
- Cancel from inside Settings (cancels at period end).

### Backend
- `app/routes/billing.py` — Stripe Checkout session creation, webhook handler
  for `checkout.session.completed`, `customer.subscription.updated`,
  `customer.subscription.deleted`.
- Test keys from Emergent env — `STRIPE_API_KEY` already provisioned in pod.
- Price IDs stored in env (`STRIPE_PRICE_PRO`, `STRIPE_PRICE_UNLIMITED`).
- Webhook signature verification via `STRIPE_WEBHOOK_SECRET`.

### Data model
- `user_profiles.billing = {stripe_customer_id, stripe_subscription_id, status, current_period_end}`

### Admin dashboard additions
- New **Billing** tab: MRR, active subscriptions, churn last 30 d, failed payments.

### Credit estimate
~70–80 tool calls.

---

## Recommended build order

1. GitHub private-repo (S) — **DONE** (this session)
2. Ambient mode + sliders + error logging + engine timeline (S/M) — **DONE** (this session)
3. **Gmail Phase A** — next L-tier session. Highest daily-driver value.
4. **Gmail Phase B** — medium follow-up.
5. **Google Drive** — unlocks file attachment from existing storage.
6. **Calendar** — smallest of the L-tier items.
7. **Stripe** — save for last; only meaningful with a paying user cohort.

## Non-goals for this blueprint
- MCP (Model Context Protocol) client mode. Doable eventually but different
  architecture — would let CAOS talk to any MCP server (Notion, Figma, etc.)
  without building bespoke connectors. Worth a separate blueprint when ready.
- Webhooks inbound (Slack slash commands etc.). Not part of the L-tier list.
