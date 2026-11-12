import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { AgentSteps, ErrorBox, Thinking } from "../components/ui";

const GOALS = [
  ["understand", "Understand the concepts"], ["build", "Build a project"],
  ["interview", "Prepare for interviews"], ["research", "Research / read papers"],
] as const;
const LEVELS = [
  ["beginner", "Beginner", "New to this area"], ["intermediate", "Intermediate", "Know the basics, want depth"],
  ["advanced", "Advanced", "Want papers and edge cases"],
] as const;
const FORMATS = ["Video lectures", "Full courses", "Research papers", "Hands-on practice"];
const SOURCES = [
  ["youtube", "YouTube", "Videos, links checked"], ["coursera", "Coursera", "Search links"],
  ["udemy", "Udemy", "Search links"], ["arxiv", "arXiv", "Pre-print papers"],
  ["semantic_scholar", "Semantic Scholar", "Papers + citations"],
] as const;
const PLACEHOLDER_STEPS = ["Topic Identifier", "Curriculum Planner", "Video Search", "Paper Search", "Curator", "Home Composer"]
  .map((agent) => ({ agent, status: "queued", summary: "", chips: [] as string[] }));
const STEP_HINTS: Record<string, string> = {
  "Topic Identifier": "Reads your goal and finds the core topics, prerequisites and search keywords.",
  "Curriculum Planner": "Orders modules and lessons to fit your time.",
  "Video Search": "Finds YouTube videos per lesson and checks every link is real.",
  "Paper Search": "Finds foundational papers (checked on arXiv) and recent ones.",
  "Curator": "Matches papers to lessons and explains each pick.",
  "Home Composer": "Builds your personalized home page.",
};

