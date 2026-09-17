import { useQuery } from "@tanstack/react-query";
import { controlsApi } from "@/api/entities";
import { fmtMoney } from "@/lib/format";

export default function Controls() {
  const { data, isLoading } = useQuery({ queryKey: ["controls"], queryFn: controlsApi.list });

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-lg font-semibold">Security Controls</h2>
        <p className="text-sm text-muted-foreground">
          Cost and effectiveness per control — the inputs the Investment Optimizer (Phase 5) will use.
        </p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

      {data && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Control</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Annual cost</th>
                <th className="px-4 py-2">Effectiveness</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Protected assets</th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id} className="border-t border-border">
                  <td className="px-4 py-2 font-medium">{c.name}</td>
                  <td className="px-4 py-2 text-muted-foreground capitalize">{c.control_type.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2">{fmtMoney(c.annual_cost)}</td>
                  <td className="px-4 py-2">{Math.round(c.effectiveness_score * 100)}%</td>
                  <td className="px-4 py-2">
                    <span className={c.is_active ? "text-success" : "text-muted-foreground"}>
                      {c.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">{c.protected_asset_ids.length} asset(s)</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
