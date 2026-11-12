# Interview Companion: plan (draft for review)

**Date:** 2026-11-10 · **Status:** implemented on 2026-11-10

**Decisions:**
1. No job description: the first companion, Agentic AI Architect, is built from web research.
2. Answers are typed only.
3. The prep plan shows on Home, tagged "Interview prep".
4. Question count is configurable (2–15 per area), and the question bar is configurable, defaulting to "Top AI company".
5. Every answer cites sources: papers checked on arXiv and links checked.

## 1. Goal

A new **Interview prep** section in Study Companion. You set up an "interview companion" by pasting a job description (or just a role title, such as *Agentic AI Architect*). The agents then:

1. Read the job description and research what the role needs in the market.
2. List every skill and technology required, with how important each one is.
3. Build a study plan (courses, videos and papers) timed to your interview date.
4. Write a question bank with model answers.
5. Run mock interviews that score your answers and point out what's missing.

The first companion I'll set up with it is **Agentic AI Architect**.

## 2. What you'll do in the app

| Step | Page | What happens |
|---|---|---|
| 1 | **Configure** (`/interview/new`) | Enter the role, company (optional), job description (optional), seniority, interview date, hours per week, your background (optional) and interview rounds. Click **Prepare**. |
| 2 | Live progress | Watch each agent work, the same way a new goal is built today (about 8–12 min). |
| 3 | **Overview** | Role summary, day countdown, readiness score, what to do today, and research findings with their sources. |
| 4 | **Skills & tech** | Every skill grouped by area and marked must-have, important or nice-to-have. Shows whether the job description asked for it and why. You rate yourself 1–5 on each, and your weakest must-haves get priority. |
| 5 | **Prep plan** | A learning path with modules and lessons, plus resources found by the existing agents and Coursera/Udemy links. It opens in the normal path and lesson pages, so Ask LLM and notes work there too. |
| 6 | **Questions** | Filter by area, type and difficulty. Reveal the model answer, key points and follow-ups. Mark each question *Needs work* or *Confident*, generate more, or add your own. |
| 7 | **Mock interview** | The companion picks questions, favouring weak areas. You type an answer and get a score, what was good, what was missing, a stronger answer, and a follow-up question the way a real interviewer would ask it. |
| 8 | **Edit** | Change the configuration (for example, paste a new job description) and rebuild. You can keep or replace the old questions. |

The new **Interview prep** menu item lists all your companions, so you can prepare for several roles or companies at the same time.

## 3. Agents

New agents use the same LLM Bridge (Claude) and show live progress like the current ones.

| # | Agent | Model | Does |
|---|---|---|---|
| 1 | **JD Analyst** | sonnet | Pulls responsibilities, required and nice-to-have skills, seniority signals and likely rounds out of the job description. Skipped when there is none. |
| 2 | **Role Researcher** | sonnet + web search | Researches current postings, interview reports and engineering blogs for the role title. Returns what is commonly expected and how interviews are structured, **with source links**. Links that don't open are dropped. |
| 3 | **Skill Mapper** | sonnet | Merges the job description and the research into one skill map. Each skill gets an area, importance, the evidence for it ("JD says…" or "8 of 10 postings…"), and how it is tested in interviews. |
| 4 | **Prep Planner** | sonnet | Turns the skill map into a learning path: modules weighted by importance and your self-ratings, fitted to the days left and your hours per week. |
| 5 | Video Search / Paper Search / Curator | existing | Find and check resources for each lesson, exactly as today. |
| 6 | **Question Writer** | sonnet, one batch per area | Writes questions across 5 types: concept, system design, scenario/trade-off, hands-on/coding, and behavioral/leadership. Each has a model answer, key points, follow-ups and *red flags* (answers that sink candidates). |
| 7 | **Mock Interviewer** | sonnet, on demand | Scores your answer against that question's key points (1–5) and gives feedback plus a follow-up. |
| 8 | **Coach** | haiku | Writes "what to do today" on the Overview from the countdown, your ratings and your weak answers. |

**Cost:** about 40–50 Claude calls per companion, mostly video search and question writing. A mock-interview answer is 1 call.

## 4. Draft skill map for Agentic AI Architect (the agents will refine this)

| Area | Skills and tech |
|---|---|
| LLM foundations | Transformers, tokens and context windows, sampling, reasoning models, prompt and context engineering, structured output, fine-tuning vs prompting vs RAG |
| Agent architecture patterns | ReAct, plan-and-execute, reflection, routing, orchestrator–workers, evaluator–optimizer, single- vs multi-agent, human-in-the-loop, long-running and durable agents |
| Tools and protocols | Function and tool calling, **MCP** (Model Context Protocol), **A2A** (agent-to-agent), tool design and permissions, computer and browser use |
| Frameworks and SDKs | LangGraph, LangChain, Claude Agent SDK, OpenAI Agents SDK, Microsoft AutoGen / Semantic Kernel, CrewAI, LlamaIndex, Google ADK; when to use none |
| Memory and knowledge | RAG design (chunking, hybrid search, reranking), vector DBs (pgvector, Pinecone, Weaviate), GraphRAG, short- and long-term agent memory, context compaction |
| Agent harness and runtime | Agent loop, state and checkpoints, retries and timeouts, sandboxing, queues, streaming, cost and latency budgets, caching |
| Evaluation and observability | Offline and online evals, LLM-as-judge, trajectory evals, benchmarks (SWE-bench, τ-bench), tracing (LangSmith, Langfuse, OpenTelemetry), regression gates |
| Safety, security and governance | Prompt injection, tool-permission design, guardrails, PII, audit trails, Responsible AI, EU AI Act basics |
| Platform and LLMOps | Model selection and routing, gateways, deployment on AWS Bedrock / Azure AI Foundry / Vertex AI, Kubernetes, CI/CD for prompts and agents, FinOps |
| System design | End-to-end designs such as support agents, coding agents and research agents; scaling, reliability and failure modes |
| Leadership (architect) | Build vs buy, reference architectures, ADRs, stakeholder communication, ROI of agent use cases, team enablement |

