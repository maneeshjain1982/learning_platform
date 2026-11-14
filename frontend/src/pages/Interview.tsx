// One Interview Prep: suggested topics (linked to your domains), questions, mock interview, and the role/JD.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  api, type Attempt, type Difficulty, type InterviewDetail, type IQuestion, type QStatus, type QType, type Reference, type Skill,
} from "../api";
import { useAsk } from "../components/AskLLM";
import { IconButton, Modal } from "../components/Manage";
import { AgentSteps, ErrorBox, Icon, Markdown, Thinking } from "../components/ui";
import { CareerMain } from "./Jobs";
import { QTYPES, QTYPE_LABEL } from "./InterviewSetup";

const TABS = [
  ["topics", "Suggested topics"], ["questions", "Questions"], ["mock", "Mock interview"], ["role", "Role & JD"],
] as const;
type Tab = (typeof TABS)[number][0];

const IMPORTANCE = {
  must: { label: "Must-have", cls: "bg-yt-bg text-yt-fg" },
  important: { label: "Important", cls: "bg-accent-soft text-accent-dark" },
  nice: { label: "Nice to have", cls: "bg-[#F1F3F6] text-body" },
};
const STATUS: Record<QStatus, { label: string; cls: string }> = {
  new: { label: "Not practised", cls: "bg-[#F1F3F6] text-muted" },
  needs_work: { label: "Needs work", cls: "bg-yt-bg text-yt-fg" },
  confident: { label: "Confident", cls: "bg-ok-soft text-ok-dark" },
};
const DIFF_CLS: Record<Difficulty, string> = { medium: "bg-[#F1F3F6] text-body", hard: "bg-pp-bg text-pp-fg", expert: "bg-ink text-white" };

