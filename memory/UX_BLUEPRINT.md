# CAOS — UX Blueprint (locked contract)
_Built from 20+ screenshots of user's deployed Base44 (`caos-chat-9c5683d8.base44.app`) and Emergent-hosted (`deno-env-review.emergent.host`) versions. This is the single source of truth. Agent must NOT deviate without explicit user approval._

---

## A. Auth / Login screen (`/login`)
Clean white card, centered, light background. Contains:
- Avatar orb (CAOS icon)
- `Welcome to CAOS-A.I.`
- `Sign in to continue`
- **[ G Continue with Google ]** primary button
- `— OR —` divider
- Email field (`you@example.com`)
- Password field
- **[ Sign in ]** dark button (full width)
- Links: `Forgot password?` (left) · `Need an account? Sign up` (right)

## B. Welcome Tour (5 steps, shown first-run)
Modal card, dark glass, dot progress indicator at top (5 dots, active one brighter).
Each step: title + body + `[Skip tour]` left · `[Next →]` (or `[Get started →]` on final) right.

1. **Start here** — "Type anything — a question, a task, code, a plan. Aria reads it and responds with real intelligence, not canned replies."
2. **Your threads** — "Every conversation is saved automatically. Switch between threads, search your history, and pick up exactly where you left off."
3. **Aria remembers** — "Tell Aria to remember something and she will — across every future session. Your preferences, your projects, your context."
4. **Attach anything** — "Drop in files, images, screenshots, or take a photo. Aria can see, read, and reason about everything you share. You can paste the image from the clipboard."
5. **Get started** — final CTA button `Get started →`

## C. Shell — top bar (3 columns)
| LEFT | CENTER | RIGHT |
|---|---|---|
| `[sidebar-toggle icon]` `M MICHAEL ▼` | `CAOS` + `Cognitive Adaptive Operating System` | active-thread-name · `[🔍 search-this-thread]` · `X.XK / 200.0K` meter |

- The `M MICHAEL ▼` chip IS the menu trigger — no separate hamburger.
- Dropdown: `Desktop ›` · `+ New Thread` · `Previous Threads` · `Profile` · `Engine = ⚡OpenAI/Claude/Gemini` (inline toggle) · `Log Out`

## D. Left rail (contained, scrollable, default CLOSED)
- `Search chats…` input at top
- Menu: **Chat** (active) · Create · Tools · Models · Projects · Threads
- `RECENT` header → recent thread cards
- Clicking "Previous Threads" opens a drawer INSIDE the rail (not an overlay on top of chat)

### Thread cards (inside Previous Threads drawer)
Each card:
- Title (bold, ellipsized)
- Preview snippet (2 lines)
- `X ago` timestamp
- Mini-WCW progress meter: `19.3K / 200.0K` with bar
- Inline actions (always visible or hover-reveal): 
  - 🔵 pencil → rename
  - 🟡 flag → mark for follow-up
  - 🔴 trash → delete
- Active thread: purple glow/outline

## E. Center surface — welcome state
- `Welcome to CAOS` big hero title (H1, bold)
- Subtitle: `Search the web, analyze data, generate content, and get instant answers.`
- Italic purple: `Try these to see what's possible`
- **3-card carousel** (not 4): `Create Image · Create Video · Chat with Multiple Models`
  - Left ‹ right › arrows, dot page indicators below
- Below carousel: composer

## F. Engine pills (above composer, centered)
- `⚡ Claude click to switch` (yellow outline glow when active)
- `Multi-Agent OFF` toggle pill
- Tooltip on hover: `Engine: Claude — click to switch`

## G. Composer (floating ~1in off bottom, glass shell)
Horizontal row:
1. 📎 attach (upload files)
2. 🔊 speaker (auto-read responses toggle)
3. `+` thought stash button
4. textarea: `Ask anything… and switch models mid chat with no problem!` (auto-grow 1–6 rows)
5. 🎤 mic (pulsing red ring + live transcript ribbon when recording)
6. ▶ purple-gradient circular send

Below composer: suggestion chips from user's projects (`Project Alpha`, `Immigration plan`, `CAOS build`).

Footer chip: `💾 Memory: N facts saved` (green pill).

**Mic behavior:** STT APPENDS at cursor position (with a space), does NOT overwrite.

## H. Message bubbles
- **User**: right-aligned, purple-gradient background, rounded with asymmetric bottom-right corner, purple glow shadow. Action chips below: `📋 Copy` · `↩ Reply` · `👍 Useful`
- **CAOS (assistant)**: left-aligned, subtle dark glass card, small purple orb avatar on left. Same 3 action chips + Read Aloud.
- Message footer: `Apr 20, 2026 • 1:00 AM • 28.5s` + `> Evidence` expandable
- Long outputs show `Show full output…` link

