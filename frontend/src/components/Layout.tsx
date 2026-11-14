import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Icon } from "./ui";

/** Every page: a left panel to browse, and the details on the right. On phones the panel slides in. */
export function TwoPane({ side, sideLabel, children }: { side: ReactNode; sideLabel: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);
  return (
    <div className="flex-1 flex w-full">
      <aside aria-label={sideLabel}
        className="hidden lg:block w-[292px] shrink-0 bg-white border-r border-line sticky top-[69px] h-[calc(100vh-69px)] overflow-y-auto">
        {side}
      </aside>
      {open && (
        <div className="lg:hidden fixed inset-0 z-40 flex" role="dialog" aria-modal="true" aria-label={sideLabel}>
          <div className="w-[86%] max-w-[340px] bg-white h-full overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-line">
              <span className="font-semibold">{sideLabel}</span>
              <button type="button" className="icon-btn" aria-label="Close" onClick={() => setOpen(false)}><Icon.close /></button>
            </div>
            {side}
          </div>
          <button type="button" aria-label="Close" className="flex-1 bg-ink/40" onClick={() => setOpen(false)} />
        </div>
      )}
      <div className="flex-1 min-w-0 flex flex-col">
        <div className="lg:hidden px-4 pt-4">
          <button type="button" className="btn-outline btn-sm" onClick={() => setOpen(true)}>
            <Icon.menu size={16} /> {sideLabel}
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Small uppercase label above a group of links in the left panel. */
export function SideHeading({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 px-5 pt-5 pb-1.5">
      <h2 className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted">{children}</h2>
      {action}
    </div>
  );
}

const sideLink = ({ isActive }: { isActive: boolean }) =>
  `group flex items-start gap-2.5 mx-2 px-3 py-2 rounded-lg text-[14px] leading-snug ${
    isActive ? "bg-accent-soft text-accent-dark font-semibold" : "text-body hover:bg-ground hover:text-ink"}`;

/** A link in the left panel. */
export function SideLink({ to, children, end, icon, meta }: {
  to: string; children: ReactNode; end?: boolean; icon?: ReactNode; meta?: ReactNode;
}) {
  return (
    <NavLink to={to} end={end} className={sideLink}>
      {icon && <span className="mt-0.5 shrink-0 text-muted group-[.active]:text-accent">{icon}</span>}
      <span className="flex-1 min-w-0">{children}</span>
      {meta && <span className="shrink-0 text-xs text-muted font-normal mt-0.5">{meta}</span>}
    </NavLink>
  );
}

/** A collapsible group of links (a section and its topics). Opens itself when it holds the current page. */
export function SideGroup({ title, count, active, children, actions }: {
  title: string; count?: number; active: boolean; children: ReactNode; actions?: ReactNode;
}) {
  const [open, setOpen] = useState(active);
  useEffect(() => { if (active) setOpen(true); }, [active]);
  return (
    <div className="mx-2 group/side">
      <div className="flex items-center">
        <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}
          className={`flex-1 flex items-center gap-2 px-3 py-2 rounded-lg text-left text-[14px] hover:bg-ground ${active ? "text-ink font-semibold" : "text-ink"}`}>
          <Icon.chevron size={14} className={`shrink-0 text-muted transition-transform ${open ? "rotate-90" : ""}`} />
          <span className="flex-1 min-w-0 font-semibold">{title}</span>
          {count !== undefined && <span className="text-xs text-muted">{count}</span>}
        </button>
        {actions && <span className="opacity-0 group-hover/side:opacity-100 focus-within:opacity-100 transition-opacity">{actions}</span>}
      </div>
      {open && <div className="ml-[18px] border-l border-line pl-1 pb-1">{children}</div>}
    </div>
  );
}

/** The right-hand detail area: a readable column with page padding. */
export function Detail({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <main className={`w-full ${wide ? "max-w-[1120px]" : "max-w-[900px]"} px-4 sm:px-8 lg:px-10 py-6 lg:py-8 flex flex-col gap-6`}>
      {children}
    </main>
  );
}

/** Breadcrumb trail above a page title. */
export function Crumbs({ items }: { items: { label: string; to?: string }[] }) {
  return (
    <nav aria-label="Breadcrumb" className="text-sm text-muted flex flex-wrap items-center gap-1.5">
      {items.map((c, i) => (
        <span key={i} className="inline-flex items-center gap-1.5">
          {i > 0 && <Icon.chevron size={12} />}
          {c.to ? <NavLink to={c.to} className="hover:text-accent">{c.label}</NavLink> : <span>{c.label}</span>}
        </span>
      ))}
    </nav>
  );
}