## 5. Data model (new SQLite tables)

| Table | Holds |
|---|---|
| `interview_preps` | Role, company, JD text, seniority, interview date, hours/week, background, rounds, notes, status, `path_id` (the prep learning path), research summary and sources (JSON) |
| `interview_skills` | prep, area, name, importance, evidence, `in_jd`, how it's tested, self-rating (1–5) |
| `interview_questions` | prep, skill, area, type, difficulty, question, model answer (Markdown), key points, follow-ups, red flags, status (new / needs work / confident), source (agent / you) |
| `practice_attempts` | question, your answer, score, feedback (Markdown), time |

`agent_runs` gets an `interview_id` column so progress tracking works the same way as today. Existing data is kept, using the same column-adding migration as last time.

## 6. API

- `POST /api/interviews` (configure and start the build) · `GET /api/interviews` · `GET/PATCH/DELETE /api/interviews/{id}` · `POST /api/interviews/{id}/rebuild`
- `PATCH /api/interview-skills/{id}` (self-rating)
- `GET /api/interviews/{id}/questions?area=&type=&difficulty=&status=` · `POST /api/interviews/{id}/questions/generate` · `POST /api/interviews/{id}/questions` (your own) · `PATCH/DELETE /api/interview-questions/{id}`
- `POST /api/interviews/{id}/mock/next` (picks a weighted question) · `POST /api/interview-questions/{id}/attempts` (score an answer) · `GET /api/interviews/{id}/attempts`

## 7. Screens (wireframes)

```
Interview prep (list)                      Configure
┌───────────────────────────────────┐     ┌──────────────────────────────────┐
│ Interview prep    [+ New companion]│     │ Role title  [Agentic AI Architect]│
│ ┌─────────────┐ ┌─────────────┐   │     │ Company     [optional]            │
│ │Agentic AI   │ │ …           │   │     │ Job description [ paste … ]       │
│ │Architect    │ │             │   │     │ Seniority (Senior/Lead/Principal) │
│ │18 days left │ │             │   │     │ Interview date [__]  Hours/wk [8] │
│ │Ready 42% ▓▓░│ │             │   │     │ Rounds ☑design ☑concept ☑behav…   │
│ └─────────────┘ └─────────────┘   │     │ Your background [optional]        │
└───────────────────────────────────┘     │ ☑ Research the role on the web     │
                                          │                   [Prepare]       │
                                          └──────────────────────────────────┘
Companion page
┌──────────────────────────────────────────────────────────────────┐
│ Agentic AI Architect · Acme · 18 days left · Readiness 42%        │
│ [Overview] [Skills & tech] [Prep plan] [Questions] [Mock interview]│
├──────────────────────────────────────────────────────────────────┤
│ Questions: Area ▾  Type ▾  Difficulty ▾  Status ▾   [+ Generate]  │
│ ▸ Design a multi-agent system for insurance claims…  System design│
│   [Show answer] [Practice] [Needs work | Confident] [Ask LLM]     │
└──────────────────────────────────────────────────────────────────┘
```

**Readiness** = 50% average self-rating on must-have skills, 30% average mock score per area (latest attempts), 20% plan lessons done.

## 8. Build order

1. **Backend:** models and migration, the agents and their schemas, orchestrator pipeline, API, tests with the fake LLM.
2. **Frontend:** Interview list, Configure, and the companion page with its 5 tabs, plus Mock interview.
3. **Live run:** set up **Agentic AI Architect** for real and review the quality of the skills and questions.
4. Update README and PLAN.md.

## 9. Risks

- **Web research quality:** Claude's web search can return thin or outdated results. Every source link is checked, and the job description always takes priority over research.
- **Answer quality:** model answers are written by the LLM. Each is marked "AI-written, check before relying on it", and you can edit any of them.
- **Plan usage:** a build costs about 40–50 calls. Questions are generated in batches, and "Generate more" is on demand.

## 10. Decisions (original questions, now answered above)

1. **Job description:** do you have a specific one for the Agentic AI Architect role, or should the first companion be built from web research of the role in general?
2. **Practice answers:** typed answers only, or should voice answers (browser speech-to-text) also be in scope?
3. **Plan on Home:** should the prep plan appear on Home like other learning paths? My recommendation is yes, tagged "Interview prep".
4. **Question count:** about 60 questions at first (about 6 per area), with more on demand. Is that enough?
