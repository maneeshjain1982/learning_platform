import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Home as HomeT, type Run } from "../api";
import { useAsk } from "../components/AskLLM";
import { MyLinksSection } from "../components/Manage";
import { AgentSteps, ErrorBox, Icon, LinkCard, PaperRow, ProgressBar, Ring, Thinking, VideoCard, storage } from "../components/ui";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function Home() {
  const qc = useQueryClient();
  const [pathId, setPathId] = useState<number | undefined>(() => Number(storage.get("home:path")) || undefined);
  const home = useQuery({ queryKey: ["home", pathId], queryFn: () => api.home(pathId) });
  const active = home.data?.active;

  // A running agent job on this path: poll until it finishes, then refresh the page data.
  const runId = active?.last_run?.status === "running" ? active.last_run.id : null;
  const run = useQuery({
    queryKey: ["run", runId], queryFn: () => api.run(runId!), enabled: !!runId,
    refetchInterval: (q) => (q.state.data?.status === "running" ? 2500 : false),
  });
  useEffect(() => {
    if (run.data && run.data.status !== "running") qc.invalidateQueries({ queryKey: ["home"] });
  }, [run.data?.status, qc]); // eslint-disable-line react-hooks/exhaustive-deps

  const choose = (id: number) => { setPathId(id); storage.set("home:path", String(id)); };

  if (home.isLoading) return <main className="max-w-[1280px] mx-auto w-full p-8"><Thinking label="Loading your home page…" /></main>;
  if (home.isError) return <main className="max-w-[1280px] mx-auto w-full p-8"><ErrorBox error={home.error} onRetry={() => home.refetch()} /></main>;
  const data = home.data!;
  if (!active) return <EmptyHome data={data} />;

  return (
    <main className="max-w-[1280px] mx-auto w-full px-4 sm:px-8 pt-8 pb-28 flex flex-col gap-8">
      <section className="flex flex-wrap gap-6 items-stretch">
        <div className="flex-[999_1_560px] min-w-0 flex flex-col gap-4">
          <p className="text-muted font-medium">{active.title} · {active.done} of {active.lessons} lessons done</p>
          <h1 className="h-display text-3xl sm:text-4xl leading-tight">
            {greeting()}{data.user.name && data.user.name !== "Learner" ? `, ${data.user.name}` : ""}.{" "}
            {active.continue ? <>Today's focus is <span className="text-accent">{active.continue.title.toLowerCase()}</span>.</> : "You've finished this path!"}
          </h1>
          {active.continue && <FocusNote lessonId={active.continue.lesson_id} initial={active.focus_note} />}
          {active.continue && <ContinueCard c={active.continue} />}
        </div>
        <WeekCard week={active.week} />
      </section>

      <section aria-labelledby="paths-h" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="paths-h" className="h-display text-[22px]">Your learning paths</h2>
          <div className="flex flex-wrap gap-2">
            <Link to="/paths" className="btn-outline"><Icon.edit size={16} /> Manage paths</Link>
            <Link to="/setup" className="btn-outline">+ New learning goal</Link>
          </div>
        </div>
        {data.hidden_paths > 0 && (
          <p className="text-sm text-muted -mt-2">
            {data.hidden_paths} path{data.hidden_paths > 1 ? "s are" : " is"} hidden from this page. <Link to="/paths" className="text-accent font-semibold hover:underline">Show again</Link>
          </p>
        )}
        <div role="tablist" aria-label="Learning paths" className="flex flex-wrap gap-2">
          {data.paths.map((p) => (
            <button key={p.id} type="button" role="tab" aria-selected={p.id === active.id} onClick={() => choose(p.id)}
              className={`pill ${p.id === active.id ? "bg-ink text-white border-ink" : "bg-white text-body border-line2 hover:bg-ground"}`}>
              {p.kind === "interview" && <span className="chip bg-pp-bg text-pp-fg mr-2">Interview prep</span>}
              {p.title} · {p.status === "building" ? "building…" : p.pct ? `${p.pct}%` : "Not started"}
            </button>
          ))}
        </div>
        {active.modules_detail.length === 0 && (
          <p className="card p-5 text-body">This course has no modules yet. <Link to={`/paths/${active.id}?edit=1`} className="text-accent font-semibold hover:underline">Add modules and lessons</Link></p>
        )}
        <ol className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          {active.modules_detail.map((m) => (
            <li key={m.id}>
              <Link to={`/paths/${active.id}#module-${m.id}`}
                className={`h-full flex flex-col gap-1.5 p-4 rounded-xl bg-white hover:shadow-sm ${m.state === "now" ? "border-2 border-accent" : "border border-line"}`}>
                <span className={`text-xs font-semibold uppercase tracking-wide ${m.state === "done" ? "text-ok" : m.state === "now" ? "text-accent" : "text-muted"}`}>
                  {m.state === "done" ? "Completed" : m.state === "now" ? "In progress" : "Up next"}
                </span>
                <span className="font-semibold">{m.idx + 1}. {m.title}</span>
                <span className="text-[13px] text-muted">{m.done}/{m.lessons} lessons · {Math.round(m.minutes / 6) / 10} h</span>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <MyLinksSection links={data.my_links} pathId={null} title="My courses & links"
        intro={`Courses and pages you added yourself: general ones, plus those for ${active.title}.`} />

      {active.current_module && active.lessons > 0 && (
        <Recommendations home={active} running={!!runId} />
      )}

      {(run.data || active.last_run) && <AgentStrip home={active} liveRun={run.data ?? null} />}
    </main>
  );
}

function FocusNote({ lessonId, initial }: { lessonId: number; initial: string | null }) {
  const note = useQuery({
    queryKey: ["focus", lessonId], queryFn: () => api.focus(lessonId).then((r) => r.text),
    enabled: !initial, retry: false, staleTime: Infinity,
  });
  const text = initial ?? note.data;
  if (!text) return note.isLoading ? <Thinking label="Your companion is writing today's note…" /> : null;
  return <p className="max-w-[680px] text-body">{text}</p>;
}

function ContinueCard({ c }: { c: NonNullable<NonNullable<HomeT["active"]>["continue"]> }) {
  return (
    <div className="card p-5 flex flex-wrap gap-5 items-center">
      <div aria-hidden="true" className="w-[180px] h-[100px] rounded-[10px] bg-[#1E2433] text-white flex items-center justify-center"><Icon.play size={36} /></div>
      <div className="flex-[1_1_240px] min-w-0 flex flex-col gap-1.5">
        <span className="text-[13px] font-semibold text-ok uppercase tracking-wide">{c.started ? "Continue learning" : "Start next lesson"}</span>
        <h2 className="text-xl font-semibold">Lesson {c.module_idx + 1}.{c.lesson_idx + 1} · {c.title}</h2>
        <p className="text-muted">Module {c.module_idx + 1}: {c.module_title} · {c.est_minutes} min</p>
        <div className="mt-1.5"><ProgressBar pct={(100 * c.module_done) / c.module_lessons} label={`Module ${c.module_done} of ${c.module_lessons} lessons done`} /></div>
      </div>
      <Link to={`/lessons/${c.lesson_id}`} className="btn-primary">{c.started ? "Resume lesson" : "Start lesson"}</Link>
    </div>
  );
}

function WeekCard({ week }: { week: NonNullable<HomeT["active"]>["week"] }) {
  const h = Math.round(week.minutes / 6) / 10;
  return (
    <aside aria-labelledby="week-h" className="card flex-[1_1_260px] p-6 flex flex-col gap-4">
      <h2 id="week-h" className="text-base font-semibold">Last 7 days</h2>
      <div className="flex items-center gap-4">
        <Ring value={week.minutes} max={week.goal_minutes} label={`${h} of ${week.goal_minutes / 60} hours`} />
        <div>
          <p className="h-display text-[28px]">{h} h</p>
          <p className="text-muted">of your {week.goal_minutes / 60} h goal</p>
        </div>
      </div>
      <ul className="flex flex-col gap-2.5 text-body">
        <li className="flex justify-between"><span>Lessons done</span><strong className="text-ink">{week.lessons_done}</strong></li>
        <li className="flex justify-between"><span>Questions asked</span><strong className="text-ink">{week.questions}</strong></li>
      </ul>
    </aside>
  );
}

function Recommendations({ home, running }: { home: NonNullable<HomeT["active"]>; running: boolean }) {
  const qc = useQueryClient();
  const { ask } = useAsk();
  const mod = home.current_module!;
  const find = useMutation({
    mutationFn: () => api.findResources(home.id, [mod.id]),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["home"] }),
  });
  const searching = running || mod.resources_status === "searching" || find.isPending;
  const noVideos = home.videos.length === 0;

  return (
    <>
      <section aria-labelledby="vid-h" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h2 id="vid-h" className="h-display text-[22px]">Video lectures for Module {mod.idx + 1}</h2>
            <p className="text-muted mt-1">Found by the Video Search agent; every link is checked on YouTube.</p>
          </div>
          <Link to={`/discover?q=${encodeURIComponent(mod.title)}`} className="font-semibold text-accent hover:underline">See more in Discover</Link>
        </div>
        {noVideos ? (
          <div className="card p-6 flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[240px]">
              <p className="font-semibold">{searching ? "Searching for videos…" : "No videos for this module yet."}</p>
              <p className="text-muted text-sm mt-1">
                {searching ? "The agents are searching YouTube and checking each link. This takes a few minutes; the page updates when they finish."
                  : "The agents search YouTube with Claude's web search, check each link, then pick papers. Takes a few minutes and uses your Claude plan."}
              </p>
            </div>
            {searching ? <Thinking label="Working" /> : (
              <button type="button" className="btn-primary" onClick={() => find.mutate()}>
                <Icon.search /> Find videos & papers
              </button>
            )}
            {find.isError && <div className="w-full"><ErrorBox error={find.error} /></div>}
          </div>
        ) : (
          <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }}>
            {home.videos.slice(0, 4).map((v) => (
              <VideoCard key={v.id} r={v} footer={
                <button type="button" className="btn-outline btn-sm" onClick={() => ask(`I'm watching "${v.title}". What should I focus on?`)}>Ask about it</button>
              } />
            ))}
          </div>
        )}
      </section>

      <section className="flex flex-wrap gap-6">
        <div role="region" aria-labelledby="crs-h" className="flex-[1_1_480px] min-w-0 flex flex-col gap-3">
          <div>
            <h2 id="crs-h" className="h-display text-[22px]">Find full courses</h2>
            <p className="text-muted mt-1">Search terms for Module {mod.idx + 1}. Opens Coursera or Udemy in a new tab.</p>
          </div>
          {home.course_links.map((l) => (
            <LinkCard key={l.url} {...l} hint={l.source === "coursera" ? "Structured courses, often with certificates" : "Practical, project-based courses"} />
          ))}
        </div>
        <div role="region" aria-labelledby="pap-h" className="flex-[1_1_420px] min-w-0 flex flex-col gap-3">
          <h2 id="pap-h" className="h-display text-[22px]">Related papers</h2>
          {home.papers.length === 0 ? (
            <p className="text-muted card p-5">{searching ? "Searching arXiv…" : "No papers for this module yet. Use “Find videos & papers” above."}</p>
          ) : home.papers.slice(0, 3).map((p) => <PaperRow key={p.id} r={p} />)}
        </div>
      </section>
    </>
  );
}