## I. Profile drawer (right side)
Header: `Profile` + X close.
- Avatar orb (M, blue-purple gradient)
- Name (`MICHAEL CHAMBERS` when Admin, `Michael` when User)
- Role badge: `Admin` or `USER`
- 3 tabs: 📄 Files (green) · 🖼 Photos (purple) · 🔗 Links (blue)
- Email row
- Member since
- Role row
- Birthday row (`Jan 22, 1977 (49)` + `[Edit]`, or `Not set` + `[Add]`)
- Permanent Memories: `N saved · View & edit`
- **Toggle list** (6 switches):
  - ✅ Remember Conversations — Enable memory
  - 🎮 Game Mode — Admin access (locked for non-admin)
  - 🔀 Developer Mode — Split-screen
  - 🤝 Multi-Agent Mode — Collaboration
  - 📊 System Console — Monitor metrics
  - 🗑 (future toggles as added)
- `Voice & Speech` link
- `Delete Account` link (red, bottom)

## J. Inspector drawer (left side, bottom-floating)
Header: `Inspector` + X close.
- Section: **Context Diagnostics**
  - Grid row 1: `Trimmed 0%` · `Lane general`
  - Grid row 2: `Continuity 0` · `Workers 0`
- Section: **Runtime** — `openai · gpt-5.2` (or current provider.model)
- Section: **Used for recall** — `No turn yet` or hydration summary
- Section: **Subject bins** — `No bins selected` or pills

## K. Artifacts drawer (right side, alt to Profile)
Header: `Artifacts` + X close.
- Stats grid: `Stored items N` · `Receipts N` · `Memory artifacts N`
- Stats grid 2: `Files N` · `Receipts N` · `Summaries N` · `Seeds N`
- **Files / Photos / Links** section:
  - `Upload file` button (multi-select, up to 10)
  - `Link label` text input
  - `https://…` URL input
  - `Save link` button
- Files list (recent uploads, clickable)
- Photos list (recent image thumbnails)

## L. Search — TWO separate surfaces
1. **Search all threads** (from left-rail `Search chats…`) — fuzzy across all threads, returns thread cards
2. **Search THIS thread** — TWO entry points:
   - Left-side `Search Thread` panel: query echo, `Search this thread` input, numbered results (`#1 You 1:56` + snippet)
   - Top-right inline `fre…` search: filters messages in the active thread with yellow `<mark>` highlights + match count `7` + X to clear → opens right-side results panel

## M. Selection reaction popover
Highlight any text in a message → popover appears:
- 31 emoji reactions (frequency-sorted, most-used first)
- Text reply input
- `🔊 Read` (browser speechSynthesis)
- `📋 Copy`
- `✉ Email` (Resend integration — Phase 7a)
- Auto-dismiss after 4s inactivity

## N. Bottom behavioral rules
- **Click-outside-to-close** is MANDATORY on every drawer, popover, modal, menu.
- **Escape key** closes the same.
- **Auto-dismiss status banners** after 4s (no sticky "Read Aloud unavailable" messages).
- **Optimistic user message** — appears instantly on send.
- **Typing dots** while awaiting first stream delta.
- **Streaming cursor (▌)** during SSE delta render.
- **Rename thread**: inline editable title on click-pencil.
- **Flag thread**: toggle state, shown as orange tag on card.
- **Delete thread**: confirmation modal before destructive action.

## O. Complaint auto-flag to Admin (Phase 4 feature)
- Chat pipeline runs a sentiment/complaint classifier on each user message.
- If classified as a complaint, Aria responds with: `"Want me to escalate this to admin?"` with Yes/No inline buttons.
- On Yes, backend sends a Resend email to admin with the thread excerpt.
- No more "go email feedback" — chat handles it.

## P. File handling
- Upload multi-file (max 10 currently — platform-capped).
- Zip support: unzip server-side, index contents (when platform allows).
- Images → auto-attach to `UserMessage.file_contents` for Gemini provider.
- Non-Gemini providers get filename + mime + size in system prompt.

## Q. Auth + role
- Emergent-managed Google OAuth.
- User `mytaxicloud@gmail.com` → auto-assigned **Admin** role on first login (seeded).
- Admin role unlocks: Game Mode, Developer Mode, Multi-Agent Mode, System Console.

---

## Build order (locked sequence)
1. Fix STT append-at-cursor (Composer bug)
2. Threads-in-sidebar (contained, not overlay) + inline card actions + mini-WCW meters
3. Left rail menu (Chat/Create/Tools/Models/Projects/Threads) + RECENT section
4. Welcome hero + 3-card carousel
5. Profile drawer 6-toggle parity + Admin role auto-assign for user's email
6. 5-step Welcome Tour modal (shown on first login only)
7. Click-outside-to-close audit across every drawer/popover
8. Mic recording indicator (pulsing + live transcript + timer)
9. Login screen visual parity (Google button + Email/Password fallback)
10. Selection popover → Email button (Resend integration, Phase 7a)
11. Complaint auto-flag pipeline (Phase 4)

Each step ships independently. No big-bang rebuild.
