import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api, type QAItem, type QAStatus } from "../api";
import { ErrorBox, Icon, Markdown, Thinking } from "./ui";

type Filter = "all" | "todo" | "review" | "known";
const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "todo", label: "Not yet known" },
  { value: "review", label: "Review again" },
  { value: "known", label: "Know it" },
];

/** Review questions for every lesson of one course: reveal the answer, then mark it. */
export default function ReviewQA({ slug, lessonCount }: { slug: string; lessonCount: number }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["course-qa", slug], queryFn: () => api.courseQA(slug),
    refetchInterval: (query) => (query.state.data?.job.status === "running" ? 4000 : false),
  });
  const [perLesson, setPerLesson] = useState(2);
  const [filter, setFilter] = useState<Filter>("all");
  const [lesson, setLesson] = useState<number | "all">("all");
  const [openAll, setOpenAll] = useState(false);
  const gen = useMutation({
    mutationFn: () => api.generateQA(slug, perLesson),
    onSuccess: (d) => qc.setQueryData(["course-qa", slug], d),
  });

  const d = q.data;
  const running = d?.job.status === "running" || gen.isPending;
  const status = d?.job.status;
  const prev = useRef(status);
  useEffect(() => {  // refresh the course card's "x of y known" once a run finishes
    if (prev.current === "running" && status !== "running") qc.invalidateQueries({ queryKey: ["academy"] });
    prev.current = status;
  }, [status, qc]);

  const items = d?.items ?? [];
  const shown = items.filter((i) =>
    (lesson === "all" || i.lesson_idx === lesson) &&
    (filter === "all" || (filter === "todo" ? i.status !== "known" : i.status === filter)));
  const known = items.filter((i) => i.status === "known").length;
  const lessonsWithQA = [...new Set(items.map((i) => i.lesson_idx))];

  const onGenerate = () => {
    if (items.length && !confirm("Write a new set of questions for this course? Your marks are kept only for questions that come back unchanged.")) return;
    gen.mutate();
  };

  return (
    <div className="flex flex-col gap-3 pt-3 border-t border-line">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="font-semibold flex-1 min-w-[200px]">
          Review Q&A {items.length > 0 && <span className="text-muted font-normal text-sm">· {known} of {items.length} known</span>}
        </h4>
        <label htmlFor={`pl-${slug}`} className="text-sm">Questions per lesson</label>
        <select id={`pl-${slug}`} className="input w-auto py-1.5" value={perLesson} disabled={running}
          onChange={(e) => setPerLesson(Number(e.target.value))}>
          {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
        <button type="button" className="btn-outline btn-sm" disabled={running} onClick={onGenerate}>
          <Icon.refresh size={15} /> {running ? "Writing…" : items.length ? "Write new questions" : "Write questions"}
        </button>
      </div>

      {q.isLoading && <Thinking label="Loading…" />}
      {q.isError && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
      {gen.isError && <ErrorBox error={gen.error} />}
      {running && d?.job.started_at && (
        <Thinking since={new Date(d.job.started_at).getTime()}
          label={`Writing ${perLesson * lessonCount} questions and checking their sources. Larger courses take several minutes…`} />
      )}
      {d?.job.status === "failed" && d.job.error && <ErrorBox error={`Couldn't write the questions: ${d.job.error}`} onRetry={() => gen.mutate()} />}
      {d && !items.length && !running && d.job.status !== "failed" && (
        <p className="text-sm text-muted">No questions yet. The LLM writes them for each lesson, checks the facts against Anthropic's docs, and links the sources.</p>
      )}

      {items.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <div role="group" aria-label="Show questions" className="flex flex-wrap gap-1.5">
              {FILTERS.map((f) => (
                <button key={f.value} type="button" aria-pressed={filter === f.value} onClick={() => setFilter(f.value)}
                  className={`min-h-[36px] px-3 rounded-full border text-sm font-semibold ${filter === f.value ? "bg-accent text-white border-accent" : "bg-white border-line2 text-body hover:bg-ground"}`}>
                  {f.label}
                </button>
              ))}
            </div>
            <label htmlFor={`ls-${slug}`} className="sr-only">Lesson</label>
            <select id={`ls-${slug}`} className="input w-auto py-1.5 max-w-[280px]" value={lesson}
              onChange={(e) => setLesson(e.target.value === "all" ? "all" : Number(e.target.value))}>
              <option value="all">All lessons</option>
              {lessonsWithQA.map((i) => <option key={i} value={i}>{i + 1}. {d!.lessons[i]}</option>)}
            </select>
            <button type="button" className="text-sm text-accent font-semibold min-h-[36px]" onClick={() => setOpenAll(!openAll)}>
              {openAll ? "Hide all answers" : "Show all answers"}
            </button>
          </div>
          {shown.length === 0 && <p className="text-sm text-muted">Nothing here with this filter.</p>}
          <ol className="flex flex-col gap-2">
            {shown.map((i, n) => {
              const showHeader = n === 0 || shown[n - 1].lesson_idx !== i.lesson_idx;
              return (
                <li key={i.id} className="flex flex-col gap-2">
                  {showHeader && <p className="text-xs font-semibold text-muted uppercase tracking-wide mt-2">Lesson {i.lesson_idx + 1}: {i.lesson_title}</p>}
                  <QACard i={i} slug={slug} forceOpen={openAll} />
                </li>
              );
            })}
          </ol>
        </>
      )}
    </div>
  );
}

