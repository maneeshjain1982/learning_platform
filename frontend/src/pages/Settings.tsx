import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../api";
import { useMe } from "../components/Auth";
import { ErrorBox, Thinking } from "../components/ui";

export default function Settings() {
  const qc = useQueryClient();
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const providers = useQuery({ queryKey: ["providers"], queryFn: api.providers });
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  useEffect(() => { if (profile.data) { setName(profile.data.name); setEmail(profile.data.email ?? ""); } }, [profile.data]);
  const save = useMutation({
    mutationFn: () => api.saveProfile({ name, email: email || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["profile"] }); qc.invalidateQueries({ queryKey: ["home"] }); },
  });

  const restore = useMutation({ mutationFn: api.restoreStarters, onSuccess: () => qc.invalidateQueries() });

  return (
    <main className="max-w-[760px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-6">
      <h1 className="h-display text-3xl">Profile and settings</h1>

      <form className="card p-6 flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <h2 className="text-lg font-semibold">Profile</h2>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="name" className="label">Name</label>
          <input id="name" className="input" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className="label">Email <span className="font-normal text-muted">(optional)</span></label>
          <input id="email" type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="flex items-center gap-3">
          <button type="submit" className="btn-primary self-start" disabled={save.isPending}>Save</button>
          {save.isSuccess && <span className="text-sm text-ok" role="status">Saved</span>}
        </div>
        {save.isError && <ErrorBox error={save.error} />}
      </form>

      <PasswordCard />

      <section className="card p-6 flex flex-col gap-4" aria-labelledby="llm-h">
        <h2 id="llm-h" className="text-lg font-semibold">LLM (via LLM Bridge)</h2>
        {providers.isLoading && <Thinking label="Checking installed CLIs…" />}
        {providers.isError && <ErrorBox error={providers.error} />}
        {providers.data && (
          <>
            <p className="text-sm text-body">
              In use: <strong>{providers.data.active.provider}</strong>, model <strong>{providers.data.active.model}</strong> for planning,
              notes and Ask LLM, and <strong>{providers.data.active.fast_model}</strong> for quick steps. Change with the
              <code className="mx-1 px-1 bg-[#F1F3F6] rounded">LLM_PROVIDER</code>, <code className="mx-1 px-1 bg-[#F1F3F6] rounded">LLM_MODEL</code> and
              <code className="mx-1 px-1 bg-[#F1F3F6] rounded">LLM_FAST_MODEL</code> environment variables.
            </p>
            <ul className="flex flex-col gap-2">
              {providers.data.providers.map((p) => (
                <li key={p.name} className="flex flex-wrap items-center gap-3 p-3 rounded-xl border border-line">
                  <span className={`chip ${p.available ? "bg-ok-soft text-ok-dark" : "bg-[#F1F3F6] text-muted"}`}>{p.available ? "Available" : "Not installed"}</span>
                  <span className="font-semibold">{p.label}</span>
                  <span className="text-xs text-muted">models: {p.models.join(", ")}</span>
                  {p.error && <span className="w-full text-xs text-muted">{p.error}</span>}
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted">Every agent step and Ask LLM answer counts toward that account's plan usage.</p>
          </>
        )}
      </section>
      <section className="card p-6 flex flex-col gap-3" aria-labelledby="st-h">
        <h2 id="st-h" className="text-lg font-semibold">Starter paths</h2>
        <p className="text-sm text-body">Deleted one of the starter paths (Agentic AI, LLM Fundamentals, Agentic Harness)? Bring it back with its papers. Your other paths aren't changed.</p>
        <div className="flex items-center gap-3">
          <button type="button" className="btn-outline self-start" disabled={restore.isPending} onClick={() => restore.mutate()}>Restore starter paths</button>
          {restore.isSuccess && <span className="text-sm text-ok" role="status">
            {restore.data.restored ? `Restored ${restore.data.restored} path${restore.data.restored > 1 ? "s" : ""}` : "All starter paths are already here"}
          </span>}
        </div>
        {restore.isError && <ErrorBox error={restore.error} />}
      </section>
    </main>
  );
}

function PasswordCard() {
  const qc = useQueryClient();
  const me = useMe();
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const change = useMutation({
    mutationFn: () => api.changePassword(cur, next),
    onSuccess: (m) => { qc.setQueryData(["me"], m); setCur(""); setNext(""); setAgain(""); },
  });
  const mismatch = again.length > 0 && next !== again;
  return (
    <form className="card p-6 flex flex-col gap-4" aria-labelledby="pw-h"
      onSubmit={(e) => { e.preventDefault(); if (!mismatch) change.mutate(); }}>
      <div>
        <h2 id="pw-h" className="text-lg font-semibold">Password</h2>
        <p className="text-sm text-muted mt-1">Signed in as <strong>{me.username}</strong> ({me.is_admin ? "admin" : "user"} account).</p>
      </div>
      {me.default_password && (
        <p className="text-sm bg-pp-bg text-pp-fg rounded-lg px-3 py-2">You're still using the default password. Change it so only you can sign in.</p>
      )}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="pw-cur" className="label">Current</label>
          <input id="pw-cur" type="password" className="input" autoComplete="current-password" required value={cur} onChange={(e) => setCur(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="pw-new" className="label">New (4+ characters)</label>
          <input id="pw-new" type="password" className="input" autoComplete="new-password" minLength={4} required value={next} onChange={(e) => setNext(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="pw-again" className="label">New again</label>
          <input id="pw-again" type="password" className="input" autoComplete="new-password" required value={again}
            aria-invalid={mismatch} onChange={(e) => setAgain(e.target.value)} />
        </div>
      </div>
      {mismatch && <p className="text-sm text-[#B42318]" role="alert">The new passwords don't match.</p>}
      <div className="flex items-center gap-3">
        <button type="submit" className="btn-primary self-start" disabled={change.isPending || mismatch}>Change password</button>
        {change.isSuccess && <span className="text-sm text-ok" role="status">Password changed</span>}
      </div>
      {change.isError && <ErrorBox error={change.error} />}
    </form>
  );
}
