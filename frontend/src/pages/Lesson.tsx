import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type Lesson } from "../api";
import { AskLLMPanel, useAsk } from "../components/AskLLM";
import { ErrorBox, Icon, LinkCard, Markdown, PaperRow, Thinking, VideoCard } from "../components/ui";

export default function LessonPage() {
  const id = Number(useParams().id);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { setLesson } = useAsk();
  const lesson = useQuery({
    queryKey: ["lesson", id], queryFn: () => api.lesson(id),
    refetchInterval: (q) => (q.state.data?.notes_status === "writing" ? 3000 : false),
  });
  const path = useQuery({
    queryKey: ["path", lesson.data?.path.id], queryFn: () => api.path(lesson.data!.path.id), enabled: !!lesson.data,
  });
  const L = lesson.data;

  // Give the floating Ask LLM drawer (narrow screens) this lesson as context.
  useEffect(() => {
    if (L) setLesson({ lessonId: L.id, lessonTitle: L.title, pathTitle: L.path.title, level: L.path.level });
    return () => setLesson(null);
  }, [L?.id, L?.title, L?.path.title, L?.path.level, setLesson]); // eslint-disable-line react-hooks/exhaustive-deps

  // Opening a lesson marks it "in progress"; write notes automatically the first time.
  const started = useRef<number | null>(null);
  const write = useMutation({
    mutationFn: (force: boolean) => api.writeNotes(id, force),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lesson", id] }),
  });
  useEffect(() => {
    if (!L || started.current === L.id) return;
    started.current = L.id;
    if (L.status === "todo") api.progress(L.id, "doing").then(() => qc.invalidateQueries({ queryKey: ["home"] }));
    if (!L.content_md && L.notes_status === "none") write.mutate(false);
  }, [L?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const [openedAt] = useState(Date.now());
  const complete = useMutation({
    mutationFn: (done: boolean) => api.progress(id, done ? "done" : "todo", done ? Math.round((Date.now() - openedAt) / 60000) : 0),
    onSuccess: (_d, done) => {
      qc.invalidateQueries({ queryKey: ["lesson", id] });
      qc.invalidateQueries({ queryKey: ["path"] });
      qc.invalidateQueries({ queryKey: ["home"] });
      if (done && L?.next) navigate(`/lessons/${L.next.id}`);
    },
  });

  if (lesson.isLoading) return <main className="p-8"><Thinking label="Loading lesson…" /></main>;
  if (lesson.isError) return <main className="p-8"><ErrorBox error={lesson.error} onRetry={() => lesson.refetch()} /></main>;
  const l = L!;
  const videos = l.resources.filter((r) => r.kind === "video");
  const papers = l.resources.filter((r) => r.kind !== "video");

  return (
    <div className="flex-1 flex flex-wrap items-stretch">
      {/* Outline */}
      <nav aria-label="Course outline" className="hidden lg:flex flex-[1_1_260px] max-w-[300px] min-w-0 flex-col gap-3.5 px-5 py-6">
        <div className="flex flex-col gap-1">
          <span className="text-[13px] text-muted">Learning path</span>
          <Link to={`/paths/${l.path.id}`} className="h-display text-lg hover:text-accent">{l.path.title}</Link>
          {path.data && <span className="text-xs text-muted">{path.data.pct}% · {path.data.done} of {path.data.lessons} lessons</span>}
        </div>
        <ol className="flex flex-col gap-1">
          {path.data?.module_list.map((m) => {
            const allDone = m.lessons.every((x) => x.status === "done");
            const isCur = m.id === l.module.id;
            return (
              <li key={m.id}>
                <details open={isCur} className="group">
                  <summary className="flex items-center gap-2.5 min-h-[44px] px-2.5 rounded-lg cursor-pointer list-none hover:bg-white">
                    <span className={`w-[22px] h-[22px] shrink-0 rounded-full flex items-center justify-center text-xs font-bold ${allDone ? "bg-ok text-white" : isCur ? "bg-accent text-white" : "border-2 border-[#C9CED8] text-muted"}`}>
                      {allDone ? <Icon.check size={12} /> : m.idx + 1}
                    </span>
                    <span className="flex-1 text-sm font-semibold">{m.title}</span>
                  </summary>
                  <ol className="ml-5 pl-3 mb-1.5 border-l-2 border-line flex flex-col gap-0.5">
                    {m.lessons.map((x) => (
                      <li key={x.id}>
                        <Link to={`/lessons/${x.id}`} aria-current={x.id === l.id ? "page" : undefined}
                          className={`flex items-center gap-2 min-h-[38px] px-2.5 rounded-lg text-sm ${x.id === l.id ? "bg-accent-soft text-accent-dark font-semibold" : "text-body hover:bg-white"}`}>
                          <span className="w-4 text-xs">{x.status === "done" ? "✓" : x.id === l.id ? "▶" : "○"}</span>
                          <span className="flex-1">{x.title}</span>
                          <span className="text-xs text-muted">{x.est_minutes}m</span>
                        </Link>
                      </li>
                    ))}
                  </ol>
                </details>
              </li>
            );
          })}
        </ol>
      </nav>

      {/* Lesson */}
      <main className="flex-[999_1_560px] min-w-0 bg-white border-x border-line px-5 sm:px-8 py-6 pb-28 flex flex-col gap-6">
        <p className="text-[13px] text-muted">
          <Link to={`/paths/${l.path.id}`} className="hover:text-accent">{l.path.title}</Link> · Module {l.module.idx + 1}: {l.module.title} · Lesson {l.idx + 1} of {l.module.lessons}
        </p>
        <h1 className="h-display text-3xl sm:text-[32px] leading-tight">{l.title}</h1>
        <div className="flex flex-wrap gap-2 text-[13px]">
          <span className="px-2.5 py-1 rounded-full bg-[#F1F3F6]">{l.est_minutes} min</span>
          <span className="px-2.5 py-1 rounded-full bg-[#F1F3F6] capitalize">{l.path.level}</span>
          {l.status === "done" && <span className="px-2.5 py-1 rounded-full bg-ok-soft text-ok-dark font-semibold">Completed</span>}
        </div>

        {l.objectives.length > 0 && (
          <section aria-labelledby="obj-h" className="p-4 rounded-xl bg-[#F6F8FF] border border-accent-line">
            <h2 id="obj-h" className="text-[15px] font-semibold mb-2">By the end you can</h2>
            <ul className="list-disc pl-5 text-body flex flex-col gap-0.5">{l.objectives.map((o) => <li key={o}>{o}</li>)}</ul>
          </section>
        )}

        {videos[0] && <VideoEmbed videoId={videos[0].external_id} title={videos[0].title} />}

        <LessonNotes l={l} onWrite={(force) => write.mutate(force)} writeError={write.error} />

        <section aria-labelledby="res-h" className="flex flex-col gap-3">
          <h2 id="res-h" className="text-lg font-semibold">Go deeper</h2>
          {videos.length > 0 && (
            <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}>
              {videos.map((v) => <VideoCard key={v.id} r={v} footer={<Detach lessonId={l.id} resourceId={v.id} />} />)}
            </div>
          )}
          {papers.map((p) => <PaperRow key={p.id} r={p} context={l.title} footer={<Detach lessonId={l.id} resourceId={p.id} />} />)}
          {l.resources.length === 0 && (
            <p className="text-sm text-muted">
              {l.module.resources_status === "searching" ? "The agents are searching for videos and papers for this module…"
                : <>No videos or papers yet. <Link className="text-accent font-semibold" to={`/paths/${l.path.id}#module-${l.module.id}`}>Find resources for this module</Link> or add some from <Link className="text-accent font-semibold" to={`/discover?q=${encodeURIComponent(l.title)}`}>Discover</Link>.</>}
            </p>
          )}
          <div className="grid gap-2.5 sm:grid-cols-3">
            {l.links.map((k) => <LinkCard key={k.url} {...k} hint={`Search ${k.label}`} />)}
          </div>
        </section>

        <MyNotes l={l} />

        <div className="flex flex-wrap gap-3 pt-4 border-t border-[#EEF0F3]">
          {l.status === "done" ? (
            <button type="button" className="btn-outline min-h-[48px]" onClick={() => complete.mutate(false)} disabled={complete.isPending}>Mark as not done</button>
          ) : (
            <button type="button" className="btn-ok min-h-[48px] px-6" onClick={() => complete.mutate(true)} disabled={complete.isPending}>
              <Icon.check /> Mark complete{l.next ? " & continue" : ""}
            </button>
          )}
          {l.prev && <Link to={`/lessons/${l.prev.id}`} className="btn-outline min-h-[48px]">← {l.prev.title}</Link>}
          {l.next && <Link to={`/lessons/${l.next.id}`} className="btn-outline min-h-[48px]">Next: {l.next.title} →</Link>}
        </div>
      </main>

      {/* Ask LLM, docked on wide screens */}
      <div className="hidden xl:flex flex-[1_1_360px] max-w-[420px] min-w-0">
        <AskLLMPanel key={l.id} className="sticky top-0 h-screen w-full border-l border-line"
          lesson={{ lessonId: l.id, lessonTitle: l.title, pathTitle: l.path.title, level: l.path.level }} />
      </div>
    </div>
  );
}

function VideoEmbed({ videoId, title }: { videoId: string; title: string }) {
  const [play, setPlay] = useState(false);
  return (
    <div className="relative aspect-video rounded-xl overflow-hidden bg-[#1E2433]">
      {play ? (
        <iframe className="w-full h-full" src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1`} title={title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
      ) : (
        <button type="button" onClick={() => setPlay(true)} className="w-full h-full group" aria-label={`Play video: ${title}`}>
          <img src={`https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`} alt="" className="w-full h-full object-cover opacity-80 group-hover:opacity-95" />
          <span className="absolute inset-0 flex items-center justify-center">
            <span className="w-[68px] h-[68px] rounded-full bg-black/60 text-white flex items-center justify-center"><Icon.play size={30} /></span>
          </span>
          <span className="absolute left-3.5 bottom-3 right-3.5 text-left text-white text-sm font-medium drop-shadow">{title}</span>
        </button>
      )}
    </div>
  );
}

function LessonNotes({ l, onWrite, writeError }: { l: Lesson; onWrite: (force: boolean) => void; writeError: unknown }) {
  const qc = useQueryClient();
  const [draft, setDraft] = useState<string | null>(null);
  const done = (d: Lesson) => { qc.setQueryData(["lesson", l.id], d); setDraft(null); };
  const save = useMutation({ mutationFn: () => api.editLessonNotes(l.id, draft ?? ""), onSuccess: done });
  const remove = useMutation({ mutationFn: () => api.deleteLessonNotes(l.id), onSuccess: done });
  if (draft !== null) {
    return (
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); if (draft.trim()) save.mutate(); }}>
        <label htmlFor="notes-md" className="label">Lesson notes (Markdown)</label>
        <textarea id="notes-md" className="input font-mono text-sm min-h-[420px]" value={draft} onChange={(e) => setDraft(e.target.value)} />
        {save.isError && <ErrorBox error={save.error} />}
        <div className="flex gap-2">
          <button type="submit" className="btn-primary btn-sm" disabled={save.isPending || !draft.trim()}>Save notes</button>
          <button type="button" className="btn-outline btn-sm" onClick={() => setDraft(null)}>Cancel</button>
        </div>
      </form>
    );
  }
  if (l.content_md) {
    return (
      <article className="flex flex-col gap-3">
        <Markdown>{l.content_md}</Markdown>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          <span>Check important facts against the sources below.</span>
          <button type="button" className="text-accent font-semibold hover:underline" onClick={() => setDraft(l.content_md ?? "")}>Edit</button>
          <button type="button" className="text-accent font-semibold hover:underline" disabled={l.notes_status === "writing"} onClick={() => onWrite(true)}>
            {l.notes_status === "writing" ? "Rewriting…" : "Rewrite"}
          </button>
          <button type="button" className="text-accent font-semibold hover:underline" disabled={remove.isPending}
            onClick={() => { if (confirm("Delete these lesson notes?")) remove.mutate(); }}>Delete</button>
        </div>
        {remove.isError && <ErrorBox error={remove.error} />}
      </article>
    );
  }
  if (l.notes_status === "deleted") {
    return (
      <div className="card p-6 flex flex-wrap items-center gap-3">
        <p className="text-body flex-1 min-w-[200px]">No notes for this lesson.</p>
        <button type="button" className="btn-outline btn-sm" onClick={() => setDraft("")}>Write my own</button>
        <button type="button" className="btn-primary btn-sm" onClick={() => onWrite(true)}>Have the agent write them</button>
      </div>
    );
  }
  if (l.notes_status === "writing" || l.notes_status === "none") {
    return <div className="card p-6 flex flex-col gap-2"><Thinking label="The Lesson Writer agent is writing these notes (usually under a minute)…" /></div>;
  }
  return (
    <div className="card p-6 flex flex-col gap-3">
      <p className="text-body">The lesson notes couldn't be written.</p>
      {writeError ? <ErrorBox error={writeError} /> : null}
      <button type="button" className="btn-primary self-start" onClick={() => onWrite(true)}>Try again</button>
    </div>
  );
}

function MyNotes({ l }: { l: Lesson }) {
  const [text, setText] = useState(l.user_notes);
  const [savedText, setSavedText] = useState(l.user_notes);
  useEffect(() => { setText(l.user_notes); setSavedText(l.user_notes); }, [l.id, l.user_notes]);
  const save = useMutation({ mutationFn: () => api.saveUserNotes(l.id, text), onSuccess: () => setSavedText(text) });
  return (
    <section aria-labelledby="my-notes-h" className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <h2 id="my-notes-h" className="text-lg font-semibold flex-1">My notes</h2>
        <span className="text-xs text-muted" aria-live="polite">{save.isPending ? "Saving…" : text === savedText ? "Saved" : "Unsaved changes"}</span>
      </div>
      <label htmlFor="my-notes" className="sr-only">My notes for this lesson</label>
      <textarea id="my-notes" rows={5} value={text} onChange={(e) => setText(e.target.value)}
        onBlur={() => text !== savedText && save.mutate()} className="input font-mono text-sm resize-y"
        placeholder="Your own notes. Answers from Ask LLM can be saved here too." />
    </section>
  );
}

function Detach({ lessonId, resourceId }: { lessonId: number; resourceId: number }) {
  const qc = useQueryClient();
  const m = useMutation({
    mutationFn: () => api.detach(lessonId, resourceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lesson", lessonId] }),
  });
  return <button type="button" className="text-[13px] text-muted hover:text-yt-fg ml-auto" onClick={() => m.mutate()}>Remove from lesson</button>;
}
