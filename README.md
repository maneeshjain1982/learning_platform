# Study Companion

A personal learning portal. Describe what you want to learn; a team of LLM agents builds a step-by-step
learning path, writes lesson notes, finds YouTube videos and research papers, and keeps a personalized home page.
An **Ask LLM** tutor is available on every lesson.

Runs locally for one person. LLM calls go through **LLM_Bridge** (`D:\Y26\work_dir\LLM_Bridge`) using your
signed-in Claude Code CLI, so **no API keys** are needed. See [PLAN.md](PLAN.md) for the design.

## Run it

Requirements: Python 3.10+, Node 18+, and the Claude Code CLI signed in (`claude` once, then log in).

**Easiest:** double-click **`run.bat`**. On first run it creates the Python environment and builds the frontend, then
starts the server and opens http://127.0.0.1:8000. Close the window (or press Ctrl+C) to stop it.
After changing frontend code, run `run.bat rebuild`. If port 8000 is already in use, it opens the running app instead.

Or manually:

```powershell
# one-time setup
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m pip install -e D:\Y26\work_dir\LLM_Bridge
cd frontend; npm install; npm run build; cd ..

# start (serves the app at http://127.0.0.1:8000)
.\run.ps1
```

On first start the app creates three starter paths — **Agentic AI**, **LLM Fundamentals**, **Agentic Harness** —
and fetches their papers from arXiv (each paper is kept only if arXiv's title matches).

**Frontend development** (hot reload): run the backend (`.\run.ps1`), then `cd frontend; npm run dev` and open
http://localhost:5173 (API calls are proxied to port 8000).

**Tests:** `.\.venv\Scripts\python -m pytest backend\tests` (offline: fake LLM, mocked network).

## How it works

| Agent | What it does | Uses |
|---|---|---|
| Topic Identifier | Turns your goal into core topics, prerequisites and search keywords | Claude (sonnet) |
| Curriculum Planner | Orders modules and lessons to fit your hours/weeks | Claude (sonnet) |
| Video Search | Finds YouTube videos per lesson; every URL is checked with YouTube oEmbed, unverifiable ones are dropped | Claude web search + oEmbed |
| Paper Search | Foundational papers named by Claude (verified on arXiv by id + title) plus an arXiv phrase search | Claude (haiku), arXiv, Semantic Scholar |
| Curator | Matches papers to lessons and explains each pick | Claude (haiku) |
| Home Composer | Today's focus note; refreshes the home page | Claude (haiku) |
| Lesson Writer | Writes lesson notes the first time you open a lesson | Claude (sonnet) |
| Tutor (Ask LLM) | Answers questions with the lesson, your level and the path as context (each can be turned off) | Claude (sonnet) |

Coursera and Udemy are **search links** (no public API). Everything is stored in `data/study.db` (SQLite).

## Interview prep

**Interview prep** in the top menu holds your interview companions. Click **New interview companion** and fill in:

- the role and company
- the job description (optional; without one, the agents research the role)
- your level and interview date
- the question bar and question types
- how many questions to write per skill area

The agents then:

1. **JD Analyst:** reads the job description.
2. **Role Researcher:** web-searches postings and interview guides, and checks every source link.
3. **Skill Mapper:** lists every skill and technology, marked must-have, important or nice-to-have.
4. **Prep Planner:** builds a study plan as a learning path, tagged "Interview prep" on Home. The video and paper agents fill it in.
5. **Question Writer:** writes questions with model answers, key points, follow-ups, red flags and sources. Papers are checked on arXiv by ID and title; dead links are removed.
6. **Coach:** writes what to do today.

A build takes about 10–15 minutes and 40–50 Claude calls.

On the companion page:

- **Skills & tech:** rate yourself 1–5 on each skill.
- **Questions:** filter, mark questions *Needs work* or *Confident*, edit, add your own, or **Generate more**.
- **Mock interview:** answer by typing and get a 1–5 score, what was missing, a stronger answer and a follow-up question. Questions are weighted toward your weak areas.

**Readiness** = 50% skill ratings + 30% mock scores + 20% prep plan done. Use **Edit configuration → Save and rebuild** after pasting a new job description.

## Customize your home page

- **My courses & links**: on Home, a path page, or **My links**, click **Add course or link** and paste any address (a Udemy or Coursera course, a YouTube playlist, docs…). Leave the title blank to use the page's own title. A link can be general or tied to one path, and can be hidden from Home.
- **Edit any course**: on **My paths**, edit, reorder, hide from Home or delete any path. On a path page, **Edit course** lets you rename, reorder, add and delete modules and lessons.
- **Create my own course**: on **My paths**, create an empty course and fill in modules and lessons yourself. The agents can still find videos and papers for it.
- Deleted starter paths stay deleted across restarts; **Settings → Restore starter paths** brings them back.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `claude` | `claude`, `chatgpt` or `gemini` (that CLI must be installed) |
| `LLM_MODEL` | `sonnet` | Planning, lesson notes, tutor, video search |
| `LLM_FAST_MODEL` | `haiku` | Curator, paper suggestions, focus note |
| `LLM_TIMEOUT` | `420` | Seconds per LLM call |
| `LLM_MAX_PARALLEL` | `3` | CLI processes running at once |
| `STUDY_DATA_DIR` | `./data` | Where `study.db` lives |

## Good to know

- Every agent step and every Ask LLM answer uses your Claude plan. Building a new path takes a few minutes
  (about 3 + 4×modules Claude calls); finding resources for one module takes 1–2 minutes.
- The bridge doesn't stream, so Ask LLM answers appear in one piece after a few seconds.
- Semantic Scholar often rate-limits requests without an API key; paper search then uses arXiv only.
- Windows Smart App Control blocks Rollup's native binary, so the frontend uses `@rollup/wasm-node`
  (see `overrides` in `frontend/package.json`).
