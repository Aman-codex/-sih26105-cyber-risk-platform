import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { assetsApi, vulnerabilitiesApi } from "@/api/entities";
import { useAuth } from "@/hooks/useAuth";
import { SEVERITY_COLOR } from "@/types/entities";

const WRITE_ROLES = ["admin", "ciso", "risk_analyst"];
const DELETE_ROLES = ["admin", "ciso"];

export default function Vulnerabilities() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data, isLoading } = useQuery({ queryKey: ["vulnerabilities"], queryFn: vulnerabilitiesApi.list });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: assetsApi.list });

  const createMutation = useMutation({
    mutationFn: vulnerabilitiesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
      setShowForm(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: vulnerabilitiesApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] }),
  });

  const canWrite = user && WRITE_ROLES.includes(user.role);
  const canDelete = user && DELETE_ROLES.includes(user.role);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const selectedAssetIds = form.getAll("affected_asset_ids").map((v) => Number(v));
    createMutation.mutate({
      title: String(form.get("title")),
      cve_id: form.get("cve_id") ? String(form.get("cve_id")) : null,
      cvss_score: Number(form.get("cvss_score") || 0),
      exploitability: String(form.get("exploitability")),
      status: String(form.get("status")),
      affected_asset_ids: selectedAssetIds,
    });
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold">Vulnerabilities</h2>
          <p className="text-sm text-muted-foreground">CVE-tracked vulnerabilities, ranked by CVSS score.</p>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground"
          >
            <Plus size={14} /> Add vulnerability
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 grid grid-cols-2 gap-3 rounded-lg border border-border bg-muted/20 p-4">
          <input name="title" required placeholder="Title (e.g. Remote Code Execution in Login)" className="col-span-2 rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input name="cve_id" placeholder="CVE ID (optional, e.g. CVE-2026-12345)" className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input name="cvss_score" type="number" step="0.1" min="0" max="10" required placeholder="CVSS score (0-10)" className="rounded-md border border-border bg-background px-3 py-2 text-sm" />

          <select name="exploitability" defaultValue="theoretical" className="rounded-md border border-border bg-background px-3 py-2 text-sm">
            <option value="theoretical">Theoretical</option>
            <option value="proof_of_concept">Proof of Concept</option>
            <option value="functional">Functional</option>
            <option value="actively_exploited">Actively Exploited</option>
          </select>

          <select name="status" defaultValue="open" className="rounded-md border border-border bg-background px-3 py-2 text-sm">
            <option value="open">Open</option>
            <option value="mitigated">Mitigated</option>
            <option value="accepted_risk">Accepted Risk</option>
            <option value="false_positive">False Positive</option>
          </select>

          <div className="col-span-2">
            <label className="mb-1 block text-xs text-muted-foreground">Affected assets (select one or more)</label>
            <select name="affected_asset_ids" multiple size={Math.min(5, assets?.length ?? 3)} className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm">
              {assets?.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>

          <button type="submit" disabled={createMutation.isPending} className="col-span-2 rounded-md bg-primary py-2 text-sm text-primary-foreground disabled:opacity-60">
            {createMutation.isPending ? "Creating..." : "Create vulnerability"}
          </button>
          {createMutation.isError && (
            <p className="col-span-2 text-sm text-danger">
              {(createMutation.error as any)?.response?.data?.detail ?? "Failed to create vulnerability."}
            </p>
          )}
        </form>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

      {data && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2">CVE</th>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">CVSS</th>
                <th className="px-4 py-2">Severity</th>
                <th className="px-4 py-2">Exploitability</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Affected assets</th>
                {canDelete && <th className="px-4 py-2" />}
              </tr>
            </thead>
            <tbody>
              {data.map((v) => (
                <tr key={v.id} className="border-t border-border">
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{v.cve_id ?? "—"}</td>
                  <td className="px-4 py-2 font-medium">{v.title}</td>
                  <td className="px-4 py-2">{v.cvss_score.toFixed(1)}</td>
                  <td className={`px-4 py-2 font-medium capitalize ${SEVERITY_COLOR[v.severity]}`}>{v.severity}</td>
                  <td className="px-4 py-2 text-muted-foreground capitalize">{v.exploitability.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2 capitalize">{v.status.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2 text-muted-foreground">{v.affected_asset_ids.length} asset(s)</td>
                  {canDelete && (
                    <td className="px-4 py-2">
                      <button onClick={() => deleteMutation.mutate(v.id)} className="text-muted-foreground hover:text-danger">
                        <Trash2 size={14} />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
