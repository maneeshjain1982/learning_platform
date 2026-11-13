import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, useNavigate, useParams } from "react-router-dom";
import {
  api, type CourseStatus, type VoiceData as HV, type HVCourse, type HVModule, type UtterParams, type UtterStyle,
  type UtterStyleInfo, type Utterance,
} from "../api";
import { ItemActions, RemovedNote, RemoveFound } from "../components/EditItem";
import { PaperSummary } from "../components/PaperSummary";
import ReviewQA from "../components/ReviewQA";
import { ErrorBox, Icon, ProgressBar, Thinking } from "../components/ui";

const TABS = [
  ["overview", "Overview & skills"],
  ["learn", "Courses & modules"],
  ["models", "Models & datasets"],
  ["papers", "Research papers"],
  ["playbook", "Launch playbook"],
  ["testing", "Testing"],
  ["data", "Data"],
  ["generator", "Utterance generator"],
  ["news", "What's new"],
] as const;
type Tab = (typeof TABS)[number][0];

const LEVELS = ["None", "Basic", "Working", "Strong", "Expert"];
const QK = "voice";
/** The language code of the page ("hi", "en"); every query and mutation is per language. */
const LangCtx = createContext("hi");
const useLang = () => useContext(LangCtx);

function fmtDay(d: string) {
  const t = new Date(`${d}T00:00:00`);
  return isNaN(t.getTime()) ? d : t.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
function ago(isoTime: string) {
  const mins = Math.round((Date.now() - new Date(isoTime).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  return h < 48 ? `${h} hour${h === 1 ? "" : "s"} ago` : `${Math.round(h / 24)} days ago`;
}
const Chip = ({ children, cls = "bg-[#F1F3F6] text-body" }: { children: ReactNode; cls?: string }) =>
  <span className={`chip ${cls}`}>{children}</span>;
const Top = () => <Chip cls="bg-ok-soft text-ok-dark">Top pick</Chip>;
const Ext = ({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) =>
  <a href={href} target="_blank" rel="noreferrer" className={`text-accent hover:underline ${className}`}>{children}</a>;

function Section({ id, title, intro, children }: { id: string; title: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <div>
        <h2 id={id} className="h-display text-2xl">{title}</h2>
        {intro && <p className="text-muted max-w-[780px]">{intro}</p>}
      </div>
      {children}
    </section>
  );
}

function useSetState() {
  const qc = useQueryClient();
  const lang = useLang();
  const key = [QK, lang];
  return useMutation({
    mutationFn: (v: { kind: "skill" | "course" | "step"; key: string; value: number | string | boolean }) =>
      api.setVoiceState(lang, v.kind, v.key, v.value),
    onMutate: async (v) => {  // optimistic: the control updates immediately
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<HV>(key);
      if (prev) qc.setQueryData<HV>(key, apply(prev, v));
      return { prev };
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(key, ctx.prev),
  });
}
function apply(d: HV, v: { kind: string; key: string; value: number | string | boolean }): HV {
  if (v.kind === "skill")
    return { ...d, competencies: d.competencies.map((a) => ({ ...a, skills: a.skills.map((s) => s.name === v.key ? { ...s, level: v.value as number } : s) })) };
  if (v.kind === "course")
    return { ...d, courses: d.courses.map((c) => c.id === v.key ? { ...c, status: v.value as CourseStatus } : c) };
  const steps = new Set(d.steps_done);
  if (v.value) steps.add(v.key); else steps.delete(v.key);
  return { ...d, steps_done: [...steps] };
}

/** Everything needed to add a language (Hindi, English…) to a voice assistant's ASR and NLU. */
export default function Voice() {
  const lang = useParams().lang ?? "hi";
  const [tab, setTab] = useState<Tab>(() => (TABS.find(([id]) => `#${id}` === location.hash)?.[0] ?? "overview"));
  useEffect(() => { history.replaceState(null, "", `#${tab}`); }, [tab, lang]);
  const langs = useQuery({ queryKey: ["voice-langs"], queryFn: api.voiceLangs, staleTime: Infinity });
  const q = useQuery({ queryKey: [QK, lang], queryFn: () => api.voice(lang) });
  const pill = ({ isActive }: { isActive: boolean }) =>
    `min-h-[40px] px-4 inline-flex items-center rounded-full border font-semibold ${isActive ? "bg-accent text-white border-accent" : "bg-white border-line2 text-body hover:bg-ground"}`;

  return (
    <LangCtx.Provider value={lang}>
    <main className="max-w-[1100px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        <nav aria-label="Language" className="flex flex-wrap gap-2">
          {(langs.data ?? [{ code: "hi", name: "Hindi", title: "" }, { code: "en", name: "English", title: "" }]).map((l) => (
            <NavLink key={l.code} to={`/voice/${l.code}#${tab}`} className={pill}>{l.name}</NavLink>
          ))}
        </nav>
        <h1 className="h-display text-3xl">{q.data?.title ?? "Voice: ASR + NLU"}</h1>
        {q.data && <p className="text-body max-w-[780px]">{q.data.intro}</p>}
        {q.data && <p className="text-xs text-muted">Researched and link-checked {fmtDay(q.data.checked_on)}. Use "What's new" to find anything newer.</p>}
      </header>
      <div role="tablist" aria-label="Voice sections" className="flex gap-1 border-b border-line overflow-x-auto">
        {TABS.map(([id, label]) => (
          <button key={id} role="tab" type="button" aria-selected={tab === id} aria-controls={`hv-panel-${id}`} id={`hv-tab-${id}`}
            onClick={() => setTab(id)}
            className={`px-3.5 min-h-[44px] -mb-px border-b-2 font-semibold whitespace-nowrap ${tab === id ? "border-accent text-accent-dark" : "border-transparent text-body hover:text-ink"}`}>
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`hv-panel-${tab}`} aria-labelledby={`hv-tab-${tab}`} className="flex flex-col gap-8">
        {q.isLoading && <Thinking label="Loading…" />}
        {q.isError && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
        {q.data && tab === "overview" && <Overview d={q.data} go={setTab} />}
        {q.data && tab === "learn" && <Learn d={q.data} />}
        {q.data && tab === "models" && <ModelsData d={q.data} />}
        {q.data && tab === "papers" && <Papers d={q.data} />}
        {q.data && tab === "playbook" && <Playbook d={q.data} />}
        {q.data && tab === "testing" && <Testing d={q.data} />}
        {q.data && tab === "data" && <DataPlan d={q.data} go={setTab} />}
        {q.data && tab === "generator" && <Generator key={lang} d={q.data} />}
        {q.data && tab === "news" && <WhatsNew key={lang} d={q.data} />}
      </div>
    </main>
    </LangCtx.Provider>
  );
}

// ---------------------------------------------------------------- overview & skills

function Overview({ d, go }: { d: HV; go: (t: Tab) => void }) {
  const set = useSetState();
  const skills = d.competencies.flatMap((a) => a.skills);
  const rated = skills.filter((s) => s.level > 0).length;
  const gaps = skills.filter((s) => s.level < s.need).sort((a, b) => (b.need - b.level) - (a.need - a.level));
  const met = skills.length - gaps.length;
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-3">
        {([
          ["learn", "1. Learn", "Courses in order, plus 12 technical modules with review Q&A."],
          ["playbook", "2. Plan the launch", "10 phases from scoping to post-launch, with a checklist."],
          ["generator", "3. Make data", `Generate ${d.utter_styles.map((s) => s.label).join(", ")} utterances with slot labels.`],
        ] as const).map(([t, h, p]) => (
          <button key={t} type="button" onClick={() => go(t)} className="card p-4 text-left hover:border-accent">
            <span className="font-semibold block">{h}</span><span className="text-sm text-muted">{p}</span>
          </button>
        ))}
      </div>

      <Section id="hv-bixby" title="About Bixby" intro="From the public Bixby developer documentation only. Internal Samsung processes aren't covered.">
        <ul className="card p-5 list-disc pl-9 flex flex-col gap-1.5 text-body">
          {d.platform_notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      </Section>

      <Section id="hv-skills" title="Competencies"
        intro={`Levels needed by the person leading the ${d.name} ASR/NLU work. Rate yourself to see your gaps.`}>
        <div className="card p-5 flex flex-col gap-2">
          <ProgressBar pct={Math.round((met / skills.length) * 100)} label={`${met} of ${skills.length} skills at the needed level`} />
          <p className="text-sm text-muted">{met} of {skills.length} skills at the needed level · {rated} rated.
            {gaps.length > 0 && rated > 0 && <> Biggest gaps: {gaps.slice(0, 3).map((g) => g.name).join("; ")}.</>}</p>
        </div>
        <div className="flex flex-col gap-4">
          {d.competencies.map((a) => (
            <div key={a.id} className="card p-5 flex flex-col gap-3">
              <h3 className="font-semibold text-lg">{a.title}</h3>
              <ul className="flex flex-col gap-3">
                {a.skills.map((s) => {
                  const id = `sk-${a.id}-${s.name.replace(/\W+/g, "-")}`;
                  const gap = s.level < s.need;
                  return (
                    <li key={s.name} className="flex flex-wrap items-start gap-3 border-t border-line pt-3 first:border-0 first:pt-0">
                      <div className="flex-1 min-w-[220px]">
                        <p className="font-semibold">{s.name} <Chip>Needed: {LEVELS[s.need]}</Chip>{" "}
                          {s.level > 0 && (gap ? <Chip cls="bg-pp-bg text-pp-fg">Gap</Chip> : <Chip cls="bg-ok-soft text-ok-dark">Met</Chip>)}</p>
                        <p className="text-sm text-muted">{s.why}</p>
                      </div>
                      <label htmlFor={id} className="sr-only">Your level in {s.name}</label>
                      <select id={id} className="input w-auto py-1.5" value={s.level}
                        onChange={(e) => set.mutate({ kind: "skill", key: s.name, value: Number(e.target.value) })}>
                        {LEVELS.map((l, i) => <option key={l} value={i}>{i === 0 ? "My level: not rated" : `My level: ${l}`}</option>)}
                      </select>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}

// ---------------------------------------------------------------- courses & modules

function Learn({ d }: { d: HV }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const lang = useLang();
  const makePath = useMutation({
    mutationFn: () => api.voicePath(lang),
    onSuccess: (r) => { qc.invalidateQueries(); navigate(`/paths/${r.path_id}`); },
  });
  const done = d.courses.filter((c) => c.status === "done").length;
  return (
    <>
      <Section id="hv-courses" title="Courses, in order"
        intro="Free courses and docs from foundations to the assistant platform. Top picks are the ones to do first.">
        <RemovedNote scope={`voice.${d.code}.courses`} count={d.removed.courses} edited={d.courses.some((c) => c._edited)} queryKey={[QK, d.code]} />
        <div className="card p-5 flex flex-col gap-2">
          <ProgressBar pct={Math.round((done / d.courses.length) * 100)} label={`${done} of ${d.courses.length} done`} />
          <p className="text-sm text-muted">{done} of {d.courses.length} courses done</p>
        </div>
        {d.phases.map((p) => (
          <div key={p.id} className="flex flex-col gap-2">
            <h3 className="font-semibold text-lg">{p.title} <span className="text-muted font-normal text-sm">· {p.summary}</span></h3>
            <ul className="flex flex-col gap-2">
              {d.courses.filter((c) => c.phase === p.id).map((c) => <li key={c.id}><CourseRow c={c} code={d.code} /></li>)}
            </ul>
          </div>
        ))}
      </Section>

      <Section id="hv-modules" title="Technical modules"
        intro={`The building blocks of ${d.name} ASR and NLU. Open a module for its topics and review Q&A; the LLM writes the questions and checks them against papers and official docs.`}>
        <div className="card p-5 flex flex-wrap items-center gap-4">
          <p className="flex-1 min-w-[240px] text-sm text-body">
            {d.modules.length} modules · {d.modules.reduce((n, m) => n + m.lessons, 0)} topics. Add them to My paths to
            tick topics off, take notes, ask the tutor and let the agents find videos and papers for each topic.
          </p>
          {d.path_id
            ? <Link to={`/paths/${d.path_id}`} className="btn-outline">Open my study path</Link>
            : <button type="button" className="btn-primary" disabled={makePath.isPending} onClick={() => makePath.mutate()}>
                <Icon.plus /> {makePath.isPending ? "Adding…" : "Add modules to My paths"}</button>}
        </div>
        {makePath.isError && <ErrorBox error={makePath.error} />}
        {d.sides.map((s) => (
          <div key={s.id} className="flex flex-col gap-2">
            <h3 className="font-semibold text-lg">{s.title}</h3>
            <ul className="flex flex-col gap-3">
              {d.modules.filter((m) => m.side === s.id).map((m) => <li key={m.slug}><ModuleCard m={m} sources={d.qa_sources} /></li>)}
            </ul>
          </div>
        ))}
      </Section>
    </>
  );
}

function CourseRow({ c, code }: { c: HVCourse; code: string }) {
  const set = useSetState();
  const id = `cs-${c.id}`;
  return (
    <div className={`card p-4 flex flex-wrap items-start gap-3 ${c.status === "done" ? "bg-ok-soft/30" : ""}`}>
      <div className="flex-1 min-w-[240px] flex flex-col gap-1">
        <p className="font-semibold"><Ext href={c.url}>{c.title}</Ext> {c.top_pick && <Top />}</p>
        <p className="text-sm text-muted">{c.provider} · {c.kind} · {c.level} · {c.cost}</p>
        <p className="text-sm text-body">{c.covers}</p>
      </div>
      <label htmlFor={id} className="sr-only">Status of {c.title}</label>
      <select id={id} className="input w-auto py-1.5" value={c.status}
        onChange={(e) => set.mutate({ kind: "course", key: c.id, value: e.target.value })}>
        <option value="todo">To do</option><option value="doing">In progress</option><option value="done">Done</option>
      </select>
      <ItemActions scope={`voice.${code}.courses`} itemKey={c._key ?? c.id} title={c.title} queryKey={[QK, code]} fields={[
        { name: "title", label: "Title", value: c.title }, { name: "provider", label: "Provider", value: c.provider },
        { name: "level", label: "Level", value: c.level }, { name: "cost", label: "Cost", value: c.cost },
        { name: "covers", label: "What it covers", value: c.covers, long: true }]} />
    </div>
  );
}

function ModuleCard({ m, sources }: { m: HVModule; sources: string }) {
  const [open, setOpen] = useState(false);
  const [qa, setQa] = useState(false);
  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex-1 min-w-[240px]">
          <h4 className="font-semibold text-lg">{m.title}</h4>
          <p className="text-sm text-body">{m.summary}</p>
          <p className="text-xs text-muted mt-1">
            {m.lessons} topics · Start with <Ext href={m.url}>{m.url.replace(/^https?:\/\//, "").replace(/\/$/, "")}</Ext>
            {m.path_progress && <> · {m.path_progress.done} of {m.path_progress.total} topics done in your path</>}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-outline btn-sm" aria-expanded={open} onClick={() => setOpen(!open)}>
          <Icon.chevron size={15} className={`transition-transform ${open ? "rotate-90" : ""}`} /> Topics and references
        </button>
        <button type="button" className="btn-outline btn-sm" aria-expanded={qa} onClick={() => setQa(!qa)}>
          Review Q&A{m.qa.total > 0 && ` · ${m.qa.known}/${m.qa.total} known`}
        </button>
      </div>
      {open && (
        <div className="flex flex-col gap-3">
          {m.outline.map((s) => (
            <div key={s.title}>
              <p className="font-semibold text-sm">{s.title}</p>
              <ul className="list-disc pl-5 text-sm text-body">{s.lessons.map((l) => <li key={l}>{l}</li>)}</ul>
            </div>
          ))}
          {m.refs.length > 0 && (
            <p className="text-sm flex flex-wrap gap-x-3 gap-y-1"><span className="text-muted">References:</span>
              {m.refs.map((r) => <Ext key={r} href={r}>{r.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")}</Ext>)}</p>
          )}
        </div>
      )}
      {qa && <ReviewQA slug={m.slug} lessonCount={m.lessons} parentKey={QK} unit="topic" sourceHint={sources} />}
    </div>
  );
}

// ---------------------------------------------------------------- models & datasets

function ModelsData({ d }: { d: HV }) {
  const [topOnly, setTopOnly] = useState(false);
  return (
    <>
      <Section id="hv-models" title={`Best ${d.name} models and tools`}
        intro="WER numbers are quoted from the source named, on the benchmark named; lower is better. Check licences before product use.">
        <label className="flex items-center gap-2 text-sm font-semibold min-h-[36px]">
          <input type="checkbox" checked={topOnly} onChange={(e) => setTopOnly(e.target.checked)} className="w-4 h-4" /> Top picks only
        </label>
        <RemovedNote scope={`voice.${d.code}.models`} count={d.removed.models} edited={d.models.some((m) => m._edited)} queryKey={[QK, d.code]} />
        {d.model_kinds.map((k) => {
          const list = d.models.filter((m) => m.kind === k.id && (!topOnly || m.top_pick));
          if (!list.length) return null;
          return (
            <div key={k.id} className="flex flex-col gap-2">
              <h3 className="font-semibold text-lg">{k.title}</h3>
              <ul className="grid gap-3 md:grid-cols-2">
                {list.map((m) => (
                  <li key={m.name} className="card p-4 flex flex-col gap-1.5">
                    <div className="flex items-start gap-2">
                      <p className="font-semibold flex-1"><Ext href={m.url}>{m.name}</Ext> {m.top_pick && <Top />}</p>
                      <ItemActions scope={`voice.${d.code}.models`} itemKey={m._key ?? m.name} title={m.name} queryKey={[QK, d.code]} fields={[
                        { name: "org", label: "Organisation", value: m.org }, { name: "size", label: "Size", value: m.size },
                        { name: "licence", label: "Licence", value: m.licence }, { name: "result", label: "Result", value: m.result, long: true },
                        { name: "notes", label: "Notes", value: m.notes, long: true }]} />
                    </div>
                    <p className="text-sm text-muted">{m.org}{m.size && ` · ${m.size}`}{m.licence && ` · ${m.licence}`}</p>
                    {m.result && <p className="text-sm"><span className="font-semibold">Result: </span>{m.result}</p>}
                    <p className="text-sm text-body">{m.notes}</p>
                    <p className="text-xs text-muted flex flex-wrap gap-x-3">
                      {m.on_device && <span>On-device: {m.on_device}</span>}
                      {m.paper && <Ext href={m.paper}>Paper</Ext>}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </Section>
      <Section id="hv-datasets" title="Datasets"
        intro='Datasets marked "gated" need you to sign in to Hugging Face and accept their terms before downloading.'>
        <RemovedNote scope={`voice.${d.code}.datasets`} count={d.removed.datasets} edited={d.datasets.some((x) => x._edited)} queryKey={[QK, d.code]} />
        {d.dataset_kinds.map((k) => (
          <div key={k.id} className="flex flex-col gap-2">
            <h3 className="font-semibold text-lg">{k.title}</h3>
            <ul className="grid gap-3 md:grid-cols-2">
              {d.datasets.filter((x) => x.kind === k.id).map((x) => (
                <li key={x.name} className="card p-4 flex flex-col gap-1.5">
                  <div className="flex items-start gap-2">
                    <p className="font-semibold flex-1"><Ext href={x.url}>{x.name}</Ext></p>
                    <ItemActions scope={`voice.${d.code}.datasets`} itemKey={x._key ?? x.name} title={x.name} queryKey={[QK, d.code]} fields={[
                      { name: "size", label: "Size", value: x.size }, { name: "licence", label: "Licence", value: x.licence },
                      { name: "what", label: "What it is", value: x.what, long: true }, { name: "use", label: "Use", value: x.use, long: true }]} />
                  </div>
                  {(x.size || x.licence) && <p className="text-sm text-muted">{[x.size, x.licence].filter(Boolean).join(" · ")}</p>}
                  <p className="text-sm text-body">{x.what}</p>
                  <p className="text-sm"><span className="font-semibold">Use: </span>{x.use}</p>
                  {x.paper && <p className="text-xs"><Ext href={x.paper}>Paper</Ext></p>}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </Section>
    </>
  );
}

// ---------------------------------------------------------------- papers

function Papers({ d }: { d: HV }) {
  const [topic, setTopic] = useState("all");
  const [topOnly, setTopOnly] = useState(false);
  const list = (t: string) => d.papers.filter((p) => p.topic === t && (!topOnly || p.top_pick));
  return (
    <Section id="hv-papers" title="Research papers"
      intro={`${d.papers.length} papers, every arXiv ID checked. Top picks are the ones to read first. "What's new" finds recent ones.`}>
      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="hv-topic" className="text-sm font-semibold">Topic</label>
        <select id="hv-topic" className="input w-auto py-1.5" value={topic} onChange={(e) => setTopic(e.target.value)}>
          <option value="all">All topics</option>
          {d.paper_topics.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm font-semibold min-h-[36px]">
          <input type="checkbox" checked={topOnly} onChange={(e) => setTopOnly(e.target.checked)} className="w-4 h-4" /> Top picks only
        </label>
      </div>
      <RemovedNote scope={`voice.${d.code}.papers`} count={d.removed.papers} edited={d.papers.some((p) => p._edited)} queryKey={[QK, d.code]} />
      {d.paper_topics.filter((t) => topic === "all" || t.id === topic).map((t) => list(t.id).length > 0 && (
        <div key={t.id} className="flex flex-col gap-2">
          <h3 className="font-semibold text-lg">{t.title}</h3>
          <ul className="flex flex-col gap-2">
            {list(t.id).map((p) => (
              <li key={p.id} className="card p-4 flex gap-3">
                <Icon.paper className="text-muted shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                  <p className="font-semibold"><Ext href={p.url}>{p.title}</Ext> {p.top_pick && <Top />}</p>
                  <p className="text-xs text-muted">{p.year} · arXiv {p.id}</p>
                  <p className="text-sm text-body">{p.why}</p>
                  <div className="pt-1.5"><PaperSummary paper={{ url: p.url, title: p.title }} context={`${d.name} voice assistant ASR/NLU`} /></div>
                </div>
                <ItemActions scope={`voice.${d.code}.papers`} itemKey={p._key ?? p.id} title={p.title} queryKey={[QK, d.code]} fields={[
                  { name: "title", label: "Title", value: p.title }, { name: "why", label: "Why read it", value: p.why, long: true }]} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </Section>
  );
}

// ---------------------------------------------------------------- playbook

function Playbook({ d }: { d: HV }) {
  const set = useSetState();
  const total = d.playbook.reduce((n, p) => n + p.steps.length, 0);
  const done = new Set(d.steps_done);
  return (
    <Section id="hv-play" title="Adding a new language: the playbook"
      intro="The phases a voice assistant team goes through to launch a new locale such as hi-IN. Tick steps off as you go.">
      <div className="card p-5 flex flex-col gap-2">
        <ProgressBar pct={Math.round((done.size / total) * 100)} label={`${done.size} of ${total} steps done`} />
        <p className="text-sm text-muted">{done.size} of {total} steps done</p>
      </div>
      <ol className="flex flex-col gap-3">
        {d.playbook.map((p, pi) => {
          const n = p.steps.filter((_, i) => done.has(`${p.id}:${i}`)).length;
          return (
            <li key={p.id}>
              <details className="card group" open={pi === 0}>
                <summary className="flex items-center gap-3 min-h-[56px] px-5 py-3 cursor-pointer list-none">
                  <Icon.chevron className="text-muted transition-transform group-open:rotate-90 shrink-0" />
                  <span className="flex-1">
                    <span className="font-semibold">{pi + 1}. {p.title}</span>
                    <span className="block text-sm text-muted">{p.goal}</span>
                  </span>
                  <Chip cls={n === p.steps.length ? "bg-ok-soft text-ok-dark" : undefined}>{n}/{p.steps.length}</Chip>
                </summary>
                <div className="px-5 pb-5 flex flex-col gap-3">
                  <ul className="flex flex-col gap-1">
                    {p.steps.map((s, i) => {
                      const key = `${p.id}:${i}`;
                      return (
                        <li key={key}>
                          <label className="flex items-start gap-2.5 min-h-[36px] py-1 cursor-pointer">
                            <input type="checkbox" className="w-4 h-4 mt-1 shrink-0" checked={done.has(key)}
                              onChange={(e) => set.mutate({ kind: "step", key, value: e.target.checked })} />
                            <span className={done.has(key) ? "line-through text-muted" : ""}>{s}</span>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                  <div className="grid gap-3 sm:grid-cols-3 text-sm">
                    <div><p className="font-semibold">Outputs</p><ul className="list-disc pl-5 text-body">{p.outputs.map((o) => <li key={o}>{o}</li>)}</ul></div>
                    <div><p className="font-semibold">Usually owned by</p><p className="text-body">{p.owners}</p></div>
                    <div><p className="font-semibold">Pitfalls</p><ul className="list-disc pl-5 text-body">{p.pitfalls.map((o) => <li key={o}>{o}</li>)}</ul></div>
                  </div>
                </div>
              </details>
            </li>
          );
        })}
      </ol>
    </Section>
  );
}

// ---------------------------------------------------------------- testing

function Testing({ d }: { d: HV }) {
  return (
    <>
      {d.testing.map((t) => (
        <Section key={t.id} id={`hv-test-${t.id}`} title={t.title}>
          <ul className="grid gap-3 md:grid-cols-2">
            {t.metrics.map(([name, what, note]) => (
              <li key={name} className="card p-4 flex flex-col gap-1">
                <p className="font-semibold">{name}</p>
                <p className="text-sm text-body">{what}</p>
                <p className="text-sm text-muted">{note}</p>
              </li>
            ))}
          </ul>
          <div className="card p-4">
            <p className="font-semibold text-sm mb-2">Slice the results by</p>
            <div className="flex flex-wrap gap-1.5">{t.slices.map((s) => <Chip key={s}>{s}</Chip>)}</div>
          </div>
        </Section>
      ))}
      <Section id="hv-test-size" title="Test-set design">
        <ul className="card p-5 list-disc pl-9 flex flex-col gap-1.5 text-body">{d.test_sizing.map((s) => <li key={s}>{s}</li>)}</ul>
      </Section>
    </>
  );
}

// ---------------------------------------------------------------- data

function DataPlan({ d, go }: { d: HV; go: (t: Tab) => void }) {
  return (
    <>
      <Section id="hv-var" title="Data variability you need"
        intro="Plan quotas across each dimension. Gaps here show up later as WER spikes on one slice.">
        <ul className="flex flex-col gap-3">
          {d.variability.map((v) => (
            <li key={v.dimension} className="card p-4 flex flex-col gap-2">
              <p className="font-semibold">{v.dimension}</p>
              <div className="flex flex-wrap gap-1.5">{v.values.map((x) => <Chip key={x}>{x}</Chip>)}</div>
              <p className="text-sm text-body"><span className="font-semibold">Why: </span>{v.why}</p>
              <p className="text-sm text-body"><span className="font-semibold">How: </span>{v.how}</p>
            </li>
          ))}
        </ul>
      </Section>
      <Section id="hv-src" title="How to get the data">
        <ul className="grid gap-3 md:grid-cols-2">
          {d.sourcing.map((s) => (
            <li key={s.method} className="card p-4 flex flex-col gap-1.5">
              <p className="font-semibold">{s.method}</p>
              <p className="text-sm text-body">{s.how}</p>
              <p className="text-sm"><span className="font-semibold text-ok-dark">Pros: </span>{s.pros}</p>
              <p className="text-sm"><span className="font-semibold text-pp-fg">Cons: </span>{s.cons}</p>
            </li>
          ))}
        </ul>
      </Section>
      <Section id="hv-gen" title="How to generate data">
        <ul className="grid gap-3 md:grid-cols-2">
          {d.generation.map((g) => (
            <li key={g.name} className="card p-4 flex flex-col gap-1.5">
              <p className="font-semibold">{g.name} <Chip>{g.for.toUpperCase()}</Chip></p>
              <p className="text-sm text-body">{g.how}</p>
              <p className="text-sm"><span className="font-semibold">Watch out: </span>{g.caution}</p>
              {g.tool && <p className="text-xs text-muted">Tools: {g.tool}</p>}
            </li>
          ))}
        </ul>
        <button type="button" className="btn-primary self-start" onClick={() => go("generator")}>Open the utterance generator</button>
      </Section>
    </>
  );
}

// ---------------------------------------------------------------- utterance generator

function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}
const csvCell = (s: string) => `"${s.replace(/"/g, '""')}"`;

function Generator({ d: info }: { d: HV }) {
  const qc = useQueryClient();
  const lang = useLang();
  const styleIds: UtterStyle[] = info.utter_styles.map((s: UtterStyleInfo) => s.id);
  const STYLE_LABEL: Record<string, string> = Object.fromEntries(info.utter_styles.map((s) => [s.id, s.label]));
  const q = useQuery({
    queryKey: ["utterances", lang], queryFn: () => api.utterances(lang),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 3000 : false),
  });
  const [p, setP] = useState<UtterParams>(info.utter_default);
  const loaded = useRef(false);
  useEffect(() => {  // start from the last run's settings
    if (!loaded.current && q.data) { loaded.current = true; if (q.data.params) setP(q.data.params); }
  }, [q.data]);
  const gen = useMutation({ mutationFn: (b: UtterParams) => api.generateUtterances(lang, b), onSuccess: (d) => qc.setQueryData(["utterances", lang], d) });
  const [style, setStyle] = useState<UtterStyle | "all">("all");

  const d = q.data;
  const running = d?.status === "running" || gen.isPending;
  const items = (d?.items ?? []).filter((u) => style === "all" || u.style === style);
  const intent = d?.params?.intent ?? p.intent;
  const onSubmit = (e: FormEvent) => { e.preventDefault(); gen.mutate({ ...p, slots: p.slots.filter((s) => s.name.trim()) }); };
  const setSlot = (i: number, k: "name" | "examples", v: string) =>
    setP({ ...p, slots: p.slots.map((s, j) => (j === i ? { ...s, [k]: v } : s)) });
  const exportJsonl = () => download(`${intent}.jsonl`, (d?.items ?? []).map((u) =>
    JSON.stringify({ intent, text: u.text, style: u.style, tone: u.tone, slots: u.slots })).join("\n"), "application/jsonl");
  const exportCsv = () => download(`${intent}.csv`, ["intent,text,style,tone,slots,aligned_nl",
    ...(d?.items ?? []).map((u) => [intent, u.text, u.style, u.tone, u.slots.map((s) => `${s.name}=${s.value}`).join("; "), u.annotated].map(csvCell).join(","))].join("\n"),
    "text/csv;charset=utf-8");
  const exportNl = () => download(`${intent}.aligned-nl.txt`, (d?.items ?? []).map((u) => u.annotated).join("\n"), "text/plain;charset=utf-8");

  return (
    <Section id="hv-gen-tool" title={`${info.name} utterance generator`}
      intro={`Describe an intent and its slots. The LLM writes varied things users would say (${info.utter_styles.map((s) => s.label).join(", ")}), with slot labels. Slot values not found in the sentence are removed. Export as CSV, JSONL or Bixby-style Aligned NL, and have a native speaker review a sample before training on it.`}>
      <form onSubmit={onSubmit} className="card p-5 flex flex-col gap-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_2fr]">
          <div>
            <label htmlFor="ug-intent" className="font-semibold text-sm">Intent name</label>
            <input id="ug-intent" className="input" required pattern="[A-Za-z][A-Za-z0-9_.]*" value={p.intent}
              onChange={(e) => setP({ ...p, intent: e.target.value })} />
            <p className="text-xs text-muted mt-1">Letters, digits, _ and . only (e.g. SetAlarm)</p>
          </div>
          <div>
            <label htmlFor="ug-desc" className="font-semibold text-sm">What it does</label>
            <input id="ug-desc" className="input" value={p.description} onChange={(e) => setP({ ...p, description: e.target.value })} />
          </div>
        </div>
        <fieldset className="flex flex-col gap-2">
          <legend className="font-semibold text-sm mb-1">Slots</legend>
          {p.slots.map((s, i) => (
            <div key={i} className="flex flex-wrap gap-2 items-center">
              <label className="sr-only" htmlFor={`ug-sn-${i}`}>Slot {i + 1} name</label>
              <input id={`ug-sn-${i}`} className="input w-[160px]" placeholder="name" value={s.name} onChange={(e) => setSlot(i, "name", e.target.value)} />
              <label className="sr-only" htmlFor={`ug-se-${i}`}>Slot {i + 1} example values</label>
              <input id={`ug-se-${i}`} className="input flex-1 min-w-[200px]" placeholder="example values, comma separated" value={s.examples}
                onChange={(e) => setSlot(i, "examples", e.target.value)} />
              <button type="button" className="btn-outline btn-sm" aria-label={`Remove slot ${s.name || i + 1}`}
                onClick={() => setP({ ...p, slots: p.slots.filter((_, j) => j !== i) })}><Icon.close size={15} /></button>
            </div>
          ))}
          {p.slots.length < 8 && (
            <button type="button" className="btn-outline btn-sm self-start" onClick={() => setP({ ...p, slots: [...p.slots, { name: "", examples: "" }] })}>
              <Icon.plus size={15} /> Add slot</button>
          )}
        </fieldset>
        <div className="flex flex-wrap items-end gap-4">
          <fieldset className="flex flex-wrap gap-3">
            <legend className="font-semibold text-sm mb-1">Styles</legend>
            {styleIds.map((st) => (
              <label key={st} className="flex items-center gap-2 min-h-[36px]">
                <input type="checkbox" className="w-4 h-4" checked={p.styles.includes(st)}
                  onChange={(e) => setP({ ...p, styles: e.target.checked ? [...p.styles, st] : p.styles.filter((x) => x !== st) })} />
                {STYLE_LABEL[st]}
              </label>
            ))}
          </fieldset>
          <div>
            <label htmlFor="ug-count" className="font-semibold text-sm block">How many</label>
            <select id="ug-count" className="input w-auto py-1.5" value={p.count} onChange={(e) => setP({ ...p, count: Number(e.target.value) })}>
              {[10, 20, 30, 50, 80].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <button type="submit" className="btn-primary" disabled={running || !p.styles.length}>
            <Icon.refresh /> {running ? "Writing…" : "Generate"}</button>
        </div>
      </form>

      {gen.isError && <ErrorBox error={gen.error} />}
      {running && d?.started_at && <Thinking since={new Date(d.started_at).getTime()} label="Writing utterances. This usually takes under a minute…" />}
      {d?.status === "failed" && d.error && <ErrorBox error={`Couldn't generate: ${d.error}`} />}

      {(d?.items.length ?? 0) > 0 && (
        <div className="card p-5 flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold flex-1 min-w-[200px]">{d!.items.length} utterances for {intent}
              {d!.fetched_at && <span className="text-muted font-normal text-sm"> · {ago(d!.fetched_at)}</span>}</p>
            <label htmlFor="ug-filter" className="sr-only">Show style</label>
            <select id="ug-filter" className="input w-auto py-1.5" value={style} onChange={(e) => setStyle(e.target.value as UtterStyle | "all")}>
              <option value="all">All styles</option>
              {styleIds.map((s) => <option key={s} value={s}>{STYLE_LABEL[s]}</option>)}
            </select>
            <button type="button" className="btn-outline btn-sm" onClick={exportCsv}>CSV</button>
            <button type="button" className="btn-outline btn-sm" onClick={exportJsonl}>JSONL</button>
            <button type="button" className="btn-outline btn-sm" onClick={exportNl}>Aligned NL</button>
          </div>
          {d!.dropped_slots > 0 && <p className="text-xs text-muted">{d!.dropped_slots} slot label{d!.dropped_slots === 1 ? " was" : "s were"} removed because the value wasn't in the sentence.</p>}
          <ul className="flex flex-col divide-y divide-line">
            {items.map((u) => <UtterRow key={u.text} u={u} label={STYLE_LABEL[u.style] ?? u.style} lang={lang} />)}
          </ul>
        </div>
      )}
    </Section>
  );
}

function UtterRow({ u, label, lang }: { u: Utterance; label: string; lang: string }) {
  const qc = useQueryClient();
  const [text, setText] = useState<string | null>(null);
  const edit = useMutation({
    mutationFn: (t: string | null) => api.editUtterance(lang, u.text, t),
    onSuccess: (d) => { qc.setQueryData(["utterances", lang], d); setText(null); },
  });
  return (
    <li className="py-2.5 flex flex-col gap-1">
      {text === null ? (
        <div className="flex items-start gap-2">
          <p className="text-lg flex-1" lang={lang === "hi" && u.style === "romanized" ? "hi-Latn" : lang}>{u.text}</p>
          <button type="button" className="icon-btn" aria-label={`Edit: ${u.text}`} title="Edit" onClick={() => setText(u.text)}><Icon.edit size={15} /></button>
          <button type="button" className="icon-btn" aria-label={`Delete: ${u.text}`} title="Delete" disabled={edit.isPending}
            onClick={() => edit.mutate(null)}><Icon.trash size={15} /></button>
        </div>
      ) : (
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); if (text.trim()) edit.mutate(text.trim()); }}>
          <label htmlFor={`ut-${u.text}`} className="sr-only">Utterance text</label>
          <input id={`ut-${u.text}`} className="input flex-1 min-w-[220px]" value={text} autoFocus onChange={(e) => setText(e.target.value)} />
          <button type="submit" className="btn-primary btn-sm" disabled={edit.isPending}>Save</button>
          <button type="button" className="btn-outline btn-sm" onClick={() => setText(null)}>Cancel</button>
          <p className="w-full text-xs text-muted">Slots whose values are no longer in the text are removed.</p>
        </form>
      )}
      {edit.isError && <ErrorBox error={edit.error} />}
      <p className="text-xs text-muted flex flex-wrap gap-1.5 items-center">
        <Chip>{label}</Chip><Chip>{u.tone}</Chip>
        {u.slots.map((s) => <Chip key={s.name + s.value} cls="bg-accent-soft text-accent-dark">{s.name}: {s.value}</Chip>)}
      </p>
      <code className="text-xs text-muted break-all">{u.annotated}</code>
    </li>
  );
}

// ---------------------------------------------------------------- what's new

function WhatsNew({ d: info }: { d: HV }) {
  const qc = useQueryClient();
  const lang = useLang();
  const q = useQuery({
    queryKey: ["voice-research", lang], queryFn: () => api.voiceResearch(lang),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 4000 : false),
  });
  const [months, setMonths] = useState(12);
  const [kind, setKind] = useState("all");
  const refresh = useMutation({ mutationFn: () => api.refreshVoiceResearch(lang, months), onSuccess: (d) => qc.setQueryData(["voice-research", lang], d) });
  const d = q.data;
  const running = d?.status === "running" || refresh.isPending;
  const kinds = [...new Set((d?.items ?? []).map((i) => i.kind))];
  const items = (d?.items ?? []).filter((i) => kind === "all" || i.kind === kind);

  return (
    <Section id="hv-new" title={`What's new in ${info.name} speech and NLU`}
      intro="The LLM searches the web for new models, datasets, papers, tools and news that aren't in the lists on this page. Every link is checked.">
      <div className="card p-5 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[220px] text-sm text-muted">
          {d?.fetched_at ? <>Last refreshed {ago(d.fetched_at)}.</> : "Not refreshed yet."}
        </div>
        <div>
          <label htmlFor="hv-months" className="text-sm font-semibold block">Look back</label>
          <select id="hv-months" className="input w-auto py-1.5" value={months} disabled={running} onChange={(e) => setMonths(Number(e.target.value))}>
            {[3, 6, 12, 24].map((m) => <option key={m} value={m}>{m} months</option>)}
          </select>
        </div>
        <button type="button" className="btn-primary" disabled={running} onClick={() => refresh.mutate()}>
          <Icon.refresh /> {running ? "Searching…" : "Refresh"}</button>
      </div>
      {q.isError && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
      {refresh.isError && <ErrorBox error={refresh.error} />}
      {running && d?.started_at && <Thinking since={new Date(d.started_at).getTime()} label="Searching models, datasets, papers and news. This takes a few minutes…" />}
      {d?.status === "failed" && d.error && <ErrorBox error={`Couldn't refresh: ${d.error}`} onRetry={() => refresh.mutate()} />}
      {d?.summary && <p className="text-body max-w-[780px]">{d.summary}</p>}
      {kinds.length > 1 && (
        <div role="group" aria-label="Filter by kind" className="flex flex-wrap gap-1.5">
          {["all", ...kinds].map((k) => (
            <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}
              className={`min-h-[36px] px-3 rounded-full border text-sm font-semibold ${kind === k ? "bg-accent text-white border-accent" : "bg-white border-line2 text-body hover:bg-ground"}`}>
              {k === "all" ? "All" : k}
            </button>
          ))}
        </div>
      )}
      <ul className="flex flex-col gap-3">
        {items.map((i) => (
          <li key={i.url} className="card p-4 flex flex-col gap-1.5">
            <div className="flex items-start gap-2">
              <p className="font-semibold flex-1"><Ext href={i.url}>{i.title}</Ext>{" "}
                <Chip>{i.kind}</Chip>{i.is_new && <> <Chip cls="bg-accent-soft text-accent-dark">New</Chip></>}
                {!i.verified && <> <Chip cls="bg-pp-bg text-pp-fg">Link unverified</Chip></>}</p>
              <RemoveFound job={`${lang === "hi" ? "hv" : "ev"}-research`} url={i.url} title={i.title} queryKey={["voice-research", lang]} />
            </div>
            <p className="text-xs text-muted">{[i.org, i.date && fmtDay(i.date), i.licence].filter(Boolean).join(" · ")}</p>
            <p className="text-sm text-body">{i.summary}</p>
            {i.result && <p className="text-sm"><span className="font-semibold">Result: </span>{i.result}</p>}
            <p className="text-sm text-muted">{i.why_it_matters}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
