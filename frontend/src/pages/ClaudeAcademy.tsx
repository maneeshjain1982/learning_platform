import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api, type Academy, type AcademyCourse, type CourseStatus } from "../api";
import AIUpdates from "../components/AIUpdates";
import { ErrorBox, Icon, ProgressBar, Thinking } from "../components/ui";

const STATUS: { value: CourseStatus; label: string }[] = [
  { value: "todo", label: "To do" },
  { value: "doing", label: "In progress" },
  { value: "done", label: "Done" },
];

const hours = (h: number | null) =>
  h === null ? null : h < 1 ? `${Math.round(h * 60)} min` : `${h} hr`;

function fmtDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** Free Anthropic courses on academy.claude.com, with the agent track first and your status on each. */
export default function ClaudeAcademy() {
  const q = useQuery({ queryKey: ["academy"], queryFn: api.academy });
  const qc = useQueryClient();
  const navigate = useNavigate();
  const makePath = useMutation({
    mutationFn: api.academyPath,
    onSuccess: (r) => { qc.invalidateQueries(); navigate(`/paths/${r.path_id}`); },
  });

  if (q.isLoading) return <main className="p-8"><Thinking label="Loading courses…" /></main>;
  if (q.isError) return <main className="p-8"><ErrorBox error={q.error} onRetry={() => q.refetch()} /></main>;
  const d = q.data!;
  const track = d.courses.filter((c) => c.group === "agents").sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  const trackDone = track.filter((c) => c.status === "done").length;
  const others = d.groups.filter((g) => g.id !== "agents");

  return (
    <main className="max-w-[1100px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="h-display text-3xl">Claude learning</h1>
        <p className="text-body max-w-[760px]">
          Anthropic's free courses on <a className="text-accent font-semibold" href={d.base_url} target="_blank" rel="noreferrer">Claude Academy</a> (formerly
          Anthropic Academy). The agent builder track below is the order to take them in if you want to build Claude agents.
          Sign up on the site with your email to take a course; most award a badge you can add to LinkedIn.
        </p>
        <p className="text-xs text-muted">Course list checked {fmtDate(d.checked_on)}. Courses change, so check the site for new ones.</p>
      </header>

      <AIUpdates />

      <TrackSummary d={d} done={trackDone} total={track.length}
        onPath={() => makePath.mutate()} busy={makePath.isPending} />
      {makePath.isError && <ErrorBox error={makePath.error} />}

      <section aria-labelledby="track-h" className="flex flex-col gap-4">
        <div>
          <h2 id="track-h" className="h-display text-2xl">Agent builder track</h2>
          <p className="text-muted">{d.groups.find((g) => g.id === "agents")?.summary}</p>
        </div>
        <ol className="flex flex-col gap-4">
          {track.map((c) => <li key={c.slug}><CourseCard c={c} pathId={d.path_id} /></li>)}
        </ol>
      </section>

      <section aria-labelledby="more-h" className="flex flex-col gap-3">
        <h2 id="more-h" className="h-display text-2xl">More from Claude Academy</h2>
        {others.map((g) => {
          const list = d.courses.filter((c) => c.group === g.id);
          return (
            <details key={g.id} className="card group">
              <summary className="flex items-center gap-3 min-h-[56px] px-5 py-3 cursor-pointer list-none">
                <Icon.chevron className="text-muted transition-transform group-open:rotate-90" />
                <span className="flex-1">
                  <span className="font-semibold">{g.title}</span>
                  <span className="text-muted text-sm"> · {list.length} course{list.length === 1 ? "" : "s"}</span>
                  <span className="block text-sm text-muted">{g.summary}</span>
                </span>
              </summary>
              <ul className="flex flex-col gap-3 px-5 pb-5">
                {list.map((c) => <li key={c.slug}><CourseCard c={c} pathId={null} compact /></li>)}
              </ul>
            </details>
          );
        })}
      </section>
    </main>
  );
}

