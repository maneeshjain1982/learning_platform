import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, type Resource, type Step } from "../api";

// ---------------------------------------------------------------- icons (stroke SVG)

type IconProps = { size?: number; className?: string };
const svg = (d: ReactNode) => ({ size = 18, className = "" }: IconProps) => (
  <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className}>{d}</svg>
);
export const Icon = {
  search: svg(<><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></>),
  play: svg(<path d="M8 5l11 7-11 7z" />),
  chat: svg(<path d="M4 5h16v11H9l-5 4z" />),
  bookmark: svg(<path d="M6 3h12v18l-6-4-6 4z" />),
  check: svg(<path d="M5 12l5 5 9-10" />),
  external: svg(<><path d="M14 4h6v6" /><path d="M20 4l-9 9" /><path d="M18 14v6H4V6h6" /></>),
  plus: svg(<path d="M12 5v14M5 12h14" />),
  close: svg(<path d="M6 6l12 12M18 6L6 18" />),
  send: svg(<path d="M5 12h14M13 6l6 6-6 6" />),
  refresh: svg(<><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 5v6h-6" /></>),
  paper: svg(<><path d="M7 3h7l5 5v13H7z" /><path d="M14 3v5h5" /><path d="M10 13h6M10 17h6" /></>),
  chevron: svg(<path d="M9 6l6 6-6 6" />),
  trash: svg(<><path d="M4 7h16" /><path d="M10 11v6M14 11v6" /><path d="M6 7l1 13h10l1-13" /><path d="M9 7V4h6v3" /></>),
  menu: svg(<path d="M4 6h16M4 12h16M4 18h16" />),
  edit: svg(<><path d="M4 20h4L19 9l-4-4L4 16z" /><path d="M13.5 6.5l4 4" /></>),
  up: svg(<path d="M6 15l6-6 6 6" />),
  down: svg(<path d="M6 9l6 6 6-6" />),
  link: svg(<><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" /><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" /></>),
};

// ---------------------------------------------------------------- source badge

const SOURCE: Record<string, { label: string; cls: string }> = {
  youtube: { label: "YouTube", cls: "bg-yt-bg text-yt-fg" },
  coursera: { label: "Coursera", cls: "bg-cs-bg text-cs-fg" },
  udemy: { label: "Udemy", cls: "bg-ud-bg text-ud-fg" },
  arxiv: { label: "arXiv", cls: "bg-pp-bg text-pp-fg" },
  semantic_scholar: { label: "Semantic Scholar", cls: "bg-pp-bg text-pp-fg" },
  linkedin: { label: "LinkedIn Learning", cls: "bg-cs-bg text-cs-fg" },
  edx: { label: "edX", cls: "bg-cs-bg text-cs-fg" },
  deeplearning_ai: { label: "DeepLearning.AI", cls: "bg-cs-bg text-cs-fg" },
  udacity: { label: "Udacity", cls: "bg-cs-bg text-cs-fg" },
  github: { label: "GitHub", cls: "bg-[#EEF0F3] text-ink" },
  claude_academy: { label: "Claude Academy", cls: "bg-pp-bg text-pp-fg" },
  web: { label: "Web", cls: "bg-[#EEF0F3] text-body" },
};

export function SourceBadge({ source, extra }: { source: string; extra?: string }) {
  const s = SOURCE[source] ?? { label: source, cls: "bg-[#EEF0F3] text-body" };
  return <span className={`chip ${s.cls}`}>{s.label}{extra ? ` · ${extra}` : ""}</span>;
}

// ---------------------------------------------------------------- save button

export function SaveButton({ r }: { r: Resource }) {
  const qc = useQueryClient();
  const [saved, setSaved] = useState(r.saved);
  useEffect(() => setSaved(r.saved), [r.saved]);
  const m = useMutation({
    mutationFn: () => (saved ? api.unsave(r.id) : api.save(r.id)),
    onSuccess: (d) => { setSaved(d.saved); qc.invalidateQueries({ queryKey: ["saved"] }); },
  });
  return (
    <button type="button" onClick={() => m.mutate()} aria-pressed={saved}
      aria-label={saved ? `Remove "${r.title}" from saved` : `Save "${r.title}"`}
      className={`w-11 h-11 shrink-0 rounded-[10px] border flex items-center justify-center ${saved ? "bg-accent-soft border-accent text-accent-dark" : "bg-white border-line2 text-body hover:bg-ground"}`}>
      <Icon.bookmark />
    </button>
  );
}

// ---------------------------------------------------------------- video card

export function VideoCard({ r, footer }: { r: Resource; footer?: ReactNode }) {
  return (
    <article className="card overflow-hidden flex flex-col">
      <a href={r.url} target="_blank" rel="noreferrer" className="relative block aspect-video bg-[#1E2433] group">
        {r.thumbnail && <img src={r.thumbnail} alt="" loading="lazy" className="w-full h-full object-cover opacity-90 group-hover:opacity-100" />}
        <span className="absolute inset-0 flex items-center justify-center">
          <span className="w-14 h-14 rounded-full bg-black/55 text-white flex items-center justify-center"><Icon.play size={26} /></span>
        </span>
        <span className="sr-only">Watch {r.title} on YouTube (opens in new tab)</span>
      </a>
      <div className="p-4 flex flex-col gap-2 flex-1">
        <div className="flex items-center gap-2"><SourceBadge source={r.source} /></div>
        <h3 className="text-base font-semibold leading-snug">
          <a href={r.url} target="_blank" rel="noreferrer" className="hover:text-accent">{r.title}</a>
        </h3>
        {r.author && <p className="text-[13px] text-muted">{r.author}</p>}
        {r.why && <p className="mt-auto pt-2 border-t border-[#EEF0F3] text-[13px] text-body"><strong className="text-ink">Why:</strong> {r.why}</p>}
        <div className="flex items-center gap-2 pt-1">
          <SaveButton r={r} />
          {footer}
        </div>
      </div>
    </article>
  );
}

// ---------------------------------------------------------------- paper row

export function PaperRow({ r, footer }: { r: Resource; footer?: ReactNode }) {
  const meta = [r.author, r.year, r.citations ? `${r.citations.toLocaleString()} citations` : null].filter(Boolean).join(" · ");
  return (
    <article className="card p-4 flex gap-3">
      <div className="flex-1 min-w-0 flex flex-col gap-1.5">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceBadge source={r.source} extra={r.year ? String(r.year) : undefined} />
          {r.pdf && <a href={r.pdf} target="_blank" rel="noreferrer" className="text-[13px] font-semibold text-accent hover:underline">PDF ↗</a>}
        </div>
        <h3 className="font-semibold leading-snug">
          <a href={r.url} target="_blank" rel="noreferrer" className="hover:text-accent">{r.title}</a>
        </h3>
        {meta && <p className="text-[13px] text-muted">{meta}</p>}
        {r.why && <p className="text-[13px] text-body"><strong className="text-ink">Why:</strong> {r.why}</p>}
        {footer && <div className="flex items-center gap-2 pt-1 flex-wrap">{footer}</div>}
      </div>
      <SaveButton r={r} />
    </article>
  );
}

// ---------------------------------------------------------------- search link

export function LinkCard({ source, label, url, query, hint }: { source: string; label: string; url: string; query?: string; hint?: string }) {
  return (
    <a href={url} target="_blank" rel="noreferrer"
      className="card flex items-center gap-3 px-4 py-3.5 hover:border-accent group">
      <SourceBadge source={source} />
      <span className="flex-1 min-w-0">
        <span className="block font-semibold truncate">{query ? `“${query}”` : `Search ${label}`}</span>
        {hint && <span className="block text-[13px] text-muted">{hint}</span>}
      </span>
      <span className="text-body group-hover:text-accent"><Icon.external /></span>
      <span className="sr-only">(opens {label} in a new tab)</span>
    </a>
  );
}

// ---------------------------------------------------------------- agent steps

const STEP_STYLE: Record<string, { dot: string; pill: string; label: string }> = {
  done: { dot: "bg-ok text-white", pill: "bg-ok-soft text-ok-dark", label: "Done" },
  running: { dot: "bg-accent text-white", pill: "bg-accent-soft text-accent-dark", label: "Running" },
  queued: { dot: "bg-white text-muted border-2 border-[#C9CED8]", pill: "bg-[#F1F3F6] text-muted", label: "Queued" },
  failed: { dot: "bg-[#B42318] text-white", pill: "bg-yt-bg text-yt-fg", label: "Failed" },
  skipped: { dot: "bg-white text-muted border-2 border-[#C9CED8]", pill: "bg-[#F1F3F6] text-muted", label: "Skipped" },
};

export function AgentSteps({ steps }: { steps: Step[] }) {
  return (
    <ol className="flex flex-col">
      {steps.map((s, i) => {
        const st = STEP_STYLE[s.status] ?? STEP_STYLE.queued;
        return (
          <li key={s.agent} className="flex gap-3.5">
            <div className="flex flex-col items-center">
              <span className={`w-7 h-7 rounded-full flex items-center justify-center text-[13px] font-bold ${st.dot}`}>
                {s.status === "done" ? <Icon.check size={14} /> : s.status === "running" ? "…" : s.status === "failed" ? "!" : i + 1}
              </span>
              {i < steps.length - 1 && <span className="flex-1 w-0.5 min-h-4 bg-line" />}
            </div>
            <div className="flex-1 min-w-0 flex flex-col gap-1.5 pb-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{s.agent}</span>
                <span className={`chip ${st.pill}`}>{st.label}</span>
              </div>
              {s.summary && <p className="text-[13px] text-muted">{s.summary}</p>}
              {s.chips.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {s.chips.map((c) => <span key={c} className="px-2 py-0.5 rounded-md bg-[#F1F3F6] text-xs text-body">{c}</span>)}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// ---------------------------------------------------------------- misc

export function Markdown({ children, className = "" }: { children: string; className?: string }) {
  return (
    <div className={`prose prose-slate max-w-none prose-headings:font-display prose-headings:tracking-tight prose-a:text-accent prose-pre:rounded-[10px] prose-pre:text-[13px] ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}
        components={{ a: ({ node: _n, ...p }) => <a {...p} target="_blank" rel="noreferrer" /> }}>
        {children}
      </ReactMarkdown>
    </div>
  );
}

export function Thinking({ label, since }: { label: string; since?: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const secs = since ? Math.max(0, Math.round((now - since) / 1000)) : null;
  return (
    <div role="status" className="flex items-center gap-2.5 text-sm text-muted">
      <span aria-hidden="true" className="flex gap-1"><span className="dot" /><span className="dot" /><span className="dot" /></span>
      {label}{secs !== null ? ` ${secs} s` : ""}
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className="rounded-xl border border-[#F5C2BE] bg-yt-bg/60 px-4 py-3 text-sm text-yt-fg flex flex-wrap items-center gap-3">
      <span className="flex-1">{friendly(msg)}</span>
      {onRetry && <button type="button" className="btn-outline btn-sm" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function friendly(msg: string): string {
  if (/usage limit|rate limit/i.test(msg)) return "Your Claude plan's usage limit was reached. Try again after it resets.";
  if (/not logged in|login|invalid api key/i.test(msg)) return "Claude isn't signed in. Run `claude` in a terminal and log in, then try again.";
  if (/did not finish within/i.test(msg)) return "The model took too long to answer. Try again.";
  if (/Failed to fetch|NetworkError/i.test(msg)) return "Can't reach the Study Companion server. Is it running?";
  return msg;
}

export function ProgressBar({ pct, label }: { pct: number; label: string }) {
  return (
    <div role="img" aria-label={label} className="h-1.5 rounded-full bg-line overflow-hidden">
      <div className="h-full bg-accent transition-all" style={{ width: `${Math.min(100, pct)}%` }} />
    </div>
  );
}

export function Ring({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max ? Math.min(100, (100 * value) / max) : 0;
  return (
    <svg role="img" aria-label={label} width="88" height="88" viewBox="0 0 36 36">
      <circle cx="18" cy="18" r="15.9" fill="none" stroke="#E3E6EC" strokeWidth="3.2" />
      <circle cx="18" cy="18" r="15.9" fill="none" stroke="#2453D6" strokeWidth="3.2" strokeLinecap="round"
        strokeDasharray={`${pct} 100`} transform="rotate(-90 18 18)" />
    </svg>
  );
}

export const storage = {
  get(key: string): string | null { try { return localStorage.getItem(key); } catch { return null; } },
  set(key: string, v: string | null) {
    try { if (v === null) localStorage.removeItem(key); else localStorage.setItem(key, v); } catch { /* ignore */ }
  },
};