function QACard({ i, slug, forceOpen }: { i: QAItem; slug: string; forceOpen: boolean }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const isOpen = open || forceOpen;
  const mark = useMutation({
    mutationFn: (s: QAStatus) => api.setQAStatus(i.id, s),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["course-qa", slug] }); qc.invalidateQueries({ queryKey: ["academy"] }); },
  });
  const tone = i.status === "known" ? "border-ok/40 bg-ok-soft/40" : i.status === "review" ? "border-[#F2C77B] bg-pp-bg/40" : "border-line";
  return (
    <div className={`rounded-xl border p-3.5 flex flex-col gap-2 ${tone}`}>
      <button type="button" aria-expanded={isOpen} onClick={() => setOpen(!open)} className="flex items-start gap-2 text-left">
        <Icon.chevron className={`mt-0.5 shrink-0 text-muted transition-transform ${isOpen ? "rotate-90" : ""}`} />
        <span className="flex-1 font-semibold">{i.question}</span>
        {i.status !== "new" && <span className={`chip ${i.status === "known" ? "bg-ok-soft text-ok-dark" : "bg-pp-bg text-pp-fg"}`}>{i.status === "known" ? "Know it" : "Review again"}</span>}
      </button>
      {isOpen && (
        <div className="pl-6 flex flex-col gap-2">
          <Markdown className="text-sm">{i.answer_md}</Markdown>
          {i.key_points.length > 0 && (
            <div className="text-sm">
              <p className="font-semibold">A good answer covers</p>
              <ul className="list-disc pl-5 text-body">{i.key_points.map((k) => <li key={k}>{k}</li>)}</ul>
            </div>
          )}
          {i.references.length > 0 && (
            <p className="text-xs text-muted flex flex-wrap gap-x-3 gap-y-1">
              Sources:{i.references.map((r) => (
                <a key={r.url} href={r.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                  {r.title}{!r.verified && " (unverified)"}
                </a>
              ))}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-outline btn-sm" disabled={mark.isPending} aria-pressed={i.status === "known"}
              onClick={() => mark.mutate(i.status === "known" ? "new" : "known")}><Icon.check size={15} /> Know it</button>
            <button type="button" className="btn-outline btn-sm" disabled={mark.isPending} aria-pressed={i.status === "review"}
              onClick={() => mark.mutate(i.status === "review" ? "new" : "review")}>Review again</button>
          </div>
        </div>
      )}
    </div>
  );
}