function TrackSummary({ d, done, total, onPath, busy }:
  { d: Academy; done: number; total: number; onPath: () => void; busy: boolean }) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  return (
    <section aria-label="Agent track progress" className="card p-5 flex flex-wrap items-center gap-5">
      <div className="flex-1 min-w-[240px] flex flex-col gap-2">
        <p className="font-semibold">
          {d.track.courses} courses · about {Math.round(d.track.hours)} hours · {d.track.lessons} lessons
        </p>
        <ProgressBar pct={pct} label={`${done} of ${total} courses done`} />
        <p className="text-sm text-muted">{done} of {total} courses done</p>
      </div>
      {d.path_id ? (
        <Link to={`/paths/${d.path_id}`} className="btn-outline">Open my study path</Link>
      ) : (
        <div className="flex flex-col gap-1 max-w-[340px]">
          <button type="button" className="btn-primary" onClick={onPath} disabled={busy}>
            <Icon.plus /> {busy ? "Adding…" : "Add track to My paths"}
          </button>
          <span className="text-xs text-muted">One module per course and one lesson per course lesson, each linked to
            the course, so you can tick lessons off, take notes and ask the tutor.</span>
        </div>
      )}
    </section>
  );
}

function CourseCard({ c, pathId, compact = false }: { c: AcademyCourse; pathId: number | null; compact?: boolean }) {
  const qc = useQueryClient();
  const set = useMutation({
    mutationFn: (s: CourseStatus) => api.setCourseStatus(c.slug, s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academy"] }),
  });
  const h = hours(c.hours);
  const facts = [c.level, h, `${c.lessons} lessons`, c.quizzes ? `${c.quizzes} quiz${c.quizzes > 1 ? "zes" : ""}` : null]
    .filter(Boolean) as string[];
  const done = c.status === "done";

  return (
    <article className={`${compact ? "border border-line rounded-xl" : "card"} p-5 flex flex-col gap-3 ${done ? "bg-ok-soft/40" : ""}`}>
      <div className="flex flex-wrap items-start gap-3">
        {c.order !== null && (
          <span aria-hidden="true" className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center font-bold text-sm ${done ? "bg-ok text-white" : "bg-accent-soft text-accent-dark"}`}>
            {done ? <Icon.check size={16} /> : c.order}
          </span>
        )}
        <div className="flex-1 min-w-[220px]">
          <h3 className="font-semibold text-lg leading-snug">
            <a href={c.url} target="_blank" rel="noreferrer" className="hover:text-accent inline-flex items-baseline gap-1.5">
              {c.title} <Icon.external size={14} className="text-muted shrink-0" />
              <span className="sr-only">(opens Claude Academy in a new tab)</span>
            </a>
          </h3>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {facts.map((f) => <span key={f} className="chip bg-[#F1F3F6] text-body">{f}</span>)}
            <span className={`chip ${c.badge ? "bg-ok-soft text-ok-dark" : "bg-[#F1F3F6] text-muted"}`}>
              {c.badge ? "Completion badge" : "No badge"}
            </span>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor={`st-${c.slug}`} className="sr-only">Status of {c.title}</label>
          <select id={`st-${c.slug}`} className="input w-auto py-1.5" value={c.status} disabled={set.isPending}
            onChange={(e) => set.mutate(e.target.value as CourseStatus)}>
            {STATUS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      <p className="text-body">{c.summary}</p>
      {c.why && (
        <p className="text-sm p-3 rounded-lg bg-[#F6F8FF] border border-accent-line">
          <span className="font-semibold">Why it matters for agents: </span>{c.why}
        </p>
      )}
      {c.prereqs && <p className="text-sm text-muted"><span className="font-semibold text-body">Before this:</span> {c.prereqs}</p>}
      {set.isError && <ErrorBox error={set.error} />}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {c.outline.length > 0 && (
          <details className="flex-1 min-w-[240px]">
            <summary className="cursor-pointer text-sm font-semibold text-accent min-h-[36px] flex items-center">
              Show all {c.outline.reduce((n, s) => n + s.lessons.length, 0)} lessons
            </summary>
            <div className="mt-2 flex flex-col gap-3">
              {c.outline.map((s) => (
                <div key={s.title}>
                  {c.outline.length > 1 && <p className="text-sm font-semibold mb-1">{s.title}</p>}
                  <ol className="list-decimal pl-5 text-sm text-body flex flex-col gap-0.5">
                    {s.lessons.map((t) => <li key={t}>{t}</li>)}
                  </ol>
                </div>
              ))}
            </div>
          </details>
        )}
        {pathId && c.path_progress && (
          <Link to={`/paths/${pathId}#module-${c.path_progress.module_id}`} className="text-sm text-accent font-semibold">
            {c.path_progress.done} of {c.path_progress.total} lessons ticked off in your path
          </Link>
        )}
      </div>
    </article>
  );
}