function AgentStrip({ home, liveRun }: { home: NonNullable<HomeT["active"]>; liveRun: Run | null }) {
  const qc = useQueryClient();
  const run = liveRun ?? home.last_run!;
  const [open, setOpen] = useState(false);
  const refresh = useMutation({
    mutationFn: () => api.findResources(home.id, home.current_module ? [home.current_module.id] : undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["home"] }),
  });
  const running = run?.status === "running";
  return (
    <section aria-labelledby="ag-h" className="card border-dashed border-[#C9CED8] p-5 flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="ag-h" className="text-[15px] font-semibold flex-1">
          Companion agents · {running ? "working now" : run?.status === "failed" ? "last run failed" : `last run ${new Date(run!.finished_at ?? run!.started_at).toLocaleString()}`}
        </h2>
        <button type="button" className="btn-outline btn-sm" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Hide details" : "Show details"}</button>
        <button type="button" className="btn-outline btn-sm" disabled={running || refresh.isPending} onClick={() => refresh.mutate()}>
          <Icon.refresh size={16} /> Refresh this module
        </button>
      </div>
      {!open && run && (
        <ul className="flex flex-wrap gap-2">
          {run.steps.map((s) => (
            <li key={s.agent} className={`chip px-2.5 py-1.5 text-[13px] font-medium ${s.status === "done" ? "bg-ok-soft text-ok-dark" : s.status === "failed" ? "bg-yt-bg text-yt-fg" : s.status === "running" ? "bg-accent-soft text-accent-dark" : "bg-[#F1F3F6] text-muted"}`}>
              {s.status === "done" && <Icon.check size={14} />}{s.agent}
            </li>
          ))}
        </ul>
      )}
      {open && run && <AgentSteps steps={run.steps} />}
      {run?.error && <ErrorBox error={run.error} />}
      {refresh.isError && <ErrorBox error={refresh.error} />}
    </section>
  );
}

function EmptyHome({ data }: { data: HomeT }) {
  const navigate = useNavigate();
  return (
    <main className="max-w-[1100px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-8">
      <div className="flex flex-col gap-4 max-w-[720px]">
        <h1 className="h-display text-3xl">Welcome to Study Companion</h1>
        <p className="text-body">
          {data.hidden_paths > 0
            ? `All ${data.hidden_paths} of your paths are hidden from the home page.`
            : "Tell your companion what you want to learn and it will build a step-by-step path, or create your own course."}
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-primary" onClick={() => navigate("/setup")}>Set up a learning goal</button>
          <Link to="/paths" className="btn-outline">{data.hidden_paths > 0 ? "Manage paths" : "Create my own course"}</Link>
        </div>
      </div>
      <MyLinksSection links={data.my_links} pathId={null} title="My courses & links" />
    </main>
  );
}