export default function InterviewPage() {
  const id = Number(useParams().id);
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const raw = params.get("tab") as Tab | null;
  const tab: Tab = raw && TABS.some(([v]) => v === raw) ? raw : "topics";
  const go = (t: Tab, extra: Record<string, string> = {}) => setParams({ tab: t, ...extra });

  const prep = useQuery({ queryKey: ["interview", id], queryFn: () => api.interview(id) });
  const runId = prep.data?.last_run?.status === "running" ? prep.data.last_run.id : null;
  const run = useQuery({
    queryKey: ["run", runId], queryFn: () => api.run(runId!), enabled: !!runId,
    refetchInterval: (q) => (q.state.data?.status === "running" || !q.state.data ? 2500 : false),
  });
  useEffect(() => {
    if (!runId) return;
    const t = setInterval(() => qc.invalidateQueries({ queryKey: ["interview", id] }), 6000);
    return () => clearInterval(t);
  }, [runId, id, qc]);
  useEffect(() => {
    if (run.data && run.data.status !== "running") qc.invalidateQueries();
  }, [run.data?.status, qc]); // eslint-disable-line react-hooks/exhaustive-deps

  if (prep.isLoading) return <CareerMain><Thinking label="Loading…" /></CareerMain>;
  if (prep.isError) return <CareerMain><ErrorBox error={prep.error} onRetry={() => prep.refetch()} /></CareerMain>;
  const p = prep.data!;
  const liveRun = run.data ?? p.last_run;
  const running = liveRun?.status === "running";

  return (
    <CareerMain>
      <Header p={p} />
      {liveRun && (running || liveRun.status === "failed") && (
        <section aria-labelledby="run-h" className="card p-5 flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h2 id="run-h" className="font-semibold flex-1">{running ? "Preparing your interview kit" : "The last run had a problem"}</h2>
            {running && <Thinking label="Working" />}
          </div>
          {running && <p className="text-sm text-muted">About 5–10 minutes. Results appear in the tabs below as each step finishes.</p>}
          <AgentSteps steps={liveRun.steps.filter((s) => s.agent !== "coach")} />
          {liveRun.error && <ErrorBox error={liveRun.error} />}
        </section>
      )}

      <div role="tablist" aria-label="Interview prep" className="flex flex-wrap gap-1 border-b border-line">
        {TABS.map(([v, l]) => (
          <button key={v} type="button" role="tab" aria-selected={tab === v} onClick={() => go(v)}
            className={`px-4 py-3 -mb-px border-b-2 font-semibold ${tab === v ? "border-accent text-accent-dark" : "border-transparent text-body hover:text-ink"}`}>
            {l}{v === "questions" && p.stats.questions ? ` (${p.stats.questions})` : ""}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {tab === "topics" && <Topics p={p} go={go} />}
        {tab === "questions" && <Questions p={p} running={running} go={go} initialArea={params.get("area") ?? ""} />}
        {tab === "mock" && <Mock p={p} initialQ={Number(params.get("q")) || null} />}
        {tab === "role" && <Role p={p} />}
      </div>
    </CareerMain>
  );
}

function Header({ p }: { p: InterviewDetail }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const del = useMutation({
    mutationFn: () => api.deleteInterview(p.id, true),
    onSuccess: () => { qc.invalidateQueries(); navigate("/career/prep"); },
  });
  return (
    <div className="flex flex-col gap-2">
      <h1 className="h-display text-3xl">{p.role_title}</h1>
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
        {p.company && <span className="font-semibold text-body">{p.company}</span>}
        <span className="chip bg-[#F1F3F6] text-body capitalize">{p.seniority}</span>
        <span className="chip bg-[#F1F3F6] text-body">{p.question_bar === "top_ai" ? "Top AI company bar" : p.question_bar === "big_tech" ? "Big tech bar" : "Standard bar"}</span>
        {!p.jd_text && <span className="chip bg-[#F1F3F6] text-body">No JD: based on role research</span>}
      </div>
      <div className="flex flex-wrap gap-2 pt-1">
        <Link to={`/career/prep/${p.id}/edit`} className="btn-outline btn-sm"><Icon.edit size={15} /> Edit</Link>
        <button type="button" className="btn-outline btn-sm" disabled={del.isPending}
          onClick={() => { if (confirm(`Delete the interview prep for "${p.role_title}" with its questions?`)) del.mutate(); }}>
          <Icon.trash size={15} /> Delete
        </button>
      </div>
      {del.isError && <ErrorBox error={del.error} />}
    </div>
  );
}

// ---------------------------------------------------------------- suggested topics

function Topics({ p, go }: { p: InterviewDetail; go: (t: Tab, extra?: Record<string, string>) => void }) {
  const groups = useMemo(() => {
    const m = new Map<string, Skill[]>();
    p.skills.forEach((s) => m.set(s.area, [...(m.get(s.area) ?? []), s]));
    return [...m.entries()];
  }, [p.skills]);
  const names = p.skills.map((s) => s.name);
  const match = useQuery({ queryKey: ["topic-match", p.id, names], queryFn: () => api.matchTopics(names), enabled: names.length > 0 });
  if (!p.skills.length) return <p className="card p-6 text-muted">The skills appear here once the job description is read.</p>;
  return (
    <div className="flex flex-col gap-5">
      <p className="text-body">What to study for this role, grouped by area. Each skill links to the matching topics in your domains.</p>
      {groups.map(([area, skills]) => (
        <section key={area} aria-label={area} className="card p-5 flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-3 mb-1">
            <h2 className="h-display text-lg flex-1">{area}</h2>
            <button type="button" className="btn-outline btn-sm" onClick={() => go("questions", { area })}>Questions</button>
          </div>
          <ul className="flex flex-col divide-y divide-[#EEF0F3]">
            {skills.map((s) => {
              const imp = IMPORTANCE[s.importance];
              const hits = match.data?.[s.name] ?? [];
              return (
                <li key={s.id} className="py-3 grid gap-x-6 gap-y-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                  <div className="flex flex-col gap-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold">{s.name}</h3>
                      <span className={`chip ${imp.cls}`}>{imp.label}</span>
                      {s.in_jd && <span className="chip bg-ok-soft text-ok-dark">In the JD</span>}
                    </div>
                    {s.how_tested && <p className="text-[13px] text-muted"><strong className="text-body">How it's tested:</strong> {s.how_tested}</p>}
                  </div>
                  <div className="flex flex-col gap-1 min-w-0">
                    {match.isLoading && <span className="text-sm text-muted">Finding topics…</span>}
                    {hits.map((t) => (
                      <Link key={t.id} to={`/d/${t.domain.slug}/t/${t.id}`} className="group flex items-start gap-2 text-sm">
                        <Icon.book size={14} className="mt-[3px] shrink-0 text-accent" />
                        <span className="min-w-0"><span className="font-medium group-hover:text-accent">{t.title}</span>
                          <span className="text-muted"> · {t.domain.name}</span></span>
                      </Link>
                    ))}
                    {!match.isLoading && hits.length === 0 && (
                      <Link to={`/search?q=${encodeURIComponent(s.name)}`} className="text-sm text-muted hover:text-accent">No topic yet · search the domains</Link>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- role and JD

function Role({ p }: { p: InterviewDetail }) {
  const r = p.research;
  const jd = p.jd_analysis;
  if (!r && !jd) return <p className="card p-6 text-muted">The role research appears here once it's done.</p>;
  return (
    <div className="flex flex-wrap gap-6">
      {jd && (
        <section aria-labelledby="jd-h" className="card flex-[1_1_420px] p-6 flex flex-col gap-3">
          <h2 id="jd-h" className="h-display text-xl">From the job description</h2>
          <p className="text-body">{jd.role_summary}</p>
          <ListBlock title="Responsibilities" items={jd.responsibilities} />
          <ListBlock title="Required" items={jd.required_skills} />
          <ListBlock title="Nice to have" items={jd.nice_to_have} />
          <ListBlock title="Likely rounds" items={jd.likely_rounds} />
        </section>
      )}
      {r && (
        <section aria-labelledby="res-h" className="card flex-[1_1_420px] p-6 flex flex-col gap-3">
          <h2 id="res-h" className="h-display text-xl">What the role needs</h2>
          <p className="text-body">{r.role_summary}</p>
          <ListBlock title="How the interviews usually run" items={r.interview_format} />
          <ListBlock title="Trends interviewers expect you to know" items={r.trends} />
          {r.sources.length > 0 && (
            <div>
              <h3 className="font-semibold mb-1.5">Sources</h3>
              <ul className="flex flex-col gap-1.5 text-sm">
                {r.sources.map((src) => (
                  <li key={src.url}><a href={src.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">{src.title}</a>
                    {!src.verified && <span className="text-muted"> · site blocks automatic link checks</span>}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <h3 className="font-semibold mb-1">{title}</h3>
      <ul className="list-disc pl-5 text-body text-[15px] flex flex-col gap-0.5">{items.map((i) => <li key={i}>{i}</li>)}</ul>
    </div>
  );
}

// ---------------------------------------------------------------- questions

function Questions({ p, running, go, initialArea }: {
  p: InterviewDetail; running: boolean; go: (t: Tab, extra?: Record<string, string>) => void; initialArea: string;
}) {
  const [area, setArea] = useState(initialArea);
  const [qtype, setQtype] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [status, setStatus] = useState("");
  const [text, setText] = useState("");
  const [adding, setAdding] = useState(false);
  const [gen, setGen] = useState(false);
  const filters = { area, qtype, difficulty, status };
  const list = useQuery({ queryKey: ["questions", p.id, filters, p.stats.questions], queryFn: () => api.questions(p.id, filters) });
  const shown = (list.data ?? []).filter((q) => !text || q.question.toLowerCase().includes(text.toLowerCase()) || (q.skill_name ?? "").toLowerCase().includes(text.toLowerCase()));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <Select id="f-area" label="Area" value={area} onChange={setArea} options={[["", "All areas"], ...p.areas.map((a) => [a, a] as [string, string])]} />
        <Select id="f-type" label="Type" value={qtype} onChange={setQtype} options={[["", "All types"], ...QTYPES.map((q) => [q.value, q.label] as [string, string])]} />
        <Select id="f-diff" label="Difficulty" value={difficulty} onChange={setDifficulty} options={[["", "Any"], ["medium", "Medium"], ["hard", "Hard"], ["expert", "Expert"]]} />
        <Select id="f-st" label="Status" value={status} onChange={setStatus} options={[["", "Any"], ["new", "Not practised"], ["needs_work", "Needs work"], ["confident", "Confident"]]} />
        <div className="flex flex-col gap-1 flex-1 min-w-[180px]">
          <label htmlFor="f-q" className="text-sm font-semibold">Search</label>
          <input id="f-q" type="search" className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. MCP, memory, evals" />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm text-muted flex-1">{shown.length} question{shown.length === 1 ? "" : "s"} · answers are AI-written: check them against the linked sources.</p>
        <button type="button" className="btn-outline btn-sm" onClick={() => setAdding(true)}><Icon.plus size={15} /> Add my own</button>
        <button type="button" className="btn-primary btn-sm" disabled={running} onClick={() => setGen(true)}><Icon.refresh size={15} /> Generate more</button>
      </div>
      {list.isLoading && <Thinking label="Loading questions…" />}
      {list.isError && <ErrorBox error={list.error} />}
      {!list.isLoading && shown.length === 0 && (
        <p className="card p-6 text-muted">{running ? "The Question Writer is still working: questions appear here as each area finishes." : "No questions match these filters."}</p>
      )}
      <ol className="flex flex-col gap-3">
        {shown.map((q) => <QuestionCard key={q.id} q={q} prepId={p.id} onPractice={() => go("mock", { q: String(q.id) })} />)}
      </ol>
      {adding && <Modal title="Add my own question" onClose={() => setAdding(false)}><AddQuestion p={p} onDone={() => setAdding(false)} /></Modal>}
      {gen && <Modal title="Generate more questions" onClose={() => setGen(false)}><Generate p={p} defaultArea={area} onDone={() => setGen(false)} /></Modal>}
    </div>
  );
}

function Select({ id, label, value, onChange, options }: { id: string; label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold">{label}</label>
      <select id={id} className="input w-auto max-w-[240px]" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );
}

function QChips({ q }: { q: IQuestion }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="chip bg-[#F1F3F6] text-body">{q.area}</span>
      <span className="chip bg-accent-soft text-accent-dark">{QTYPE_LABEL[q.qtype]}</span>
      <span className={`chip capitalize ${DIFF_CLS[q.difficulty]}`}>{q.difficulty}</span>
      {q.skill_name && <span className="text-xs text-muted">{q.skill_name}</span>}
      {q.source === "user" && <span className="chip bg-[#F1F3F6] text-body">Yours</span>}
      <span className={`chip ${STATUS[q.status].cls}`}>{STATUS[q.status].label}</span>
    </div>
  );
}

function QuestionCard({ q, prepId, onPractice }: { q: IQuestion; prepId: number; onPractice: () => void }) {
  const qc = useQueryClient();
  const { ask } = useAsk();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["questions", prepId] }); qc.invalidateQueries({ queryKey: ["interview", prepId] }); };
  const m = useMutation({ mutationFn: (fn: () => Promise<unknown>) => fn(), onSuccess: refresh });
  const setStatus = (s: QStatus) => m.mutate(() => api.updateQuestion(q.id, { status: q.status === s ? "new" : s }));

  return (
    <li className="card p-5 flex flex-col gap-3">
      <QChips q={q} />
      <h3 className="text-[17px] font-semibold leading-snug">{q.question}</h3>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className="btn-outline btn-sm" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Hide answer" : "Show answer"}</button>
        <button type="button" className="btn-primary btn-sm" onClick={onPractice}>Practise</button>
        <button type="button" aria-pressed={q.status === "needs_work"} onClick={() => setStatus("needs_work")}
          className={`btn-sm btn border ${q.status === "needs_work" ? "bg-yt-bg text-yt-fg border-[#F5C2BE]" : "bg-white border-line2"}`}>Needs work</button>
        <button type="button" aria-pressed={q.status === "confident"} onClick={() => setStatus("confident")}
          className={`btn-sm btn border ${q.status === "confident" ? "bg-ok-soft text-ok-dark border-ok" : "bg-white border-line2"}`}><Icon.check size={14} /> Confident</button>
        <button type="button" className="btn-outline btn-sm" onClick={() => ask(`Help me prepare for this interview question. Walk me through how a strong candidate would structure the answer:\n\n${q.question}`)}>
          <Icon.chat size={15} /> Ask LLM
        </button>
        <span className="flex-1" />
        {q.last_score != null && <span className="text-sm text-muted">Last mock score {q.last_score}/5</span>}
        <IconButton label="Edit question" onClick={() => setEditing(true)}><Icon.edit size={15} /></IconButton>
        <IconButton danger label="Delete question" onClick={() => { if (confirm("Delete this question?")) m.mutate(() => api.deleteQuestion(q.id)); }}><Icon.trash size={15} /></IconButton>
      </div>
      {m.isError && <ErrorBox error={m.error} />}
      {open && <AnswerBlock q={q} />}
      {editing && <Modal title="Edit question" onClose={() => setEditing(false)}><EditQuestion q={q} onDone={() => { setEditing(false); refresh(); }} /></Modal>}
    </li>
  );
}

function AnswerBlock({ q }: { q: IQuestion }) {
  return (
    <div className="flex flex-col gap-4 pt-3 border-t border-[#EEF0F3]">
      {q.answer_md ? <Markdown>{q.answer_md}</Markdown> : <p className="text-muted">No model answer yet. Click Edit to write one.</p>}
      <div className="grid gap-4 md:grid-cols-3">
        <Bullets title="Key points to hit" items={q.key_points} />
        <Bullets title="Likely follow-ups" items={q.follow_ups} />
        <Bullets title="Red flags to avoid" items={q.red_flags} />
      </div>
      <References refs={q.references ?? []} />
    </div>
  );
}

function Bullets({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="rounded-xl bg-ground p-4">
      <h4 className="font-semibold mb-1.5">{title}</h4>
      <ul className="list-disc pl-5 text-sm text-body flex flex-col gap-1">{items.map((i) => <li key={i}>{i}</li>)}</ul>
    </div>
  );
}

function References({ refs }: { refs: Reference[] }) {
  if (!refs.length) return <p className="text-[13px] text-muted">No sources survived the link check for this answer.</p>;
  return (
    <div>
      <h4 className="font-semibold mb-1.5">Sources</h4>
      <ol className="flex flex-col gap-1.5 text-sm list-decimal pl-5">
        {refs.map((r) => (
          <li key={r.url}>
            <span className={`chip mr-1.5 ${r.kind === "paper" ? "bg-pp-bg text-pp-fg" : "bg-[#F1F3F6] text-body"}`}>{r.kind === "paper" ? "Paper" : "Docs / web"}</span>
            <a href={r.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">{r.title}</a>
            {r.kind === "paper" && (r.authors || r.year) && <span className="text-muted"> · {[r.authors?.split(",").slice(0, 2).join(","), r.year].filter(Boolean).join(" · ")}</span>}
            <span className="text-muted text-xs"> · {r.verified ? (r.kind === "paper" ? "checked on arXiv" : "link checked") : "site blocks link checks"}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function EditQuestion({ q, onDone }: { q: IQuestion; onDone: () => void }) {
  const [question, setQuestion] = useState(q.question);
  const [answer, setAnswer] = useState(q.answer_md ?? "");
  const [points, setPoints] = useState((q.key_points ?? []).join("\n"));
  const save = useMutation({
    mutationFn: () => api.updateQuestion(q.id, { question, answer_md: answer, key_points: points.split("\n").map((s) => s.trim()).filter(Boolean) }),
    onSuccess: onDone,
  });
  return (
    <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <label htmlFor="eq-q" className="label text-sm">Question</label>
      <textarea id="eq-q" className="input min-h-[72px]" required minLength={5} value={question} onChange={(e) => setQuestion(e.target.value)} />
      <label htmlFor="eq-a" className="label text-sm">Model answer (Markdown)</label>
      <textarea id="eq-a" className="input min-h-[180px] font-mono text-sm" value={answer} onChange={(e) => setAnswer(e.target.value)} />
      <label htmlFor="eq-k" className="label text-sm">Key points (one per line, used to grade mock answers)</label>
      <textarea id="eq-k" className="input min-h-[96px]" value={points} onChange={(e) => setPoints(e.target.value)} />
      {save.isError && <ErrorBox error={save.error} />}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-outline" onClick={onDone}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={save.isPending}>Save</button>
      </div>
    </form>
  );
}

function AddQuestion({ p, onDone }: { p: InterviewDetail; onDone: () => void }) {
  const qc = useQueryClient();
  const [question, setQuestion] = useState("");
  const [area, setArea] = useState(p.areas[0] ?? "My questions");
  const [qtype, setQtype] = useState<QType>("concept");
  const [difficulty, setDifficulty] = useState<Difficulty>("hard");
  const [answer, setAnswer] = useState("");
  const save = useMutation({
    mutationFn: () => api.addQuestion(p.id, { question, area, qtype, difficulty, answer_md: answer }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["questions", p.id] }); qc.invalidateQueries({ queryKey: ["interview", p.id] }); onDone(); },
  });
  return (
    <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <label htmlFor="aq-q" className="label text-sm">Question</label>
      <textarea id="aq-q" className="input min-h-[72px]" required minLength={5} value={question} onChange={(e) => setQuestion(e.target.value)}
        placeholder="e.g. A question a recruiter or friend told you they ask" autoFocus />
      <div className="grid gap-3 sm:grid-cols-3">
        <Select id="aq-a" label="Area" value={area} onChange={setArea} options={[...p.areas, "My questions"].filter((v, i, a) => a.indexOf(v) === i).map((a) => [a, a])} />
        <Select id="aq-t" label="Type" value={qtype} onChange={(v) => setQtype(v as QType)} options={QTYPES.map((q) => [q.value, q.label])} />
        <Select id="aq-d" label="Difficulty" value={difficulty} onChange={(v) => setDifficulty(v as Difficulty)} options={[["medium", "Medium"], ["hard", "Hard"], ["expert", "Expert"]]} />
      </div>
      <label htmlFor="aq-ans" className="label text-sm">Your notes or model answer (optional)</label>
      <textarea id="aq-ans" className="input min-h-[96px]" value={answer} onChange={(e) => setAnswer(e.target.value)} />
      {save.isError && <ErrorBox error={save.error} />}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-outline" onClick={onDone}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={save.isPending}>Add question</button>
      </div>
    </form>
  );
}

function Generate({ p, defaultArea, onDone }: { p: InterviewDetail; defaultArea: string; onDone: () => void }) {
  const qc = useQueryClient();
  const [area, setArea] = useState(defaultArea);
  const [qtype, setQtype] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [count, setCount] = useState(6);
  const gen = useMutation({
    mutationFn: () => api.generateQuestions(p.id, { area: area || undefined, qtype: (qtype || undefined) as QType | undefined,
      difficulty: (difficulty || undefined) as Difficulty | undefined, count }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["interview", p.id] }); onDone(); },
  });
  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); gen.mutate(); }}>
      <p className="text-sm text-muted">The Question Writer avoids repeating questions you already have, and checks every source link. Progress shows at the top of the page.</p>
      <div className="grid gap-3 sm:grid-cols-3">
        <Select id="g-a" label="Area" value={area} onChange={setArea} options={[["", "Spread across areas"], ...p.areas.map((a) => [a, a] as [string, string])]} />
        <Select id="g-t" label="Type" value={qtype} onChange={setQtype} options={[["", "Your configured types"], ...QTYPES.map((q) => [q.value, q.label] as [string, string])]} />
        <Select id="g-d" label="Difficulty" value={difficulty} onChange={setDifficulty} options={[["", "Match the bar"], ["medium", "Medium"], ["hard", "Hard"], ["expert", "Expert"]]} />
      </div>
      <div className="flex flex-col gap-1 max-w-[320px]">
        <label htmlFor="g-n" className="label text-sm">How many: {count}</label>
        <input id="g-n" type="range" min={1} max={20} value={count} onChange={(e) => setCount(Number(e.target.value))} className="accent-accent" />
      </div>
      {gen.isError && <ErrorBox error={gen.error} />}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-outline" onClick={onDone}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={gen.isPending}>Generate</button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- mock interview

function Mock({ p, initialQ }: { p: InterviewDetail; initialQ: number | null }) {
  const qc = useQueryClient();
  const [area, setArea] = useState("");
  const [qtype, setQtype] = useState("");
  const [seen, setSeen] = useState<number[]>([]);
  const [current, setCurrent] = useState<IQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<(Attempt & { question: IQuestion }) | null>(null);
  const [showModel, setShowModel] = useState(false);

  const show = (q: IQuestion) => { setCurrent(q); setAnswer(""); setResult(null); setShowModel(false); setSeen((s) => [...s, q.id]); };
  const next = useMutation({
    mutationFn: () => api.mockNext(p.id, { area: area || undefined, qtype: (qtype || undefined) as QType | undefined, exclude: seen }),
    onSuccess: show,
  });
  useEffect(() => {
    if (initialQ) api.questions(p.id).then((all) => { const q = all.find((x) => x.id === initialQ); if (q) show(q); });
  }, [initialQ, p.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = useMutation({
    mutationFn: () => api.submitAttempt(current!.id, answer),
    onSuccess: (r) => { setResult(r); qc.invalidateQueries({ queryKey: ["interview", p.id] }); qc.invalidateQueries({ queryKey: ["questions", p.id] }); qc.invalidateQueries({ queryKey: ["attempts", p.id] }); },
  });
  const history = useQuery({ queryKey: ["attempts", p.id], queryFn: () => api.attempts(p.id) });

  if (!p.stats.questions) return <p className="card p-6 text-muted">There are no questions yet. They appear once the Question Writer finishes.</p>;

  return (
    <div className="flex flex-col gap-5">
      <div className="card p-5 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[240px]">
          <h2 className="h-display text-xl">Mock interview</h2>
          <p className="text-sm text-muted">Questions favour your weak spots: “needs work”, low self-ratings and low past scores. Answer as you would out loud: structure first, then depth.</p>
        </div>
        <Select id="m-a" label="Area" value={area} onChange={setArea} options={[["", "Any area"], ...p.areas.map((a) => [a, a] as [string, string])]} />
        <Select id="m-t" label="Type" value={qtype} onChange={setQtype} options={[["", "Any type"], ...QTYPES.map((q) => [q.value, q.label] as [string, string])]} />
        <button type="button" className="btn-primary" disabled={next.isPending || submit.isPending} onClick={() => next.mutate()}>
          {current ? "Next question" : "Start"} <Icon.chevron size={16} />
        </button>
      </div>
      {next.isError && <ErrorBox error={next.error} />}

      {current && (
        <section aria-labelledby="mq-h" className="card p-6 flex flex-col gap-4">
          <QChips q={current} />
          <h3 id="mq-h" className="text-xl font-semibold leading-snug">{current.question}</h3>
          {!result && (
            <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
              <label htmlFor="m-ans" className="label text-sm">Your answer</label>
              <textarea id="m-ans" className="input min-h-[220px] resize-y" required minLength={10} value={answer} onChange={(e) => setAnswer(e.target.value)}
                placeholder="Clarify the requirements, state your approach, go deep on the key decisions and trade-offs, and close with how you would evaluate it." />
              <div className="flex flex-wrap items-center gap-3">
                <button type="submit" className="btn-primary" disabled={submit.isPending || answer.trim().length < 10}>Submit for feedback</button>
                <span className="text-[13px] text-muted">{answer.trim().split(/\s+/).filter(Boolean).length} words</span>
                {submit.isPending && <Thinking label="The interviewer is reviewing your answer…" />}
              </div>
              {submit.isError && <ErrorBox error={submit.error} />}
            </form>
          )}
          {result && (
            <Feedback r={result} showModel={showModel} setShowModel={setShowModel}
              onRetry={() => { setResult(null); }} onNext={() => next.mutate()} />
          )}
        </section>
      )}

      <section aria-labelledby="hist-h" className="flex flex-col gap-3">
        <h2 id="hist-h" className="h-display text-xl">Recent answers</h2>
        {history.data?.length === 0 && <p className="text-muted">Your graded answers appear here.</p>}
        <ul className="flex flex-col gap-2">
          {history.data?.map((a) => (
            <li key={a.id}>
              <details className="card p-4">
                <summary className="cursor-pointer flex flex-wrap items-center gap-3">
                  <ScoreBadge score={a.score} />
                  <span className="font-medium flex-1 min-w-[200px]">{a.question_text}</span>
                  <span className="text-xs text-muted">{new Date(a.created_at).toLocaleString()}</span>
                </summary>
                <div className="pt-3 flex flex-col gap-3">
                  <p className="text-body">{a.verdict}</p>
                  <div><h4 className="font-semibold text-sm mb-1">Your answer</h4><p className="text-sm whitespace-pre-line text-body">{a.answer}</p></div>
                  <div className="grid gap-3 md:grid-cols-2"><Bullets title="Strengths" items={a.strengths} /><Bullets title="Missing" items={a.missing} /></div>
                </div>
              </details>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  const cls = score >= 4 ? "bg-ok text-white" : score === 3 ? "bg-accent text-white" : "bg-[#B42318] text-white";
  return <span className={`inline-flex items-center justify-center min-w-[52px] h-8 px-2 rounded-lg font-bold ${cls}`} aria-label={`Score ${score} of 5`}>{score}/5</span>;
}

function Feedback({ r, showModel, setShowModel, onRetry, onNext }: {
  r: Attempt & { question: IQuestion }; showModel: boolean; setShowModel: (v: boolean) => void; onRetry: () => void; onNext: () => void;
}) {
  return (
    <div className="flex flex-col gap-4 pt-2 border-t border-[#EEF0F3]" role="status">
      <div className="flex flex-wrap items-center gap-3">
        <ScoreBadge score={r.score} />
        <p className="flex-1 min-w-[240px] font-medium">{r.verdict}</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Bullets title="What was strong" items={r.strengths} />
        <Bullets title="What was missing" items={r.missing} />
      </div>
      <div className="rounded-xl border border-line p-4">
        <h4 className="font-semibold mb-2">A stronger version of your answer</h4>
        <Markdown>{r.better_answer_md}</Markdown>
      </div>
      {r.follow_up && <p className="rounded-xl bg-accent-soft p-4"><strong>Follow-up the interviewer would ask:</strong> {r.follow_up}</p>}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-outline" aria-expanded={showModel} onClick={() => setShowModel(!showModel)}>{showModel ? "Hide" : "Show"} model answer & sources</button>
        <button type="button" className="btn-outline" onClick={onRetry}>Try again</button>
        <button type="button" className="btn-primary" onClick={onNext}>Next question <Icon.chevron size={16} /></button>
      </div>
      {showModel && <AnswerBlock q={r.question} />}
    </div>
  );
}
