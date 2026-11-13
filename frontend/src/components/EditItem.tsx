import { useMutation, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../api";
import { useMe } from "./Auth";
import { ErrorBox, Icon } from "./ui";

export type EditField = { name: string; label: string; value: string; long?: boolean };

/** Edit / Delete (admin, for every account) or Hide (other accounts, just for them) on a built-in catalog item. */
export function ItemActions({ scope, itemKey, title, fields, queryKey }: {
  scope: string; itemKey: string; title: string; fields: EditField[]; queryKey: QueryKey;
}) {
  const me = useMe();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const del = useMutation({
    mutationFn: () => api.deleteItem(scope, itemKey),
    onSuccess: () => qc.invalidateQueries({ queryKey }),
  });
  const ask = me.is_admin ? `Delete "${title}" for every account? You can restore it later.` : `Hide "${title}"? You can restore it later.`;
  return (
    <span className="inline-flex items-center gap-1 self-start shrink-0">
      {me.is_admin && fields.length > 0 && (
        <button type="button" className="icon-btn" aria-label={`Edit ${title}`} title="Edit" onClick={() => setEditing(true)}><Icon.edit size={15} /></button>
      )}
      <button type="button" className="icon-btn" aria-label={`${me.is_admin ? "Delete" : "Hide"} ${title}`} title={me.is_admin ? "Delete" : "Hide"}
        disabled={del.isPending} onClick={() => { if (confirm(ask)) del.mutate(); }}>
        {me.is_admin ? <Icon.trash size={15} /> : <Icon.close size={15} />}
      </button>
      {editing && <EditDialog scope={scope} itemKey={itemKey} title={title} fields={fields} queryKey={queryKey} onClose={() => setEditing(false)} />}
    </span>
  );
}

function EditDialog({ scope, itemKey, title, fields, queryKey, onClose }: {
  scope: string; itemKey: string; title: string; fields: EditField[]; queryKey: QueryKey; onClose: () => void;
}) {
  const qc = useQueryClient();
  const [f, setF] = useState<Record<string, string>>(() => Object.fromEntries(fields.map((x) => [x.name, x.value ?? ""])));
  const save = useMutation({
    mutationFn: () => api.editItem(scope, itemKey, f),
    onSuccess: () => { qc.invalidateQueries({ queryKey }); onClose(); },
  });
  return (
    <Dialog title={`Edit: ${title}`} onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        {fields.map((x) => (
          <div key={x.name} className="flex flex-col gap-1">
            <label htmlFor={`ed-${x.name}`} className="label">{x.label}</label>
            {x.long
              ? <textarea id={`ed-${x.name}`} className="input" rows={3} value={f[x.name]} onChange={(e) => setF({ ...f, [x.name]: e.target.value })} />
              : <input id={`ed-${x.name}`} className="input" value={f[x.name]} onChange={(e) => setF({ ...f, [x.name]: e.target.value })} />}
          </div>
        ))}
        <p className="text-xs text-muted">Changes apply for every account. Restore brings back the original.</p>
        {save.isError && <ErrorBox error={save.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary btn-sm" disabled={save.isPending}>Save</button>
        </div>
      </form>
    </Dialog>
  );
}

/** "3 removed · Restore": brings back hidden/deleted items (and, for the admin, undoes edits). */
export function RemovedNote({ scope, count, edited = false, queryKey }: { scope: string; count: number; edited?: boolean; queryKey: QueryKey }) {
  const me = useMe();
  const qc = useQueryClient();
  const reset = useMutation({ mutationFn: () => api.resetItems(scope), onSuccess: () => qc.invalidateQueries({ queryKey }) });
  if (!count && !(me.is_admin && edited)) return null;
  const what = [count ? `${count} ${me.is_admin ? "removed" : "hidden"}` : "", me.is_admin && edited ? "edited" : ""].filter(Boolean).join(", ");
  return (
    <p className="text-sm text-muted flex flex-wrap items-center gap-2">
      <span>{what}.</span>
      <button type="button" className="font-semibold text-accent hover:underline" disabled={reset.isPending}
        onClick={() => { if (confirm("Restore the original list?")) reset.mutate(); }}>Restore original</button>
    </p>
  );
}

/** Small modal used by the edit forms. */
export function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-40 bg-black/30 flex items-end sm:items-center justify-center sm:p-6"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div role="dialog" aria-modal="true" aria-label={title}
        className="bg-white w-full sm:max-w-[560px] rounded-t-2xl sm:rounded-2xl shadow-xl p-5 flex flex-col gap-4 max-h-[90vh] overflow-auto text-left">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold truncate">{title}</h2>
          <button type="button" aria-label="Close" className="icon-btn" onClick={onClose}><Icon.close /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** "Remove" on an item an LLM research run found (news update, job, certification change, research find). */
export function RemoveFound({ job, url, title, queryKey }: { job: string; url: string; title: string; queryKey: QueryKey }) {
  const qc = useQueryClient();
  const rm = useMutation({ mutationFn: () => api.removeJobItem(job, url), onSuccess: () => qc.invalidateQueries({ queryKey }) });
  return (
    <button type="button" className="icon-btn" aria-label={`Remove ${title}`} title="Remove" disabled={rm.isPending}
      onClick={() => rm.mutate()}><Icon.trash size={15} /></button>
  );
}
