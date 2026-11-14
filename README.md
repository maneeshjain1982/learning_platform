# Study Companion

A personal knowledge base for AI engineering. Knowledge is organised by **domain** (Gen AI, LLM, Agentic AI, Voice AI,
and any domain the admin adds). Each topic gives an **executive summary** and the **best links to go deeper**:
YouTube, Coursera, university courses, docs, arXiv papers, Medium and engineering blogs. Each link is labelled with
its type and whether it's free, needs a login or is paid. For admins, a **Career** section holds jobs, interview prep
and FAANG questions.

Runs locally. LLM calls go through **LLM_Bridge** (`D:\Y26\work_dir\LLM_Bridge`) using your signed-in Claude Code
CLI, so **no API keys** are needed.

## Sign in

| Account | Username / password | Sees |
|---|---|---|
| Admin | `admin` / `admin` | Everything. Adds, edits and deletes domains, topics and links. Has **Career** |
| User | `user` / `user` | Home, Domains, Tech News and their own bookmarks. Career is hidden and blocked by the server |

Change a password in **Settings**. Domains are shared by both accounts; bookmarks are per account.

## Layout

Every page has two parts: a **left panel** to browse (sections and topics, news topics, Career pages) and the
**details on the right**. On a phone the left panel opens from the button at the top of the page.

The top menu has **Home**, **Domains**, **Tech News** and **Career** (admin), and a search box that searches every topic.
The round button on the right holds **Bookmarks**, **Settings** and **Sign out**.

## Domains

- **Pick a domain** from the top menu, Home, or the selector at the top of the left panel.
- **Left panel:** the domain's sections, each opening to its topics, plus a filter box.
- **A topic** shows:
  - an **executive summary**: what it is, the key points and why it matters
  - **Blogs & explainers**: plain-language posts (Medium, Hugging Face, Kaggle, well-known AI blogs), each with its
    level (Beginner, Intermediate, Advanced), reading time and whether it's free. Easiest first.
  - **Courses, videos & docs**: the other links, filterable by type (video, course, paper, docs…) and **Free only**
  - **Summarize this source** on any link, which writes a short AI summary from the page itself (papers get problem,
    method, results and limitations). Summaries are saved and shared.
  - **Bookmark**, and **Previous / Next** topic
- **First-time summaries:** a topic built from an outline gets its summary the first time anyone opens it (about a
  minute). If it has fewer than 3 links, more are found with web search at the same time. Every link is checked;
  dead ones are dropped.
- **Blog Scout:** the first time a topic with fewer than 2 blog posts is opened, Blog Scout finds 4-6 posts that
  explain it well (1-2 minutes). It prefers recent, free posts and skips SEO filler and vendor marketing.

**Admin tools:**
- **Add domain**, from the Domains menu, Home or the left panel. Give a name and scope; **Build the outline with AI**
  plans the sections and topics and writes each one with its links (several minutes).
- **Sections:** add, rename and delete them in the left panel.
- **Topics:** **Add topic**, with AI or written yourself; **Edit**; **Rewrite** the summary; **Find more links**;
  **Delete**.
- **Links:** **Add link** (type and access are worked out from the address), **Edit**, **Delete**.
- **Write N summaries** writes every draft topic in a domain now, instead of on first open.
- **Blogs:** **Find blogs** / **Find more blogs** on a topic; **Find blogs for all topics** on a domain. In the domain's
  **Edit**, add **trusted blogs** (one per line, `Name | link`) that Blog Scout checks first.

**Starting content:** on first start after the upgrade, the four domains were built from the existing content. Nothing
was re-researched. They run once; a domain the admin deletes doesn't come back.
- **Gen AI:** your own learning paths (e.g. the RAG app path)
- **LLM:** LLM Fundamentals and the other Claude Academy courses
- **Agentic AI:** Agentic AI, Agentic Harness and the Claude Academy agent builder track
- **Voice AI:** the Hindi and English voice content: technical modules, models, datasets, papers, courses and the launch
  playbook

