import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api, type CareerProfile } from "../api";
import { Dialog } from "../components/EditItem";
import { Field } from "../components/Sources";
import { ErrorBox, Icon, Thinking, ago } from "../components/ui";

const LEVELS = ["junior", "mid", "senior", "staff", "principal", "lead", "manager", "director"];
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export function useProfile() {
  return useQuery({ queryKey: ["career-profile"], queryFn: api.careerProfile });
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1] ?? "");
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

/** Your CV as a saved profile: used by Job search (matching) and Interview prep (gaps). */
export function ProfileCard() {
  const qc = useQueryClient();
  const q = useProfile();
  const fileRef = useRef<HTMLInputElement>(null);
  const [paste, setPaste] = useState(false);
  const [text, setText] = useState("");
  const [edit, setEdit] = useState(false);
  const save = (d: { profile: CareerProfile | null }) => qc.setQueryData(["career-profile"], d);
  const upload = useMutation({
    mutationFn: async (b: { file?: File; text?: string }) =>
      b.file ? api.uploadCV({ filename: b.file.name, content_b64: await toBase64(b.file) }) : api.uploadCV({ text: b.text }),
    onSuccess: (d) => { save(d); setPaste(false); setText(""); },
  });
  const remove = useMutation({ mutationFn: api.deleteProfile, onSuccess: save });
  const p = q.data?.profile;

  const pick = (
    <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden"
      onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate({ file: f }); e.target.value = ""; }} />
  );
  const privacy = <p className="text-xs text-muted">Read on this computer. Name, email, phone, address and profile links are removed before the AI sees it; the file isn't kept.</p>;

  if (q.isLoading) return null;
  if (upload.isPending) return <div className="card p-5"><Thinking label="Reading your CV…" /></div>;

  if (!p) return (
    <section aria-labelledby="cv-h" className="card p-5 flex flex-col gap-3 border-dashed">
      {pick}
      <div className="flex flex-wrap items-center gap-3">
        <span className="w-10 h-10 rounded-xl bg-accent-soft text-accent grid place-items-center"><Icon.doc size={20} /></span>
        <div className="flex-1 min-w-[200px]">
          <h2 id="cv-h" className="font-semibold">Add your CV to find jobs that fit you</h2>
          <p className="text-sm text-muted">PDF, Word or text. Each job then gets a match score, why it fits and what's missing.</p>
        </div>
        <button type="button" className="btn-primary btn-sm" onClick={() => fileRef.current?.click()}><Icon.plus size={15} /> Upload CV</button>
        <button type="button" className="btn-outline btn-sm" aria-expanded={paste} onClick={() => setPaste(!paste)}>Paste text</button>
      </div>
      {paste && (
        <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); upload.mutate({ text }); }}>
          <label htmlFor="cv-t" className="sr-only">CV text</label>
          <textarea id="cv-t" className="input min-h-[160px]" value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste your CV here" />
          <div><button type="submit" className="btn-primary btn-sm" disabled={text.trim().length < 80}>Read CV</button></div>
        </form>
      )}
      {privacy}
      {upload.isError && <ErrorBox error={upload.error} />}
    </section>
  );

  return (
    <section aria-labelledby="cv-h" className="card p-5 flex flex-col gap-3">
      {pick}
      <div className="flex flex-wrap items-start gap-3">
        <span className="w-10 h-10 rounded-xl bg-ok-soft text-ok-dark grid place-items-center shrink-0"><Icon.check size={20} /></span>
        <div className="flex-1 min-w-[200px]">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Your profile</p>
          <h2 id="cv-h" className="font-semibold">{p.headline || "No title"}</h2>
          <p className="text-sm text-body">{p.years} years · {cap(p.level)}{p.domains.length > 0 && <> · {p.domains.join(", ")}</>}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={() => setEdit(true)}><Icon.edit size={15} /> Edit</button>
          <button type="button" className="btn-outline btn-sm" onClick={() => fileRef.current?.click()}>Replace CV</button>
          <button type="button" className="icon-btn" aria-label="Remove profile" disabled={remove.isPending}
            onClick={() => { if (confirm("Remove your saved profile and CV text?")) remove.mutate(); }}><Icon.trash size={16} /></button>
        </div>
      </div>
      {p.skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {p.skills.slice(0, 16).map((s) => <span key={s} className="chip bg-accent-soft text-accent-dark">{s}</span>)}
          {p.skills.length > 16 && <span className="chip bg-[#F1F3F6] text-muted">+{p.skills.length - 16}</span>}
        </div>
      )}
      <p className="text-xs text-muted">
        From {p.cv_name || "your CV"}{p.updated_at && <> · {ago(p.updated_at)}</>}. Used by Job search and Interview prep.
      </p>
      {p.cv_text && (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted hover:text-ink">What the AI sees</summary>
          <pre className="mt-2 whitespace-pre-wrap text-xs text-body bg-ground rounded-lg p-3 max-h-60 overflow-auto">{p.cv_text}</pre>
        </details>
      )}
      {(upload.isError || remove.isError) && <ErrorBox error={upload.error ?? remove.error} />}
      {edit && <EditProfile p={p} onClose={() => setEdit(false)} />}
    </section>
  );
}

function EditProfile({ p, onClose }: { p: CareerProfile; onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({
    headline: p.headline, years: p.years, level: p.level, summary: p.summary,
    domains: p.domains.join(", "), skills: p.skills.join(", "), roles: p.roles.join(", "),
  });
  const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
  const save = useMutation({
    mutationFn: () => api.editProfile({ ...f, domains: list(f.domains), skills: list(f.skills), roles: list(f.roles) }),
    onSuccess: (d) => { qc.setQueryData(["career-profile"], d); onClose(); },
  });
  const set = (k: keyof typeof f, v: string | number) => setF({ ...f, [k]: v });
  return (
    <Dialog title="Edit profile" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Field id="pf-h" label="Title"><input id="pf-h" className="input" value={f.headline} onChange={(e) => set("headline", e.target.value)} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field id="pf-y" label="Years of experience">
            <input id="pf-y" type="number" min={0} max={60} className="input" value={f.years} onChange={(e) => set("years", Number(e.target.value))} />
          </Field>
          <Field id="pf-l" label="Level">
            <select id="pf-l" className="input" value={f.level} onChange={(e) => set("level", e.target.value)}>
              {LEVELS.map((l) => <option key={l} value={l}>{cap(l)}</option>)}
            </select>
          </Field>
        </div>
        <Field id="pf-d" label="Domains" hint="Comma separated"><input id="pf-d" className="input" value={f.domains} onChange={(e) => set("domains", e.target.value)} /></Field>
        <Field id="pf-r" label="Roles to search for" hint="Comma separated"><input id="pf-r" className="input" value={f.roles} onChange={(e) => set("roles", e.target.value)} /></Field>
        <Field id="pf-s" label="Skills" hint="Comma separated, most used first">
          <textarea id="pf-s" className="input min-h-[80px]" value={f.skills} onChange={(e) => set("skills", e.target.value)} />
        </Field>
        <Field id="pf-m" label="Strengths"><textarea id="pf-m" className="input min-h-[70px]" value={f.summary} onChange={(e) => set("summary", e.target.value)} /></Field>
        {save.isError && <ErrorBox error={save.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary btn-sm" disabled={save.isPending}>Save</button>
        </div>
      </form>
    </Dialog>
  );
}