export default function Setup() {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const runId = Number(params.get("run")) || null;
  const [text, setText] = useState("");
  const [goal, setGoal] = useState("build");
  const [level, setLevel] = useState("intermediate");
  const [hours, setHours] = useState(5);
  const [weeks, setWeeks] = useState(6);
  const [formats, setFormats] = useState<string[]>(["Video lectures", "Full courses", "Research papers", "Hands-on practice"]);
  const [sources, setSources] = useState<string[]>(SOURCES.map((s) => s[0]));

  const create = useMutation({
    mutationFn: () => api.createRequirement({ raw_text: text, goal, level, hours_per_week: hours, weeks, formats, sources }),
    onSuccess: (d) => setParams({ run: String(d.run_id) }),
  });

  const run = useQuery({
    queryKey: ["run", runId], queryFn: () => api.run(runId!), enabled: !!runId,
    refetchInterval: (q) => (q.state.data?.status === "running" || !q.state.data ? 2000 : false),
  });
  useEffect(() => {
    if (run.data?.status === "done") { qc.invalidateQueries({ queryKey: ["home"] }); qc.invalidateQueries({ queryKey: ["paths"] }); }
  }, [run.data?.status, qc]);

  const toggle = (list: string[], v: string, set: (x: string[]) => void) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const steps = (run.data?.steps ?? PLACEHOLDER_STEPS).map((s) => ({ ...s, summary: s.summary || STEP_HINTS[s.agent] || "" }));
  const busy = create.isPending || run.data?.status === "running";

  return (
    <main className="max-w-[1280px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-wrap gap-7 items-start">
      <form className="card flex-[999_1_600px] min-w-0 p-6 sm:p-8 flex flex-col gap-6"
        onSubmit={(e) => { e.preventDefault(); if (!busy) create.mutate(); }}>
        <div className="flex flex-col gap-2">
          <h1 className="h-display text-3xl">Set up a learning goal</h1>
          <p className="text-muted">Describe what you want to learn. Your companion agents turn it into a step-by-step path and a personalized home page.</p>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="topic" className="label">What do you want to learn?</label>
          <textarea id="topic" rows={4} required minLength={10} value={text} onChange={(e) => setText(e.target.value)} className="input resize-y"
            placeholder="e.g. I want to learn RAG well enough to build a document Q&A app in Python — chunking, embeddings, vector search and evaluation." />
          <p className="text-[13px] text-muted">Tip: say what you already know and what you want to be able to do at the end.</p>
        </div>

        <fieldset className="flex flex-col gap-2.5">
          <legend className="label mb-2.5">Why are you learning this?</legend>
          <div className="flex flex-wrap gap-2">
            {GOALS.map(([v, l]) => (
              <button key={v} type="button" aria-pressed={goal === v} onClick={() => setGoal(v)}
                className={`pill font-medium ${goal === v ? "bg-ink text-white border-ink" : "bg-white text-body border-line2 hover:bg-ground"}`}>{l}</button>
            ))}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2.5">
          <legend className="label mb-2.5">Your current level</legend>
          <div className="grid gap-2.5 grid-cols-1 sm:grid-cols-3">
            {LEVELS.map(([v, l, d]) => (
              <button key={v} type="button" aria-pressed={level === v} onClick={() => setLevel(v)}
                className={`flex flex-col items-start gap-1 p-3.5 rounded-xl text-left ${level === v ? "bg-accent-soft border-2 border-accent" : "bg-white border border-line2 hover:bg-ground"}`}>
                <span className="font-semibold">{l}</span><span className="text-[13px] text-muted">{d}</span>
              </button>
            ))}
          </div>
        </fieldset>

        <div className="flex flex-wrap gap-4">
          <div className="flex-[1_1_200px] flex flex-col gap-2">
            <label htmlFor="hours" className="label">Hours per week</label>
            <select id="hours" value={hours} onChange={(e) => setHours(Number(e.target.value))} className="input min-h-[44px]">
              {[2, 3, 5, 8, 10, 15, 20].map((h) => <option key={h} value={h}>{h} hours</option>)}
            </select>
          </div>
          <div className="flex-[1_1_200px] flex flex-col gap-2">
            <label htmlFor="weeks" className="label">Finish in</label>
            <select id="weeks" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))} className="input min-h-[44px]">
              {[2, 4, 6, 8, 12].map((w) => <option key={w} value={w}>{w} weeks</option>)}
            </select>
          </div>
        </div>

        <fieldset className="flex flex-col gap-2.5">
          <legend className="label mb-2.5">Preferred formats</legend>
          <div className="flex flex-wrap gap-2.5">
            {FORMATS.map((f) => (
              <label key={f} className="inline-flex items-center gap-2 min-h-[44px] px-3.5 border border-line2 rounded-[10px] cursor-pointer">
                <input type="checkbox" checked={formats.includes(f)} onChange={() => toggle(formats, f, setFormats)} className="w-[18px] h-[18px] accent-accent" />{f}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2.5">
          <legend className="label mb-2.5">Search these sources</legend>
          <div className="grid gap-2.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))" }}>
            {SOURCES.map(([v, l, n]) => (
              <label key={v} className="flex items-center gap-2.5 min-h-[52px] px-3.5 border border-line2 rounded-[10px] cursor-pointer">
                <input type="checkbox" checked={sources.includes(v)} onChange={() => toggle(sources, v, setSources)} className="w-[18px] h-[18px] accent-accent" />
                <span className="flex flex-col leading-tight"><span className="font-semibold">{l}</span><span className="text-xs text-muted">{n}</span></span>
              </label>
            ))}
          </div>
        </fieldset>

        {create.isError && <ErrorBox error={create.error} />}
        <div className="flex flex-wrap gap-3 pt-2 border-t border-[#EEF0F3]">
          <button type="submit" className="btn-primary min-h-[48px] px-6" disabled={busy || text.trim().length < 10}>
            {busy ? "Building your path…" : "Build my learning path"}
          </button>
        </div>
      </form>

      <aside aria-labelledby="agents-h" className="card flex-[1_1_360px] min-w-0 p-6 flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 id="agents-h" className="h-display text-xl">Companion agents</h2>
          <p className="text-muted text-sm">
            {runId ? "Live progress. This takes a few minutes and runs on Claude through LLM Bridge." : "What happens when you press “Build my learning path”."}
          </p>
        </div>
        {run.isLoading && <Thinking label="Starting…" />}
        <div aria-live="polite"><AgentSteps steps={steps} /></div>
        {run.data?.status === "done" && run.data.path_id && (
          <div className="flex flex-wrap gap-2">
            <Link to={`/paths/${run.data.path_id}`} className="btn-primary">Open my new path</Link>
            <Link to="/" className="btn-outline">Go to home</Link>
          </div>
        )}
        {run.data?.status === "failed" && (
          <>
            <ErrorBox error={run.data.error ?? "The agents stopped."} />
            {run.data.path_id && <Link to={`/paths/${run.data.path_id}`} className="btn-outline self-start">Open what was built</Link>}
          </>
        )}
        <p className="rounded-[10px] bg-ground px-3.5 py-3 text-[13px] text-body">You can leave this page. Your path appears under My paths when the agents finish.</p>
      </aside>
    </main>
  );
}
