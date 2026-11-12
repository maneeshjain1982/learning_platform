// Interview prep: list of companions + the Configure page (new or edit).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, type Bar, type InterviewConfig, type QType, type Seniority } from "../api";
import { ErrorBox, Icon, ProgressBar, Thinking } from "../components/ui";

export const QTYPES: { value: QType; label: string; hint: string }[] = [
  { value: "concept", label: "Concept deep-dive", hint: "First principles, how things really work" },
  { value: "design", label: "System design", hint: "Open-ended architecture of a whole system" },
  { value: "scenario", label: "Scenario / trade-off", hint: "What would you do when…" },
  { value: "hands_on", label: "Hands-on / coding", hint: "Code, APIs, debugging an agent" },
  { value: "behavioral", label: "Behavioral / leadership", hint: "Influence, decisions, past projects" },
];
export const QTYPE_LABEL = Object.fromEntries(QTYPES.map((q) => [q.value, q.label])) as Record<QType, string>;

const BARS: { value: Bar; label: string; hint: string }[] = [
  { value: "top_ai", label: "Top AI company", hint: "Frontier-lab / AI-first big-tech depth: trade-offs, failure modes, numbers" },
  { value: "big_tech", label: "Big tech", hint: "Solid depth and practical system design" },
  { value: "standard", label: "Standard", hint: "Fundamentals and practical experience" },
];
const SENIORITY: Seniority[] = ["senior", "staff", "principal", "lead"];

export function daysLabel(d: number | null) {
  if (d === null) return "No date set";
  if (d < 0) return "Interview date passed";
  if (d === 0) return "Interview today";
  return `${d} day${d === 1 ? "" : "s"} left`;
}

// ---------------------------------------------------------------- list

