import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { api, type Home as HomeT, type HomeCard } from "../api";
import { useMe } from "../components/Auth";
import { ErrorBox, Icon, ProgressBar, Ring, Thinking, storage } from "../components/ui";
import { useNews } from "./News";

type Active = NonNullable<HomeT["active"]>;

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

/** Grid width of each card on wide screens (12 columns). */
const SPAN: Record<string, string> = {
  continue: "lg:col-span-8", week: "lg:col-span-4", paths: "lg:col-span-12", news: "lg:col-span-7",
  picks: "lg:col-span-5", links: "lg:col-span-12", jobs: "lg:col-span-12",
};

export default function Home() {
  const qc = useQueryClient();
  const me = useMe();
  const [pathId, setPathId] = useState<number | undefined>(() => Number(storage.get("home:path")) || undefined);
  const [customizing, setCustomizing] = useState(false);
  const home = useQuery({ queryKey: ["home", pathId], queryFn: () => api.home(pathId) });
  const active = home.data?.active ?? null;

  // A running agent job on this path: poll until it finishes, then refresh.
  const runId = active?.last_run?.status === "running" ? active.last_run.id : null;
  const run = useQuery({
    queryKey: ["run", runId], queryFn: () => api.run(runId!), enabled: !!runId,
    refetchInterval: (q) => (q.state.data?.status === "running" ? 2500 : false),
  });
  useEffect(() => {
    if (run.data && run.data.status !== "running") qc.invalidateQueries({ queryKey: ["home"] });
  }, [run.data?.status, qc]); // eslint-disable-line react-hooks/exhaustive-deps

  if (home.isLoading) return <Shell><Thinking label="Loading…" /></Shell>;
  if (home.isError) return <Shell><ErrorBox error={home.error} onRetry={() => home.refetch()} /></Shell>;
  const data = home.data!;
  const choose = (id: number) => { setPathId(id); storage.set("home:path", String(id)); };
  const name = data.user.name && !["Learner", "Admin", "User"].includes(data.user.name) ? `, ${data.user.name}` : "";
  const cards = data.layout.filter((c) => c.on);

  const render = (c: HomeCard): ReactNode => {
    switch (c.id) {
      case "continue": return <ContinueCard active={active} />;
      case "week": return active ? <WeekCard week={active.week} /> : null;
      case "paths": return <PathsCard data={data} activeId={active?.id} onChoose={choose} />;
      case "news": return <NewsCard />;
      case "picks": return active?.current_module ? <PicksCard active={active} running={!!runId} /> : null;
      case "links": return <LinksCard data={data} />;
      case "jobs": return me.is_admin ? <JobsCard /> : null;
      default: return null;
    }
  };

  return (
    <Shell>
      <header className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[240px]">
          <h1 className="h-display text-3xl sm:text-[34px] leading-tight">{greeting()}{name}</h1>
          {active && <p className="text-muted mt-1">{active.title} · {active.pct}% complete</p>}
        </div>
        <button type="button" className="btn-outline btn-sm" onClick={() => setCustomizing(true)} aria-haspopup="dialog">
          <Icon.edit size={15} /> Customize
        </button>
      </header>

      {me.default_password && (
        <p className="text-sm bg-pp-bg text-pp-fg rounded-xl px-4 py-2.5">
          You're using the default password. <Link to="/settings" className="font-semibold underline">Change it</Link>
        </p>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 grid-flow-row-dense">
        {cards.map((c) => {
          const el = render(c);
          return el ? <div key={c.id} className={`min-w-0 ${SPAN[c.id] ?? "lg:col-span-6"}`}>{el}</div> : null;
        })}
      </div>
      {cards.length === 0 && <p className="card p-6 text-body">All cards are turned off. Use <strong>Customize</strong> to choose what you see here.</p>}
      {customizing && <Customize layout={data.layout} onClose={() => setCustomizing(false)} />}
    </Shell>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return <main className="max-w-[1200px] mx-auto w-full px-4 sm:px-8 pt-8 pb-28 flex flex-col gap-6">{children}</main>;
}

function Card({ title, to, toLabel, children, className = "" }: {
  title: string; to?: string; toLabel?: string; children: ReactNode; className?: string;
}) {
  return (
    <section className={`card h-full p-5 flex flex-col gap-4 ${className}`} aria-label={title}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[15px] font-semibold">{title}</h2>
        {to && <Link to={to} className="text-sm font-semibold text-accent hover:underline whitespace-nowrap">{toLabel ?? "See all"} →</Link>}
      </div>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------- cards

function ContinueCard({ active }: { active: Active | null }) {
  if (!active) {
    return (
      <Card title="Get started">
        <p className="text-body">Build a learning path from a goal, or create your own.</p>
        <div className="flex flex-wrap gap-2">
          <Link to="/setup" className="btn-primary">New learning goal</Link>
          <Link to="/paths" className="btn-outline">My paths</Link>
        </div>
      </Card>
    );
  }
  const c = active.continue;
  if (!c) {
    return (
      <Card title="Continue learning">
        <p className="text-lg font-semibold">You've finished {active.title}.</p>
        <Link to="/setup" className="btn-primary self-start">Start a new goal</Link>
      </Card>
    );
  }
  return (
    <section className="card h-full p-5 sm:p-6 flex flex-col gap-4 border-accent-line bg-gradient-to-br from-white to-accent-soft/50" aria-label="Continue learning">
      <span className="text-xs font-semibold uppercase tracking-wide text-accent">{c.started ? "Continue learning" : "Up next"}</span>
      <div className="flex flex-col gap-1">
        <h2 className="h-display text-2xl leading-snug">{c.title}</h2>
        <p className="text-muted text-sm">Module {c.module_idx + 1} · {c.module_title} · {c.est_minutes} min</p>
      </div>
      <ProgressBar pct={(100 * c.module_done) / c.module_lessons} label={`${c.module_done} of ${c.module_lessons} lessons in this module`} />
      <Link to={`/lessons/${c.lesson_id}`} className="btn-primary self-start"><Icon.play size={16} /> {c.started ? "Resume" : "Start lesson"}</Link>
    </section>
  );
}

function WeekCard({ week }: { week: Active["week"] }) {
  const h = Math.round(week.minutes / 6) / 10;
  return (
    <Card title="This week">
      <div className="flex items-center gap-4">
        <Ring value={week.minutes} max={week.goal_minutes} label={`${h} of ${week.goal_minutes / 60} hours`} />
        <div>
          <p className="h-display text-[28px] leading-none">{h} h</p>
          <p className="text-muted text-sm mt-1">of {week.goal_minutes / 60} h goal</p>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-3 text-center">
        <div className="rounded-xl bg-ground py-2.5"><dt className="text-xs text-muted">Lessons</dt><dd className="text-lg font-semibold">{week.lessons_done}</dd></div>
        <div className="rounded-xl bg-ground py-2.5"><dt className="text-xs text-muted">Questions</dt><dd className="text-lg font-semibold">{week.questions}</dd></div>
      </dl>
    </Card>
  );
}

function PathsCard({ data, activeId, onChoose }: { data: HomeT; activeId?: number; onChoose: (id: number) => void }) {
  return (
    <Card title="My paths" to="/paths" toLabel={data.hidden_paths ? `All paths (${data.hidden_paths} hidden)` : "All paths"}>
      {data.paths.length === 0 ? (
        <Link to="/setup" className="btn-outline self-start">+ New learning goal</Link>
      ) : (
        <ul className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))" }}>
          {data.paths.map((p) => (
            <li key={p.id}>
              <button type="button" onClick={() => onChoose(p.id)} aria-pressed={p.id === activeId}
                className={`w-full h-full text-left p-4 rounded-xl border flex flex-col gap-2.5 hover:shadow-sm ${p.id === activeId ? "border-accent border-2 bg-accent-soft/40" : "border-line bg-white"}`}>
                <span className="font-semibold leading-snug line-clamp-2">{p.title}</span>
                <ProgressBar pct={p.pct} label={p.status === "building" ? "Building…" : `${p.pct}%`} />
                <span className="text-xs text-muted flex justify-between gap-2">
                  <span>{p.kind === "interview" ? "Upskill Prep · " : ""}{p.done}/{p.lessons} lessons</span>
                  <span className="font-semibold text-body">{p.status === "building" ? "Building…" : `${p.pct}%`}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function NewsCard() {
  const news = useNews();
  const live = useQuery({ queryKey: ["news-live"], queryFn: () => api.liveNews(20), staleTime: 5 * 60_000,
    enabled: news.isSuccess && news.data.items.length === 0 });
  const digest = news.data?.items.slice(0, 5) ?? [];
  return (
    <Card title="Tech News" to="/news" toLabel="Open">
      {news.isLoading && <Thinking label="Loading…" />}
      {digest.length > 0 ? (
        <ul className="flex flex-col divide-y divide-line">
          {digest.map((i) => (
            <li key={i.url} className="py-2.5 first:pt-0">
              <a href={i.url} target="_blank" rel="noreferrer" className="font-medium leading-snug hover:text-accent">{i.title}</a>
              <p className="text-xs text-muted mt-0.5">{i.source}</p>
            </li>
          ))}
        </ul>
      ) : (
        <ul className="flex flex-col divide-y divide-line">
          {live.data?.items.slice(0, 5).map((h) => (
            <li key={h.id} className="py-2.5 first:pt-0">
              <a href={h.url} target="_blank" rel="noreferrer" className="font-medium leading-snug hover:text-accent">{h.title}</a>
              <p className="text-xs text-muted mt-0.5">{h.site} · Hacker News</p>
            </li>
          ))}
          {live.data && live.data.items.length === 0 && <li className="text-sm text-muted">No headlines right now.</li>}
        </ul>
      )}
    </Card>
  );
}

function PicksCard({ active, running }: { active: Active; running: boolean }) {
  const qc = useQueryClient();
  const mod = active.current_module!;
  const find = useMutation({
    mutationFn: () => api.findResources(active.id, [mod.id]),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["home"] }),
  });
  const searching = running || mod.resources_status === "searching" || find.isPending;
  const videos = active.videos.slice(0, 2);
  const papers = active.papers.slice(0, 2);
  return (
    <Card title={`For Module ${mod.idx + 1}`} to={`/paths/${active.id}#module-${mod.id}`} toLabel="Module">
      {videos.length + papers.length === 0 ? (
        <div className="flex flex-col gap-3 items-start">
          <p className="text-sm text-muted">{searching ? "Finding videos and papers…" : "No videos or papers yet."}</p>
          {searching ? <Thinking label="Working" /> : (
            <button type="button" className="btn-outline btn-sm" onClick={() => find.mutate()}><Icon.search size={15} /> Find videos & papers</button>
          )}
          {find.isError && <ErrorBox error={find.error} />}
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {videos.map((v) => (
            <li key={v.id}>
              <a href={v.url} target="_blank" rel="noreferrer" className="flex gap-3 items-center group">
                {v.thumbnail
                  ? <img src={v.thumbnail} alt="" className="w-[96px] h-[54px] rounded-lg object-cover shrink-0 bg-ground" />
                  : <span className="w-[96px] h-[54px] rounded-lg bg-[#1E2433] text-white flex items-center justify-center shrink-0"><Icon.play /></span>}
                <span className="min-w-0">
                  <span className="block font-medium leading-snug line-clamp-2 group-hover:text-accent">{v.title}</span>
                  <span className="block text-xs text-muted">{v.author}{v.duration_min ? ` · ${v.duration_min} min` : ""}</span>
                </span>
              </a>
            </li>
          ))}
          {papers.map((p) => (
            <li key={p.id} className="flex gap-3 items-center">
              <span className="w-[96px] h-[54px] rounded-lg bg-ground text-muted flex items-center justify-center shrink-0"><Icon.paper /></span>
              <span className="min-w-0">
                <a href={p.url} target="_blank" rel="noreferrer" className="block font-medium leading-snug line-clamp-2 hover:text-accent">{p.title}</a>
                <span className="block text-xs text-muted">{p.year ? `${p.year} · ` : ""}{p.lesson_id ? <Link to={`/lessons/${p.lesson_id}`} className="hover:underline">Summarize in lesson</Link> : "Paper"}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function LinksCard({ data }: { data: HomeT }) {
  return (
    <Card title="My links" to="/links" toLabel="Manage">
      {data.my_links.length === 0 ? <p className="text-sm text-muted">No saved links yet.</p> : (
        <ul className="flex flex-wrap gap-2">
          {data.my_links.slice(0, 12).map((l) => (
            <li key={l.id}>
              <a href={l.url} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1.5 max-w-[280px] px-3 py-2 rounded-full border border-line2 bg-white hover:border-accent text-sm">
                <span className="truncate font-medium">{l.title}</span>
                {l.provider && <span className="text-xs text-muted shrink-0">{l.provider}</span>}
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function JobsCard() {
  const q = useQuery({ queryKey: ["jobs"], queryFn: api.jobs });
  const jobs = q.data?.jobs.slice(0, 4) ?? [];
  return (
    <Card title="Hot jobs" to="/career#jobs" toLabel="Career">
      {q.isLoading && <Thinking label="Loading…" />}
      {q.data && jobs.length === 0 && <p className="text-sm text-muted">No job search yet. Run one from Career.</p>}
      <ul className="grid gap-x-8 gap-y-3 md:grid-cols-2">
        {jobs.map((j) => (
          <li key={j.url} className="border-t border-line pt-2.5">
            <a href={j.url} target="_blank" rel="noreferrer" className="font-medium leading-snug hover:text-accent">{j.title}</a>
            <p className="text-xs text-muted mt-0.5">{[j.company, j.location, j.work_mode].filter(Boolean).join(" · ")}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

// ---------------------------------------------------------------- customize

function Customize({ layout, onClose }: { layout: HomeCard[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [cards, setCards] = useState(layout);
  const save = useMutation({
    mutationFn: (c: { id: string; on: boolean }[]) => api.homeLayout(c),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["home"] }); onClose(); },
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  const move = (i: number, d: number) => {
    const next = [...cards];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    setCards(next);
  };
  return (
    <div className="fixed inset-0 z-40 bg-black/30 flex items-end sm:items-center justify-center p-0 sm:p-6" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div role="dialog" aria-modal="true" aria-labelledby="cust-h"
        className="bg-white w-full sm:max-w-[440px] rounded-t-2xl sm:rounded-2xl shadow-xl p-5 flex flex-col gap-4 max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between">
          <h2 id="cust-h" className="text-lg font-semibold">Customize Home</h2>
          <button type="button" aria-label="Close" className="w-9 h-9 rounded-lg hover:bg-ground flex items-center justify-center" onClick={onClose}><Icon.close /></button>
        </div>
        <p className="text-sm text-muted -mt-2">Choose the cards you see and their order.</p>
        <ul className="flex flex-col gap-1.5">
          {cards.map((c, i) => (
            <li key={c.id} className="flex items-center gap-2 p-2 pl-3 rounded-xl border border-line">
              <label className="flex-1 flex items-center gap-3 min-h-[36px] cursor-pointer">
                <input type="checkbox" className="w-4 h-4" checked={c.on}
                  onChange={(e) => setCards(cards.map((x) => (x.id === c.id ? { ...x, on: e.target.checked } : x)))} />
                <span className={c.on ? "font-medium" : "text-muted"}>{c.label}</span>
              </label>
              <button type="button" aria-label={`Move ${c.label} up`} disabled={i === 0} onClick={() => move(i, -1)}
                className="w-9 h-9 rounded-lg hover:bg-ground disabled:opacity-30 flex items-center justify-center"><Icon.up size={16} /></button>
              <button type="button" aria-label={`Move ${c.label} down`} disabled={i === cards.length - 1} onClick={() => move(i, 1)}
                className="w-9 h-9 rounded-lg hover:bg-ground disabled:opacity-30 flex items-center justify-center"><Icon.down size={16} /></button>
            </li>
          ))}
        </ul>
        {save.isError && <ErrorBox error={save.error} />}
        <div className="flex flex-wrap gap-2 justify-between">
          <button type="button" className="btn-outline btn-sm" disabled={save.isPending} onClick={() => save.mutate([])}>Reset to default</button>
          <div className="flex gap-2">
            <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
            <button type="button" className="btn-primary btn-sm" disabled={save.isPending}
              onClick={() => save.mutate(cards.map(({ id, on }) => ({ id, on })))}>Save</button>
          </div>
        </div>
      </div>
    </div>
  );
}
