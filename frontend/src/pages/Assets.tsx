import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Globe, Plus, Trash2 } from "lucide-react";
import { assetsApi } from "@/api/entities";
import { useAuth } from "@/hooks/useAuth";
import { fmtMoney } from "@/lib/format";
import { CRITICALITY_COLOR, type Asset, type BusinessCriticality } from "@/types/entities";

const WRITE_ROLES = ["admin", "ciso", "risk_analyst"];
const DELETE_ROLES = ["admin", "ciso"];

export default function Assets() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data: assets, isLoading } = useQuery({ queryKey: ["assets"], queryFn: assetsApi.list });

  const createMutation = useMutation({
    mutationFn: assetsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setShowForm(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: assetsApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets"] }),
  });

  const canWrite = user && WRITE_ROLES.includes(user.role);
  const canDelete = user && DELETE_ROLES.includes(user.role);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createMutation.mutate({
      name: String(form.get("name")),
      asset_type: String(form.get("asset_type")),
      business_criticality: form.get("business_criticality") as BusinessCriticality,
      business_value: Number(form.get("business_value") || 0),
      internet_exposure: form.get("internet_exposure") === "on",
    });
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold">Assets</h2>
          <p className="text-sm text-muted-foreground">
            Business-critical systems tracked for risk quantification.
          </p>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground"
          >
            <Plus size={14} /> Add asset
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 grid grid-cols-2 gap-3 rounded-lg border border-border bg-muted/20 p-4">
          <input name="name" required placeholder="Asset name" className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input name="asset_type" required placeholder="Type (e.g. web_app, database, server)" className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <select name="business_criticality" defaultValue="medium" className="rounded-md border border-border bg-background px-3 py-2 text-sm">
            <option value="low">Low criticality</option>
            <option value="medium">Medium criticality</option>
            <option value="high">High criticality</option>
            <option value="critical">Critical</option>
          </select>
          <input name="business_value" type="number" placeholder="Business value ($)" className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <label className="col-span-2 flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" name="internet_exposure" /> Internet-exposed
          </label>
          <button type="submit" disabled={createMutation.isPending} className="col-span-2 rounded-md bg-primary py-2 text-sm text-primary-foreground disabled:opacity-60">
            {createMutation.isPending ? "Creating..." : "Create asset"}
          </button>
        </form>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Loading assets...</p>}

      {assets && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Criticality</th>
                <th className="px-4 py-2">Business value</th>
                <th className="px-4 py-2">Exposure</th>
                <th className="px-4 py-2">Depends on</th>
                {canDelete && <th className="px-4 py-2" />}
              </tr>
            </thead>
            <tbody>
              {assets.map((asset: Asset) => (
                <tr key={asset.id} className="border-t border-border">
                  <td className="px-4 py-2 font-medium">{asset.name}</td>
                  <td className="px-4 py-2 text-muted-foreground">{asset.asset_type}</td>
                  <td className={`px-4 py-2 font-medium capitalize ${CRITICALITY_COLOR[asset.business_criticality]}`}>
                    {asset.business_criticality}
                  </td>
                  <td className="px-4 py-2">{fmtMoney(asset.business_value)}</td>
                  <td className="px-4 py-2">
                    {asset.internet_exposure ? (
                      <span className="flex items-center gap-1 text-warning"><Globe size={14} /> Exposed</span>
                    ) : (
                      <span className="text-muted-foreground">Internal</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {asset.depends_on_ids.length
                      ? asset.depends_on_ids.map((id) => assets.find((a) => a.id === id)?.name ?? id).join(", ")
                      : "—"}
                  </td>
                  {canDelete && (
                    <td className="px-4 py-2">
                      <button onClick={() => deleteMutation.mutate(asset.id)} className="text-muted-foreground hover:text-danger">
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