export function InterviewList() {
  const list = useQuery({ queryKey: ["interviews"], queryFn: api.interviews });
  return (
    <main className="max-w-[1100px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="h-display text-3xl">Interview prep</h1>
          <p className="text-muted mt-1 max-w-[640px]">
            Each interview companion researches a role, maps every skill it needs, builds a study plan, writes a question bank with sourced answers and runs mock interviews.
          </p>
        </div>
        <Link to="/interview/new" className="btn-primary"><Icon.plus /> New interview companion</Link>
      </div>
      {list.isLoading && <Thinking label="Loading…" />}
      {list.isError && <ErrorBox error={list.error} onRetry={() => list.refetch()} />}
      {list.data?.length === 0 && (
        <Link to="/interview/new" className="card border-dashed p-8 flex flex-col gap-2 hover:border-accent">
          <span className="h-display text-xl">Set up your first interview companion</span>
          <span className="text-muted">Paste a job description, or just enter the role title and let the agents research it.</span>
        </Link>
      )}
      <ul className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
        {list.data?.map((p) => (
          <li key={p.id}>
            <Link to={`/interview/${p.id}`} className="card h-full p-5 flex flex-col gap-3 hover:border-accent">
              <div className="flex flex-wrap gap-2">
                <span className="chip bg-[#F1F3F6] text-body capitalize">{p.seniority}</span>
                {p.status === "building" || p.last_run?.status === "running"
                  ? <span className="chip bg-pp-bg text-pp-fg">Agents working…</span>
                  : p.status === "failed" ? <span className="chip bg-yt-bg text-yt-fg">Build failed</span> : null}
                <span className="chip bg-accent-soft text-accent-dark">{daysLabel(p.days_left)}</span>
              </div>
              <h2 className="h-display text-xl">{p.role_title}</h2>
              {p.company && <p className="text-muted -mt-2">{p.company}</p>}
              <div className="mt-auto flex flex-col gap-1.5">
                <ProgressBar pct={p.readiness} label={`Readiness ${p.readiness}%`} />
                <span className="text-[13px] text-muted">Readiness {p.readiness}% · {p.skills} skills · {p.questions} questions</span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}

// ---------------------------------------------------------------- configure

const EMPTY: InterviewConfig = {
  role_title: "", company: "", jd_text: "", seniority: "senior", interview_date: null, hours_per_week: 8,
  background: "", focus_notes: "", question_types: QTYPES.map((q) => q.value), questions_per_area: 6,
  question_bar: "top_ai", web_research: true,
};

export function InterviewConfigure() {
  const params = useParams();
  const editId = params.id ? Number(params.id) : null;
  const navigate = useNavigate();
  const qc = useQueryClient();
  const existing = useQuery({ queryKey: ["interview", editId], queryFn: () => api.interview(editId!), enabled: !!editId });
  const prefill = (useLocation().state as { prefill?: Partial<InterviewConfig> } | null)?.prefill;
  // Arriving from a job on the Career tab fills in the role, company and JD.
  const [f, setF] = useState<InterviewConfig>(() => (editId || !prefill ? EMPTY : { ...EMPTY, ...prefill }));
  const [replacePlan, setReplacePlan] = useState(true);
  const [replaceQuestions, setReplaceQuestions] = useState(false);

  useEffect(() => {
    const d = existing.data;
    if (d) {
      setF({ role_title: d.role_title, company: d.company, jd_text: d.jd_text, seniority: d.seniority,
        interview_date: d.interview_date, hours_per_week: d.hours_per_week, background: d.background,
        focus_notes: d.focus_notes, question_types: d.question_types, questions_per_area: d.questions_per_area,
        question_bar: d.question_bar, web_research: d.web_research });
    }
  }, [existing.data]);

  const set = <K extends keyof InterviewConfig>(k: K, v: InterviewConfig[K]) => setF((o) => ({ ...o, [k]: v }));
  const toggleType = (t: QType) =>
    set("question_types", f.question_types.includes(t) ? f.question_types.filter((x) => x !== t) : [...f.question_types, t]);

  const create = useMutation({
    mutationFn: () => api.createInterview(f),
    onSuccess: (d) => { qc.invalidateQueries(); navigate(`/interview/${d.id}`); },
  });
  const save = useMutation({
    mutationFn: async (rebuild: boolean) => {
      await api.updateInterview(editId!, { ...f, ...(f.interview_date ? {} : { clear_date: true }) });
      if (rebuild) await api.rebuildInterview(editId!, { replace_plan: replacePlan, replace_questions: replaceQuestions });
    },
    onSuccess: () => { qc.invalidateQueries(); navigate(`/interview/${editId}`); },
  });
  const busy = create.isPending || save.isPending;
  const err = create.error ?? save.error;

  if (editId && existing.isLoading) return <main className="p-8"><Thinking label="Loading…" /></main>;

  return (
    <main className="max-w-[900px] mx-auto w-full px-4 sm:px-8 py-8">
      <form className="card p-6 sm:p-8 flex flex-col gap-6"
        onSubmit={(e) => { e.preventDefault(); if (editId) save.mutate(false); else create.mutate(); }}>
        <div className="flex flex-col gap-2">
          <Link to={editId ? `/interview/${editId}` : "/interview"} className="text-sm text-accent font-semibold">← Back</Link>
          <h1 className="h-display text-3xl">{editId ? "Edit interview companion" : "Configure your interview companion"}</h1>
          <p className="text-muted">The agents use this to research the role, map the skills, plan your study time and write questions at the bar you choose.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <label htmlFor="role" className="label">Role title</label>
            <input id="role" className="input" required minLength={2} value={f.role_title} onChange={(e) => set("role_title", e.target.value)}
              placeholder="e.g. Agentic AI Architect" />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="company" className="label">Company <span className="font-normal text-muted">(optional)</span></label>
            <input id="company" className="input" value={f.company} onChange={(e) => set("company", e.target.value)} />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="jd" className="label">Job description <span className="font-normal text-muted">(optional, recommended)</span></label>
          <textarea id="jd" rows={8} className="input resize-y" value={f.jd_text} onChange={(e) => set("jd_text", e.target.value)}
            placeholder="Paste the full job description. Without one, the agents research what this role usually requires." />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="flex flex-col gap-2">
            <label htmlFor="sen" className="label">Level</label>
            <select id="sen" className="input capitalize" value={f.seniority} onChange={(e) => set("seniority", e.target.value as Seniority)}>
              {SENIORITY.map((s) => <option key={s} value={s} className="capitalize">{s}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="date" className="label">Interview date</label>
            <input id="date" type="date" className="input" value={f.interview_date ?? ""} onChange={(e) => set("interview_date", e.target.value || null)} />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="hrs" className="label">Hours per week</label>
            <input id="hrs" type="number" min={1} max={60} className="input" value={f.hours_per_week} onChange={(e) => set("hours_per_week", Number(e.target.value))} />
          </div>
        </div>

        <fieldset className="flex flex-col gap-2.5">
          <legend className="label mb-2.5">Question bar</legend>
          <div className="grid gap-2.5 sm:grid-cols-3">
            {BARS.map((b) => (
              <button key={b.value} type="button" aria-pressed={f.question_bar === b.value} onClick={() => set("question_bar", b.value)}
                className={`flex flex-col items-start gap-1 p-3.5 rounded-xl text-left ${f.question_bar === b.value ? "bg-accent-soft border-2 border-accent" : "bg-white border border-line2 hover:bg-ground"}`}>
                <span className="font-semibold">{b.label}</span><span className="text-[13px] text-muted">{b.hint}</span>
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2.5">
          <legend className="label mb-2.5">Question types (interview rounds)</legend>
          <div className="grid gap-2.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}>
            {QTYPES.map((q) => (
              <label key={q.value} className="flex items-center gap-2.5 min-h-[52px] px-3.5 border border-line2 rounded-[10px] cursor-pointer">
                <input type="checkbox" checked={f.question_types.includes(q.value)} onChange={() => toggleType(q.value)} className="w-[18px] h-[18px] accent-accent" />
                <span className="flex flex-col leading-tight"><span className="font-semibold">{q.label}</span><span className="text-xs text-muted">{q.hint}</span></span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="flex flex-col gap-2 max-w-[360px]">
          <label htmlFor="qpa" className="label">Questions per skill area: {f.questions_per_area}</label>
          <input id="qpa" type="range" min={2} max={15} value={f.questions_per_area} onChange={(e) => set("questions_per_area", Number(e.target.value))} className="accent-accent" />
          <p className="text-[13px] text-muted">About {f.questions_per_area * 10} questions across ~10 skill areas (one Claude call per area). Generate more anytime.</p>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="bg" className="label">Your background <span className="font-normal text-muted">(optional)</span></label>
          <textarea id="bg" rows={4} className="input resize-y" value={f.background} onChange={(e) => set("background", e.target.value)}
            placeholder="Paste a CV summary or describe your experience. The plan spends less time on what you already know." />
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="focus" className="label">Focus areas or notes <span className="font-normal text-muted">(optional)</span></label>
          <textarea id="focus" rows={2} className="input resize-y" value={f.focus_notes} onChange={(e) => set("focus_notes", e.target.value)}
            placeholder="e.g. The recruiter said there will be a multi-agent system design round." />
        </div>
        <label className="flex items-center gap-2.5 font-medium">
          <input type="checkbox" className="w-5 h-5 accent-accent" checked={f.web_research} onChange={(e) => set("web_research", e.target.checked)} />
          Research the role on the web (job postings, interview reports)
        </label>

        {editId && (
          <fieldset className="rounded-xl bg-ground p-4 flex flex-col gap-2">
            <legend className="sr-only">Rebuild options</legend>
            <p className="font-semibold">When rebuilding with these settings</p>
            <label className="flex items-center gap-2.5"><input type="checkbox" className="w-5 h-5 accent-accent" checked={replacePlan} onChange={(e) => setReplacePlan(e.target.checked)} />
              Replace the prep plan (its lesson progress is lost)</label>
            <label className="flex items-center gap-2.5"><input type="checkbox" className="w-5 h-5 accent-accent" checked={replaceQuestions} onChange={(e) => setReplaceQuestions(e.target.checked)} />
              Replace the questions (your own and practised questions are kept)</label>
            <p className="text-[13px] text-muted">The research and skill map are always refreshed; your self-ratings are kept for skills with the same name.</p>
          </fieldset>
        )}

        {err && <ErrorBox error={err} />}
        <div className="flex flex-wrap gap-3 pt-2 border-t border-[#EEF0F3]">
          {editId ? (
            <>
              <button type="submit" className="btn-outline" disabled={busy || !f.question_types.length}>Save settings only</button>
              <button type="button" className="btn-primary" disabled={busy || !f.question_types.length} onClick={() => save.mutate(true)}>
                {busy ? "Starting…" : "Save and rebuild"}
              </button>
            </>
          ) : (
            <button type="submit" className="btn-primary min-h-[48px] px-6" disabled={busy || !f.question_types.length}>
              {busy ? "Starting the agents…" : "Prepare my interview plan"}
            </button>
          )}
          <span className="text-[13px] text-muted self-center">Takes about 10 minutes and roughly 40–50 Claude calls.</span>
        </div>
      </form>
    </main>
  );
}
