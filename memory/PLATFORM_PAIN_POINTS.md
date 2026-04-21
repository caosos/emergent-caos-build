# CAOS — Platform Pain Points for Emergent Meeting
_Captured from user session Apr 20, 2026 — in user's own words, no paraphrasing where possible. These are workarounds the user is burning time on because the platform fights them._

## 1. Agent can't read user's deployed work
- User has TWO working CAOS deployments (`caos-chat-9c5683d8.base44.app` + `deno-env-review.emergent.host`) with **months** of refined behaviors.
- Agent has no way to browse/scrape these URLs (auth-gated) to self-extract the UX contract.
- **Workaround:** User is manually screenshotting 20+ views and narrating behaviors via voice/text.
- **Cost:** ~$300 of token credits spent partially because of this inability.
- **Ask:** Platform-level ability for agent to authenticate into user's own other Emergent deployments OR a "paste-from-URL" tool that can auth-cookie-through.

## 2. STT overwrites textarea instead of appending
- When user hits mic with text already in the composer, STT wipes it and replaces. User cannot "follow up and add to things you're thinking about instead of writing it down and later typing it in."
- **Workaround:** User copies text, records, pastes back. Clunky.
- Quote: "I cannot be held back by an STT that won't allow me to add more to what's already there. And then it erases it. It's such bullshit."
- **Ask:** Platform STT widget should append at cursor (with a space) by default. Or expose a config flag.

## 3. Screenshot tool clobbers clipboard
- User takes a screenshot to send to agent → OS writes image to clipboard → user's previously-copied TEXT is gone.
- **Workaround:** None. Just lose the copied content.
- Quote: "if I take a picture, it erases what I copied, so I just fucking erased a bunch of stuff that I agreed with you on"
- **Ask:** OS-level or platform-level "screenshot to file, don't touch clipboard" option.

## 4. Photo / file upload cap is too low
- User wants to send "zipped bunches of files" in one shot to brief the agent (code dumps, design refs, etc).
- Current cap: 10 files per upload.
- Zip files: not parsed server-side — agent would have to `unzip` manually.
- Quote: "am I able to send you zipped bunches of files or what? Why do I need a workaround? SOO STUPID."
- **Ask:** Raise file upload cap. Auto-extract `.zip` on upload and expose the contents.

## 5. Emergent audio proxy has invalid upstream key
- Diagnostic showed `/llm/audio/transcriptions` returns HTTP 401 with `"Incorrect API key provided: sk-proj-...AIA"` on whisper-1.
- `/audio/speech` returns HTTP 500 with empty body on tts-1 / tts-1-hd.
- User had to provide their **personal** `OPENAI_API_KEY` to bypass the broken proxy.
- **Ask:** Rotate the proxy's upstream OpenAI project key. Expand audio allow-list to include `gpt-4o-mini-tts` and `gpt-4o-mini-transcribe`.

## 6. Voice transcription model is outdated
- Allow-list is `{tts-1, tts-1-hd, whisper-1}` — rejects `gpt-4o-mini-tts` / `gpt-4o-mini-transcribe` (newer 2026 defaults) with HTTP 400 "Invalid model name".
- User wants the new models on the proxy.
- **Ask:** Add new OpenAI audio models to the proxy allow-list.

## 7. Agent repeatedly asks for clarification instead of inferring from assets
- Agent asked 5+ clarifying questions across multiple turns before committing to a plan. User is explicitly frustrated: "I've already built this thing. I already know what I need."
- **Workaround:** User forcing agent to just "look at photos" to extract contract.
- **Ask:** Platform agent should lean harder toward "build from reference assets first, iterate after" rather than interview-mode.

## 8. No cost visibility inside the agent loop
- User spent ~$300 in credits and feels 50/50 about the output.
- No in-chat meter showing "this task has cost $X so far."
- **Workaround:** User tracks usage externally via Profile → Universal Key → Usage page.
- **Ask:** Per-conversation or per-task cost pill in the Emergent UI.

## 9. Token waste on Q&A ping-pong
- Every clarifying question burns a full-context response. Screenshots must be re-uploaded multiple times as context rolls over.
- **Ask:** Persistent "session assets" panel the agent auto-references on every turn without re-sending.

## 10. User's own deployed CAOS is a better reference than any spec
- All the behaviors the user wants (thread-cards with inline pencil/trash, 5-step onboarding tour, active-thread search with yellow marks, 6-toggle profile panel, Inspector panel, Artifacts panel) already exist at `caos-chat-9c5683d8.base44.app` and `deno-env-review.emergent.host`.
- Agent cannot auth into either.
- **Ask:** First-class "Import UX contract from existing deployment URL" tool, even if it's just "take 50 screenshots of the logged-in site and give them to the agent as a .zip".

---
_Use these as talking points. Each is a specific, actionable friction with a clear ask._
