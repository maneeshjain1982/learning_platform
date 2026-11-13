import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api, ApiError, type Me } from "../api";
import { Thinking } from "./ui";

const MeCtx = createContext<Me | null>(null);

/** The signed-in account. Only used below <AuthGate>, so it is always set. */
export function useMe(): Me {
  const me = useContext(MeCtx);
  if (!me) throw new Error("useMe outside AuthGate");
  return me;
}

/** Shows the sign-in page until there is a session; signing out (or an expired session) comes back here. */
export function AuthGate({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false, staleTime: Infinity });
  useEffect(() => {
    const expired = () => { qc.clear(); qc.setQueryData(["me"], null); };
    window.addEventListener("auth:expired", expired);
    return () => window.removeEventListener("auth:expired", expired);
  }, [qc]);

  if (me.isLoading) return <main className="min-h-screen flex items-center justify-center"><Thinking label="Loading…" /></main>;
  if (me.isError && !(me.error instanceof ApiError && me.error.status === 401)) {
    return <main className="min-h-screen flex items-center justify-center p-6 text-body">Can't reach the server. Is it running?</main>;
  }
  if (!me.data) return <Login />;
  return <MeCtx.Provider value={me.data}>{children}</MeCtx.Provider>;
}

function Login() {
  const qc = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => api.login(username.trim(), password),
    onSuccess: (me) => { qc.clear(); qc.setQueryData(["me"], me); },
  });
  const submit = (e: FormEvent) => { e.preventDefault(); login.mutate(); };

  return (
    <main className="min-h-screen grid place-items-center px-4 py-10 bg-ground">
      <div className="w-full max-w-[400px] flex flex-col gap-6">
        <div className="flex items-center gap-3 justify-center">
          <span className="w-10 h-10 rounded-xl bg-accent text-white font-display font-bold text-lg flex items-center justify-center">S</span>
          <span className="font-display font-semibold text-xl">Study Companion</span>
        </div>
        <form onSubmit={submit} className="card p-7 flex flex-col gap-4 shadow-sm" aria-labelledby="login-h">
          <div>
            <h1 id="login-h" className="h-display text-2xl">Sign in</h1>
            <p className="text-sm text-muted mt-1">Your own home page, paths and progress.</p>
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="un" className="label">Username</label>
            <input id="un" className="input" autoComplete="username" autoFocus required value={username}
              onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="pw" className="label">Password</label>
            <input id="pw" type="password" className="input" autoComplete="current-password" required value={password}
              onChange={(e) => setPassword(e.target.value)} />
          </div>
          {login.isError && (
            <p role="alert" className="text-sm text-[#B42318] bg-[#FEF3F2] border border-[#FECDCA] rounded-lg px-3 py-2">
              {login.error instanceof ApiError && login.error.status === 401 ? "Wrong username or password." : String(login.error.message)}
            </p>
          )}
          <button type="submit" className="btn-primary justify-center" disabled={login.isPending}>
            {login.isPending ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}

/** Sign out: ends the session and returns to the sign-in page. */
export function useSignOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSettled: () => { qc.clear(); qc.setQueryData(["me"], null); },
  });
}
