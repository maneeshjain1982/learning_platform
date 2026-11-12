# Study Companion — Detailed Plan (v0.2, for review)

> v0.2 (2026-11-09): uses your LLM_Bridge at `D:\Y26\work_dir\LLM_Bridge`; links-only for Coursera/Udemy; no YouTube API key; single-user local app; 3 cold-boot paths.

A personal learning portal that turns a learning requirement ("I want to learn Agentic AI well enough to build a multi-agent app in 6 weeks") into a **sequential course**, a **personalized home page** of curated videos, courses and papers, and an **Ask LLM** tutor available on every lesson.

Status: plan + UI design only. Nothing is built yet. Items marked **[DECIDE]** need your input.

---

## 1. Goals and non-goals

**Goals (v1)**
1. Configure a learning requirement (topic, goal, level, time per week, preferred formats and sources).
2. LLM agents analyse the requirement and generate:
   - an ordered **learning path** (modules → lessons) with generated lesson notes,
   - a **personalized home page** (continue learning, today's lesson, recommended videos/courses/papers).
3. **Discover**: search YouTube, Coursera, Udemy and paper sources (arXiv, Semantic Scholar) from one box.
4. **Ask LLM**: a side-panel tutor that knows the current lesson, your level and your path.
5. Track progress (lesson done, resource saved, time spent) in SQLite.
6. **Cold boot**: ship with pre-generated paths for the seed topics so the app is useful on first launch.

**Non-goals (v1)**: multi-tenant auth, payments, hosting video ourselves, mobile app, quizzes with grading (v2).

---

## 2. What we borrow from existing platforms

| Platform | Pattern worth keeping | How we use it |
|---|---|---|
| Coursera | Structured specializations → courses → weeks → items; visible progress per module; "Coach" AI helper inside the lesson | Path → Module → Lesson spine; progress rings; Ask LLM docked beside the lesson |
| Udemy | Dense course cards (rating, hours, level, last updated); expandable curriculum accordion | Resource cards show source, duration, level, and why it was recommended |
| LinkedIn Learning | Onboarding asks role, goals and skills; "Learning paths"; short videos with transcript beside the player | Requirement wizard; path-first home page; notes/transcript pane in lesson view |
| All three | Horizontal "recommended for you" rails | Home rails per resource type, each item explained ("matches Module 2: Tool use") |

Where we differ: the path is **generated for you** and every recommendation is tied to a specific lesson, not a generic catalog.

---

## 3. Architecture

```
┌──────────────── React + Vite + TS (frontend/) ────────────────┐
│ Home · Setup wizard · Path/Lesson view · Discover · Ask LLM   │
└───────────────┬───────────────────────────────▲───────────────┘
                │ REST (JSON)                   │ polling every 2–4 s (agent progress)
┌───────────────▼───────────────────────────────┴───────────────┐
│ FastAPI (backend/)                                             │
│  api/        routers: profile, requirements, paths, lessons,   │
│              resources, search, chat, agent-runs, home         │
│  agents/     Orchestrator + sub-agents (below)                 │
│  providers/  youtube, coursera, udemy, arxiv, semantic_scholar │
│  llm/        LLMClient interface → LLM-Bridge adapter          │
│  db/         SQLModel models + SQLite (study.db)               │
└───────────────┬───────────────────────────────────────────────┘
                │
        LLM-Bridge (your existing bridge — path TBD) → model provider
```

**Stack**
- Frontend: React 18, Vite, TypeScript, Tailwind CSS, React Router, TanStack Query; Markdown rendering (react-markdown + KaTeX for formulas).
- Backend: Python 3.11+, FastAPI, SQLModel (SQLAlchemy + Pydantic), SQLite, httpx, `sse-starlette`.
- Background work: FastAPI `BackgroundTasks` for v1 (agent run ≈ 30–90 s); progress pushed over SSE. Upgrade to a queue only if needed.

**LLM integration — LLM_Bridge (`D:\Y26\work_dir\LLM_Bridge`, v0.5.0)**

Installed into the backend venv with `pip install -e D:\Y26\work_dir\LLM_Bridge`. What it gives us and what that means:

| Bridge fact | Consequence for the design |
|---|---|
| Runs the signed-in vendor CLI (`claude -p`, `codex exec`, `gemini -p`); **no API keys** | No key management. On this machine only **Claude is available** (found via the VS Code extension); ChatGPT/Gemini show as unavailable until their CLIs are installed. |
| `ask(prompt, system_prompt=, json_schema=, model=, web=, files=)` is **synchronous** and spawns a process | Wrap in `run_in_threadpool`; cap concurrent calls with a semaphore (3). |
| `ask_json(..., json_schema=)` — Claude validates natively | Every agent returns typed JSON (Pydantic model → JSON Schema). |
| `web=True` lets the model use web search | Search agents can find **real** YouTube/Coursera/Udemy URLs without any search API key. |
| **No token streaming**; a call takes ~5–30 s (longer with web) | Ask LLM shows a "thinking" state with elapsed time, then the full answer. Agent pipeline takes a few minutes, not seconds → progress UI matters. |
| Calls count toward your Claude plan limits; `LLMError` on limits/timeouts | Use `haiku` for cheap steps (ranking, home note), `sonnet` for planning/tutor; show a clear "usage limit reached, try later" state. |
| `list_providers()` | Settings page shows available providers + model choice. |

Thin wrapper so agents never import the bridge directly:

```python
class LLMClient:
    def __init__(self, provider="claude", default_model="sonnet"): ...
    async def ask(self, prompt, *, system=None, model=None, web=False) -> str: ...
    async def ask_json(self, prompt, schema: type[BaseModel], *, system=None, model=None, web=False) -> BaseModel: ...
```

Ask LLM conversation memory: we keep chat history in SQLite and send the last ~10 turns plus lesson context with each `ask()` (works for any provider). The bridge's `ClaudeSession` (`--resume`) is an option later if prompts get large.

---

## 4. The agents

All agents are plain Python classes with a `run(input) -> output` contract, typed with Pydantic, and log every step to `agent_steps` so the UI can show what happened.

| # | Agent | Input | Output | Tools |
|---|---|---|---|---|
| 0 | **Companion Orchestrator** | LearningRequirement | Path + HomeFeed | Calls 1→5 in order; 3 and 4 run in parallel |
| 1 | **Topic Identifier** | Free-text requirement + level + goal | Topic graph: core topics, sub-topics, prerequisites, out-of-scope, search keywords | LLM (JSON schema) |
| 2 | **Curriculum Planner** | Topic graph + hours/week + weeks | Ordered modules → lessons, each with objectives, est. time, and lesson notes (Markdown) | LLM |
| 3 | **Video & Course Search** | Per-lesson keywords | Candidate videos and courses with real URLs, plus "search on YouTube / Coursera / Udemy" links | LLM_Bridge `ask_json(web=True)`; YouTube oEmbed to verify; deep-link builder |
| 4 | **Paper Search** | Per-module keywords | Papers (title, authors, year, abstract, citations, PDF link) | arXiv API, Semantic Scholar API (both keyless) |
| 5 | **Curator / Ranker** | Candidates + lesson objectives + level | Top-N per lesson with a one-line "why this" | LLM scoring + rules (dedupe, duration, level, recency) |
| 6 | **Home Composer** | Path + progress + curated resources | Home feed JSON (sections, order, items) | Rules + small LLM call for the daily focus note |
| 7 | **Tutor (Ask LLM)** | Question + current lesson + profile + chat history | Streamed answer, cited to lesson/resources | LLM streaming |

Re-runs: changing the requirement re-runs from agent 1; "Refresh recommendations" re-runs 3–6 only; marking lessons done re-runs 6 only.

### Content sources (no API keys anywhere)
| Source | How we get results | How we verify | Fallback shown in UI |
|---|---|---|---|
| YouTube | Bridge web search: agent asks for specific videos for a lesson, returns title/channel/URL | YouTube **oEmbed** (`youtube.com/oembed?url=…`, keyless) confirms the video exists and gives the real title/channel/thumbnail; unverified items are dropped | "Search on YouTube" link (`youtube.com/results?search_query=…`) |
| Coursera | **Links only** (your decision): `coursera.org/search?query=…` per lesson/module | — | Same link |
| Udemy | **Links only**: `udemy.com/courses/search/?q=…` | — | Same link |
| arXiv | Public Atom API | Real API data | — |
| Semantic Scholar | Public Graph API (keyless, rate-limited) | Real API data | — |

Note: the web search could also find specific Coursera/Udemy course pages the same way as YouTube. That's off for now (links only), but it can be switched on later with one setting (`COURSE_WEB_SEARCH=true`).

---

## 5. Data model (SQLite)

```
users(id, name, email, created_at)
learning_requirements(id, user_id, title, raw_text, goal, level, hours_per_week,
                      weeks, formats_json, sources_json, status, created_at)
topic_graphs(id, requirement_id, graph_json, created_at)
paths(id, requirement_id, title, summary, status, created_at)
modules(id, path_id, idx, title, objectives_json, est_minutes)
lessons(id, module_id, idx, title, objectives_json, content_md, est_minutes)
resources(id, kind[video|course|paper|article], source[youtube|coursera|udemy|arxiv|s2|web],
          external_id, title, url, author, duration_min, level, rating, published_at,
          meta_json, fetched_at)                      -- also serves as search cache
lesson_resources(lesson_id, resource_id, rank, why_text)
progress(user_id, lesson_id, status[todo|doing|done], minutes_spent, updated_at)
saved_resources(user_id, resource_id, saved_at)
chat_sessions(id, user_id, lesson_id NULL, created_at)
chat_messages(id, session_id, role, content, created_at)
agent_runs(id, requirement_id, status, started_at, finished_at, error)
agent_steps(id, run_id, agent, status, input_json, output_json, started_at, finished_at)
home_feeds(id, user_id, path_id, feed_json, generated_at)
```

Single-user for v1 (`user_id = 1`), but the column is there so auth can be added later.

---

## 6. API (FastAPI)

```
GET  /api/profile                    PUT /api/profile
POST /api/requirements               → creates requirement, starts agent run, returns run_id
GET  /api/requirements               GET /api/requirements/{id}
GET  /api/agent-runs/{id}/events     (SSE) step-by-step progress
GET  /api/home?path_id=              personalized feed
GET  /api/paths/{id}                 path with modules/lessons/progress
GET  /api/lessons/{id}               lesson notes + ranked resources
POST /api/lessons/{id}/progress      {status, minutes}
GET  /api/search?q=&sources=&kind=&level=&max_minutes=
POST /api/resources/{id}/save        DELETE /api/resources/{id}/save
POST /api/chat                       {session_id?, lesson_id?, message} → full answer (no token streaming in the bridge)
GET  /api/providers                  bridge providers + models (for Settings)
GET  /api/chat/{session_id}
POST /api/paths/{id}/refresh         re-run agents 3–6
```

---

## 7. Frontend screens (see the design canvas)

1. **Home (personalized)** — greeting + today's focus, "Continue learning" card, path progress spine, rails: Videos · Courses · Papers, "Why these?" explanations, agent activity footer.
2. **Set up a learning goal** — 4-step wizard (What · Why/level · Time · Sources) with a live preview of what the agents are doing.
3. **Lesson view** — left: sequential syllabus with locked/next/done; centre: lesson notes + embedded video + resources; right: Ask LLM panel (collapsible, available on every page via a floating button).
4. **Discover** — one search box, source tabs (All, YouTube, Coursera, Udemy, Papers), filters (level, duration, year), "Add to lesson" action.

Ask LLM behaviour: context chips at the top ("Lesson 2.3 · Tool calling", "Level: Intermediate") that the user can remove; quick prompts ("Explain simpler", "Give an example", "Quiz me"); answers can be saved into lesson notes. Because the bridge does not stream, the panel shows "Thinking… 8 s" while waiting, then the full answer with "Claude · sonnet · 12 s" under it.

---

## 8. Cold boot content

Pre-generated at install time by running the agent pipeline once (`python -m backend.seed`) and stored in SQLite, so the first launch shows full paths without waiting.

| # | Path | Example modules |
|---|---|---|
| 1 | **Agentic AI** | What makes a system agentic · Planning & reasoning loops (ReAct, plan-and-execute) · Tool use & function calling · Memory · Multi-agent patterns · Evaluation & safety |
| 2 | **LLM Fundamentals** | Tokens & embeddings · Transformer & attention · Pre-training, fine-tuning, RLHF · Prompting · Context windows & sampling · Limits & hallucination |
| 3 | **Agentic Harness** | What a harness is (loop, tools, permissions, context) · Tool schemas & execution sandboxes · Context management & compaction · Sub-agents & orchestration · Hooks, skills, MCP · Observability & evals |

v1 ships these three paths. More can be added any time from "New goal" (e.g. *RAG & Retrieval*).

Seed papers include e.g. *Attention Is All You Need* (2017), *ReAct* (2022), *Toolformer* (2023), *Generative Agents* (2023) — fetched live from arXiv by the Paper Search agent, not hard-coded.

---

## 9. Folder structure

```
Learning/
  PLAN.md
  backend/
    main.py              app factory, CORS, routers
    config.py            env: LLM_BRIDGE_PATH, YOUTUBE_API_KEY, SEARCH_API_KEY, DB_URL
    db/                  models.py, session.py, seed.py
    api/                 profile.py, requirements.py, paths.py, lessons.py, search.py, chat.py, home.py
    agents/              base.py, orchestrator.py, topic_identifier.py, curriculum_planner.py,
                         video_search.py, paper_search.py, curator.py, home_composer.py, tutor.py
    providers/           youtube.py, coursera.py, udemy.py, arxiv.py, semantic_scholar.py
    llm/                 client.py (Protocol), bridge_adapter.py, prompts/
    tests/
  frontend/
    src/pages/           Home, Setup, Lesson, Discover
    src/components/      ResourceCard, PathSpine, AskLLMPanel, AgentProgress, SourceBadge…
    src/api/             typed client
```

---

## 10. Delivery phases

| Phase | Scope | Done when |
|---|---|---|
| 0 | Review this plan + design | You approve / send changes |
| 1 | Backend skeleton: FastAPI, SQLite models, LLM-Bridge adapter, `/chat` streaming | Ask LLM works from curl |
| 2 | Agents 1–2 (Topic Identifier, Curriculum Planner) + requirement API + SSE progress | A requirement produces a stored path |
| 3 | Providers + agents 3–5 (search, papers, curator) | Each lesson has ranked resources |
| 4 | Frontend: Setup wizard, Home, Lesson view, Ask LLM panel | End-to-end in the browser |
| 5 | Discover page, saved items, Home Composer refresh | Search across sources works |
| 6 | Cold-boot seed for the 4 topics, tests, README | Fresh clone → `run` → full home page |

---

## 11. Risks

- **Coursera/Udemy** — links only, so no specific course cards for them in v1.
- **Plan usage limits / latency** — every agent step and every Ask LLM question uses your Claude plan. Generate module outlines first, lesson notes lazily on first open, then cache; use `haiku` for cheap steps; cache all search results in `resources` and refresh at most daily.
- **Hallucinated links** — YouTube URLs from web search are only kept if oEmbed confirms them; papers come from real APIs.
- **Only Claude is installed** — app works with Claude alone; other providers appear when their CLIs are installed.
- **Generated content accuracy** — every lesson links real sources; Tutor answers cite the lesson and resources; "Report issue" on lesson notes.

## 12. Decisions (2026-11-09)

1. LLM: LLM_Bridge at `D:\Y26\work_dir\LLM_Bridge`, provider `claude` (only one installed), models `sonnet` / `haiku`.
2. Cold boot: Agentic AI, LLM Fundamentals, Agentic Harness.
3. Coursera/Udemy: links only.
4. YouTube: no API key → bridge web search + oEmbed verification + search links.
5. Single user, local, no login.
