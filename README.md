# Study Companion

A personal learning portal. Describe what you want to learn; a team of LLM agents builds a step-by-step
learning path, writes lesson notes, finds YouTube videos and research papers, and keeps a personalized home page.
An **Ask LLM** tutor is available on every lesson.

Runs locally. LLM calls go through **LLM_Bridge** (`D:\Y26\work_dir\LLM_Bridge`) using your
signed-in Claude Code CLI, so **no API keys** are needed. See [PLAN.md](PLAN.md) for the design.

## Sign in

There are two accounts. Each has its own home page, paths, progress, links, notes and settings.

| Account | Username / password | Sees |
|---|---|---|
| Admin | `admin` / `admin` | Everything, including **Career** (certifications, hot jobs) and **Upskill Prep** |
| User | `user` / `user` | Learning, Tech News and Library. Career, jobs and Upskill Prep are hidden and blocked by the server |

Change a password in **Settings**. The data from before sign-in was added belongs to the admin; the user account starts
with its own copy of the starter paths. Review questions and paper summaries are shared; marks are per account.

## Menu

The top menu has **Home**, **Learning** (My paths, Claude learning, Voice ASR/NLU, Upskill Prep, New goal),
**Tech News**, **Career** (admin) and **Library** (Discover, My links). The round button on the right shows who is
signed in, with Settings and Sign out. On a phone, the groups open inside the ☰ menu.

## Home

A short page of cards: Continue learning, This week, My paths, Tech News, Videos & papers for the current module,
My links and (admin) Hot jobs. **Customize** turns cards on or off and changes their order, per account.

## Tech News

**Tech News** shows live Hacker News headlines (public API, no key) next to your own digest. Pick topics (AI & LLMs,
Agents & tools, Speech & NLP, Developer tools, Cloud, Mobile, Security, Chips) and a time range, then **Get my digest**:
the LLM searches the web, writes one or two lines per story and every link is checked. **Hide** removes a story.

## Paper summaries

Every paper (lesson pages, Discover, Voice papers) has **Summarize**. The LLM reads the paper on arXiv (full text when
it can open it, otherwise the abstract, and says which) and writes a TL;DR, problem, method, key results with numbers,
limitations and why it matters. Summaries are saved and shared; the admin can **Edit**, **Regenerate** or **Delete** them.

## Editing and deleting content

- Your own content: paths, modules, lessons, links, lesson notes (**Edit** / **Delete** under the notes), generated
  utterances, and items found by research runs (news, certification changes, jobs, What's new) can be edited or removed.
- Built-in lists (Voice models, datasets, papers and courses; certifications; Claude courses): the admin can edit or
  delete an item for every account; the user account can hide items for itself. **Restore original** undoes it.
- Review questions: any account marks them; the admin can edit or delete them.

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

## Upskill Prep (admin)

**Upskill Prep** (under **Learning** in the top menu) holds your prep companions for a target role. Click **New Upskill Prep companion** and fill in:

- the role and company
- the job description (optional; without one, the agents research the role)
- your level and interview date
- the question bar and question types
- how many questions to write per skill area

The agents then:

1. **JD Analyst:** reads the job description.
2. **Role Researcher:** web-searches postings and interview guides, and checks every source link.
3. **Skill Mapper:** lists every skill and technology, marked must-have, important or nice-to-have.
4. **Prep Planner:** builds a study plan as a learning path, tagged "Upskill Prep" on Home. The video and paper agents fill it in.
5. **Question Writer:** writes questions with model answers, key points, follow-ups, red flags and sources. Papers are checked on arXiv by ID and title; dead links are removed.
6. **Coach:** writes what to do today.

A build takes about 10–15 minutes and 40–50 Claude calls.

On the companion page:

- **Skills & tech:** rate yourself 1–5 on each skill.
- **Questions:** filter, mark questions *Needs work* or *Confident*, edit, add your own, or **Generate more**.
- **Mock interview:** answer by typing and get a 1–5 score, what was missing, a stronger answer and a follow-up question. Questions are weighted toward your weak areas.

**Readiness** = 50% skill ratings + 30% mock scores + 20% prep plan done. Use **Edit configuration → Save and rebuild** after pasting a new job description.

## Claude learning

The **Claude learning** tab lists Anthropic's free courses on [Claude Academy](https://academy.claude.com).

- **Agent builder track:** 11 courses in the order to take them, with lesson lists, a status for each course, and **Add track to My paths** to study them lesson by lesson.
- **Review Q&A:** on each track course, **Review Q&A** opens questions for every lesson. The LLM writes them, checks facts against Anthropic's docs and links the sources. Reveal an answer, then mark it *Know it* or *Review again*. **Write new questions** replaces the set (your marks stay on questions that come back unchanged).
- **New updates:** **Refresh** has the LLM search the web for recent Claude, Claude Code, MCP and agent news. Dead links are dropped.

## Voice ASR/NLU (Hindi and English)

The **Voice ASR/NLU** tab covers adding a language to a voice assistant such as Bixby. Switch between **Hindi** (adding hi-IN) and **English** (adding an English locale such as en-IN, and accent robustness) at the top. Everything was researched and link-checked; arXiv IDs were checked against arXiv, and licences come from the model and dataset cards.

Each language has the same sections:

- **Overview & skills:** the competencies needed, with the level each needs. Rate yourself to see your gaps.
- **Courses & modules:** courses in order, and 12 technical modules (speech basics, ASR models, text normalization, LM and biasing, on-device, intent/slot NLU, code-mixing or accents, entities, LLM NLU, data, testing, launch). Each module has **Review Q&A**, and **Add modules to My paths** turns them into a study path.
- **Models & datasets:** the best open and commercial ASR models (with WER from the named source), NLU encoders, tools, and datasets with licences.
- **Research papers:** reading list grouped by topic.
- **Launch playbook:** 10 phases with steps to tick off, outputs, owners and pitfalls.
- **Testing:** ASR, NLU and end-to-end metrics, the slices to report, and test-set design.
- **Data:** the variability matrix, how to get data, and how to generate it.
- **Utterance generator:** enter an intent and slots; the LLM writes utterances in the language's styles (Hindi: Devanagari, romanized, Hinglish; English: standard, Indian English, casual, ASR-like) with slot labels. Export as CSV, JSONL or Bixby-style Aligned NL.
- **What's new:** **Refresh** finds new models, datasets, papers and news.

To add another language, add a content module like `backend/english_voice.py` and register it in `backend/voice_langs.py`.

## Career (admin)

- **Certifications:** a researched list of Agentic AI and Generative AI certifications (Anthropic, Google Cloud, Microsoft, NVIDIA, AWS, Databricks, plus courses with certificates), grouped by level, with price, format and what each one tests. **Refresh** looks for new certifications and changes to these.
- **Hot jobs:** set the roles and location, then **Find jobs**. The LLM finds open postings from the last 30 days, breaks down each job description, and lists the skills asked for most. **Prepare in Upskill Prep** opens Upskill Prep with the role, company and JD filled in.

All LLM research runs in the background; you can leave the page and come back.

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
