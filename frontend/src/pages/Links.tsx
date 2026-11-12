import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api";
import { MyLinksSection } from "../components/Manage";
import { ErrorBox, Thinking } from "../components/ui";

/** Every course and link you added, including ones hidden from home or tied to one path. */
export default function Links() {
  const links = useQuery({ queryKey: ["links", "all"], queryFn: () => api.links() });
  const paths = useQuery({ queryKey: ["paths"], queryFn: api.paths });
  const [filter, setFilter] = useState<string>("all");
  const all = links.data ?? [];
  const shown = all.filter((l) =>
    filter === "all" ? true : filter === "general" ? l.path_id === null : l.path_id === Number(filter));

  return (
    <main className="max-w-[1100px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-5">
      {links.isLoading && <Thinking label="Loading…" />}
      {links.isError && <ErrorBox error={links.error} onRetry={() => links.refetch()} />}
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="lf" className="text-sm font-semibold">Show</label>
        <select id="lf" className="input w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All ({all.length})</option>
          <option value="general">General only</option>
          {paths.data?.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
        </select>
      </div>
      <MyLinksSection headingLevel={1} links={shown} title="My courses & links"
        pathId={filter !== "all" && filter !== "general" ? Number(filter) : null}
        intro="Everything you added yourself. Use “Show on my home page” in each one to choose what appears on Home." />
    </main>
  );
}