## Tech News

- **Left panel:** your digest, its topics and the live Hacker News front page.
- **Topics and refresh:** pick topics and a time range. The LLM searches the web, writes one or two lines per story,
  and checks every link.

## Career (admin)

- **Hot Jobs:** roles, **country** (or Anywhere / Remote only), optional city and how many, then **Refresh**. You get
  open postings from the last 30 days, each with its JD broken down, plus the most-asked skills, which work as a filter.
- **Job search:**
  - **Your CV:** upload a PDF, Word file or text, or paste it. It's read on this computer; name, email, phone, address
    and profile links are removed before the AI sees it, and the file isn't kept. The AI writes a profile (title,
    years, level, domains, skills, roles to search for) that you can edit. **What the AI sees** shows the exact text.
  - **Matching my CV:** jobs that fit your profile, each with a **match score**, **why it fits** and **gaps**, best
    match first.
  - **Custom search:** a role, company or skills, or a domain.
  - **Filters:** years of experience, level, country and city; under **More filters**, work mode, company type,
    posted within, minimum salary, visa sponsorship and anything else.
- **Interview prep:** paste a JD, or press **Interview prep for this job** on any job. If you've added your CV and
  leave "Your background" empty, your CV is used, so the skills it doesn't show stand out. You get:
  - **Suggested topics:** the skills the role needs by area, each linked to the matching topics in your domains
  - **Questions:** questions with model answers, key points, follow-ups and checked sources. You can generate more or
    add your own.
  - **Mock interview:** answer by typing and get a score, what was missing, a stronger answer and a follow-up question
  - **Role & JD:** the JD breakdown and web research on the role
- **FAANG questions:** pick Google, Meta, Amazon, Apple, Netflix or Microsoft, a role and a domain. The LLM finds
  interview questions that were **publicly reported** (prep guides, Glassdoor, Blind, candidate write-ups), each with
  an answer outline and its source. Results are saved until you press **Refresh**.
- **Certifications:** AI certifications worth earning, with price, format and what each tests. **Refresh** looks for
  new ones.

All LLM research runs in the background; you can leave the page and come back.

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

**Frontend development** (hot reload): run the backend (`.\run.ps1`), then `cd frontend; npm run dev` and open
http://localhost:5173 (API calls are proxied to port 8000).

**Tests:** `.\.venv\Scripts\python -m pytest backend\tests` (offline: fake LLM, mocked network).

## How it is built

- **Data model:** domain → section → topic (executive summary) → source (link with type, access and an optional
  AI summary), in `data/study.db` (SQLite). Code: `backend/api/domains.py`, `backend/agents/domains.py`.
- **Link labels:** the type and access come from the address (`classify()`): YouTube is a free video, Coursera needs a
  login, Udemy is paid, Medium may be paywalled, university sites are free courses, arXiv is a free paper, and so on.
- **Old pages and data:** the old learning paths, progress, review Q&A and study plans are no longer shown, but their
  data is still in the database. Old links (`/paths`, `/claude`, `/voice`, `/upskill`, `/jobs`) redirect to the new
  pages.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `claude` | `claude`, `chatgpt` or `gemini` (that CLI must be installed) |
| `LLM_MODEL` | `sonnet` | Summaries, sources, research |
| `LLM_FAST_MODEL` | `haiku` | Short tasks |
| `LLM_TIMEOUT` | `420` | Seconds per LLM call |
| `LLM_MAX_PARALLEL` | `3` | CLI processes running at once |
| `STUDY_DATA_DIR` | `./data` | Where `study.db` lives |

## Good to know

- Every summary, link search and research run uses your Claude plan.
- A topic summary takes about a minute; with a link search, 1–3 minutes. A new AI-built domain takes several minutes.
- The bridge doesn't stream, so Ask LLM answers appear in one piece after a few seconds.
- Windows Smart App Control blocks Rollup's native binary, so the frontend uses `@rollup/wasm-node`
  (see `overrides` in `frontend/package.json`).
