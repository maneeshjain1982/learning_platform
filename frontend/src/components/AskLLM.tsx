import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api, type ChatMsg } from "../api";
import { ErrorBox, Icon, Markdown, Thinking, friendly, storage } from "./ui";

export interface LessonCtx { lessonId: number; lessonTitle: string; pathTitle: string; level: string }

interface AskState {
  open: boolean;
  setOpen: (v: boolean) => void;
  lesson: LessonCtx | null;
  setLesson: (l: LessonCtx | null) => void;
  ask: (question: string) => void;       // open the drawer with a question ready to send
  pending: string | null;
  clearPending: () => void;
}

const AskContext = createContext<AskState | null>(null);

export function AskProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [lesson, setLesson] = useState<LessonCtx | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  return (
    <AskContext.Provider value={{
      open, setOpen, lesson, setLesson, pending, clearPending: () => setPending(null),
      ask: (q) => { setPending(q); setOpen(true); },
    }}>{children}</AskContext.Provider>
  );
}

export function useAsk() {
  const ctx = useContext(AskContext);
  if (!ctx) throw new Error("useAsk outside AskProvider");
  return ctx;
}

const QUICK = ["Explain this simpler", "Give me a concrete example", "Quiz me on this lesson"];

export function AskLLMPanel({ lesson, onClose, className = "" }: { lesson: LessonCtx | null; onClose?: () => void; className?: string }) {
  const qc = useQueryClient();
  const { pending, clearPending } = useAsk();
  const key = lesson ? `chat:lesson:${lesson.lessonId}` : "chat:general";
  const [sessionId, setSessionId] = useState<number | null>(() => Number(storage.get(key)) || null);
  const [ctx, setCtx] = useState({ lesson: true, level: true, path: true });
  const [text, setText] = useState("");
  const [local, setLocal] = useState<ChatMsg[]>([]);
  const [sentAt, setSentAt] = useState<number | null>(null);
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set());
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { setSessionId(Number(storage.get(key)) || null); setLocal([]); }, [key]);

  const session = useQuery({
    queryKey: ["chat", sessionId],
    queryFn: () => api.chatSession(sessionId!),
    enabled: !!sessionId,
    retry: false,
  });
  useEffect(() => { if (session.isError) { storage.set(key, null); setSessionId(null); } }, [session.isError, key]);

  const send = useMutation({
    mutationFn: (message: string) => api.chat({
      message, session_id: sessionId, lesson_id: lesson?.lessonId ?? null,
      context: lesson ? ctx : undefined,
    }),
    onMutate: (message) => {
      setSentAt(Date.now());
      setLocal((l) => [...l, { id: -Date.now(), role: "user", content: message, meta: {}, created_at: "" }]);
    },
    onSuccess: (d) => {
      storage.set(key, String(d.session_id));
      setSessionId(d.session_id);
      setLocal([]);
      qc.setQueryData(["chat", d.session_id], (old: { messages: ChatMsg[] } | undefined) => ({
        id: d.session_id, lesson_id: lesson?.lessonId ?? null,
        messages: [...(old?.messages ?? []), d.user, d.reply],
      }));
    },
    onSettled: () => setSentAt(null),
  });

  const saveNote = useMutation({
    mutationFn: (id: number) => api.saveToNotes(id),
    onSuccess: (_d, id) => {
      setSavedIds((s) => new Set(s).add(id));
      if (lesson) qc.invalidateQueries({ queryKey: ["lesson", lesson.lessonId] });
    },
  });

  const messages = [...(sessionId ? session.data?.messages ?? [] : []), ...local];

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, send.isPending]);

  useEffect(() => {
    if (pending) { setText(pending); clearPending(); inputRef.current?.focus(); }
  }, [pending, clearPending]);

  const submit = (msg: string) => {
    const m = msg.trim();
    if (!m || send.isPending) return;
    setText("");
    send.mutate(m);
  };

  const newChat = () => { storage.set(key, null); setSessionId(null); setLocal([]); send.reset(); };

  const chips: { k: keyof typeof ctx; label: string }[] = lesson ? [
    { k: "lesson", label: `Lesson: ${lesson.lessonTitle}` },
    { k: "level", label: `Level: ${lesson.level}` },
    { k: "path", label: `Path: ${lesson.pathTitle}` },
  ] : [];

  return (
    <section aria-labelledby="ask-h" className={`flex flex-col bg-white min-h-0 ${className}`}>
      <div className="flex items-center gap-2.5 px-4 py-3.5 border-b border-line">
        <span className="text-accent"><Icon.chat size={20} /></span>
        <h2 id="ask-h" className="flex-1 text-base font-semibold">Ask LLM</h2>
        <button type="button" onClick={newChat} aria-label="Start a new chat" title="New chat"
          className="w-10 h-10 rounded-lg border border-line flex items-center justify-center text-body hover:bg-ground"><Icon.plus size={16} /></button>
        {onClose && (
          <button type="button" onClick={onClose} aria-label="Close Ask LLM"
            className="w-10 h-10 rounded-lg border border-line flex items-center justify-center text-body hover:bg-ground"><Icon.close size={16} /></button>
        )}
      </div>

      {lesson && (
        <div className="px-4 py-3 flex flex-wrap gap-1.5 border-b border-[#EEF0F3]">
          <span className="w-full text-xs text-muted">Context the tutor can see (click to toggle)</span>
          {chips.map(({ k, label }) => (
            <button key={k} type="button" aria-pressed={ctx[k]} onClick={() => setCtx((c) => ({ ...c, [k]: !c[k] }))}
              className={`chip max-w-full truncate px-2.5 py-1 ${ctx[k] ? "bg-accent-soft text-accent-dark" : "bg-[#F1F3F6] text-muted line-through"}`}>
              {label}
            </button>
          ))}
        </div>
      )}

      <div ref={logRef} role="log" aria-label="Conversation" className="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-4">
        {messages.length === 0 && !send.isPending && (
          <div className="text-sm text-muted flex flex-col gap-2">
            <p className="text-ink font-semibold">Ask anything while you study.</p>
            <p>{lesson ? "Answers use this lesson's notes and objectives, unless you turn that off above." : "Open a lesson to give the tutor that lesson as context."}</p>
            <p className="text-xs">Answers arrive in one piece after a few seconds (the bridge doesn't stream).</p>
          </div>
        )}
        {messages.map((m) => m.role === "user" ? (
          <div key={m.id} className="self-end max-w-[88%] px-3.5 py-2.5 rounded-[14px_14px_4px_14px] bg-ink text-white text-sm whitespace-pre-wrap">{m.content}</div>
        ) : m.role === "error" ? (
          <div key={m.id} role="alert" className="text-sm text-yt-fg bg-yt-bg/60 rounded-xl px-3 py-2">{friendly(m.content)}</div>
        ) : (
          <div key={m.id} className="max-w-full flex flex-col gap-2">
            <Markdown className="prose-sm">{m.content}</Markdown>
            <p className="text-xs text-muted">
              {[m.meta.provider && m.meta.provider[0].toUpperCase() + m.meta.provider.slice(1), m.meta.model,
                m.meta.duration_ms ? `${Math.round(m.meta.duration_ms / 1000)} s` : null].filter(Boolean).join(" · ")}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {lesson && (
                <button type="button" className="btn-outline btn-sm text-[13px]" disabled={savedIds.has(m.id) || saveNote.isPending}
                  onClick={() => saveNote.mutate(m.id)}>{savedIds.has(m.id) ? "Saved to notes" : "Save to notes"}</button>
              )}
              <button type="button" className="btn-outline btn-sm text-[13px]"
                onClick={() => navigator.clipboard?.writeText(m.content)}>Copy</button>
            </div>
          </div>
        ))}
        {send.isPending && <Thinking label="Thinking…" since={sentAt ?? undefined} />}
        {send.isError && <ErrorBox error={send.error} />}
      </div>

      <div className="p-4 border-t border-line flex flex-col gap-2.5">
        <div className="flex flex-wrap gap-1.5">
          {QUICK.slice(lesson ? 0 : 1).map((q) => (
            <button key={q} type="button" disabled={send.isPending} onClick={() => submit(q)}
              className="min-h-[36px] px-3 rounded-full border border-line2 bg-ground text-[13px] hover:bg-white disabled:opacity-50">{q}</button>
          ))}
        </div>
        <form className="flex items-end gap-2 pl-3.5 pr-2 py-2 border border-[#C9CED8] rounded-xl focus-within:border-accent"
          onSubmit={(e) => { e.preventDefault(); submit(text); }}>
          <label htmlFor="ask-input" className="sr-only">Ask a question</label>
          <textarea id="ask-input" ref={inputRef} rows={2} value={text} onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(text); } }}
            placeholder={lesson ? "Ask anything about this lesson…" : "Ask anything…"}
            className="flex-1 min-w-0 resize-none text-sm outline-none bg-transparent" />
          <button type="submit" aria-label="Send question" disabled={!text.trim() || send.isPending}
            className="w-11 h-11 rounded-[10px] bg-accent text-white flex items-center justify-center disabled:opacity-40"><Icon.send /></button>
        </form>
      </div>
    </section>
  );
}

export function AskDrawer() {
  const { open, setOpen, lesson } = useAsk();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Ask LLM">
      <button type="button" aria-label="Close" className="absolute inset-0 bg-ink/30" onClick={() => setOpen(false)} />
      <AskLLMPanel lesson={lesson} onClose={() => setOpen(false)} className="relative w-full max-w-[440px] h-full shadow-2xl" />
    </div>
  );
}

export function AskFab({ className = "" }: { className?: string }) {
  const { setOpen } = useAsk();
  return (
    <button type="button" onClick={() => setOpen(true)}
      className={`fixed right-6 bottom-6 z-40 inline-flex items-center gap-2.5 min-h-[52px] px-5 rounded-full bg-ink text-white font-semibold shadow-[0_8px_24px_rgba(20,23,31,0.22)] hover:bg-black ${className}`}>
      <Icon.chat size={20} /> Ask LLM
    </button>
  );
}
