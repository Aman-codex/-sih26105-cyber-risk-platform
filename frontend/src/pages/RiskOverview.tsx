import { Fragment, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { assetsApi, risksApi } from "@/api/entities";
import { useAuth } from "@/hooks/useAuth";
import { fmtMoney } from "@/lib/format";
import type { Risk } from "@/types/entities";

const WRITE_ROLES = ["admin", "ciso", "risk_analyst"];

function bandForScore(score: number): { label: string; color: string } {
  if (score >= 75) return { label: "Critical", color: "text-danger" };
  if (score >= 50) return { label: "High", color: "text-warning" };
  if (score >= 25) return { label: "Medium", color: "text-warning" };
  return { label: "Low", color: "text-muted-foreground" };
}

export default function RiskOverview() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data: summary, isLoading: loadingSummary } = useQuery({ queryKey: ["risk-summary"], queryFn: risksApi.summary });
  const { data: risks, isLoading: loadingRisks } = useQuery({ queryKey: ["risks"], queryFn: risksApi.list });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: assetsApi.list });

  const recalcMutation = useMutation({
    mutationFn: risksApi.recalculateAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["risks"] });
      queryClient.invalidateQueries({ queryKey: ["risk-summary"] });
    },
  });

  const canRecalculate = user && WRITE_ROLES.includes(user.role);
  const assetName = (id: number) => assets?.find((a) => a.id === id)?.name ?? `Asset #${id}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Risk Overview</h2>
          <p className="text-sm text-muted-foreground">
            Continuously quantified financial cyber risk across all assets.
          </p>
        </div>
        {canRecalculate && (
          <button
            onClick={() => recalcMutation.mutate()}
            disabled={recalcMutation.isPending}
            className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-60"
          >
            <RefreshCw size={14} className={recalcMutation.isPending ? "animate-spin" : ""} />
            {recalcMutation.isPending ? "Recalculating..." : "Recalculate all"}
          </button>
        )}
      </div>

      {!loadingSummary && summary && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <SummaryCard label="Total Financial Exposure" value={fmtMoney(summary.total_financial_exposure)} />
          <SummaryCard label="Expected Annual Loss (EAL)" value={fmtMoney(summary.total_expected_annual_loss)} accent="text-warning" />
          <SummaryCard label="Value at Risk (95%)" value={fmtMoney(summary.total_value_at_risk)} accent="text-danger" />
          <SummaryCard label="Assets Assessed" value={String(summary.asset_count)} />
        </div>
      )}

      {summary && (
        <div className="flex gap-3 text-sm">
          <Badge label="Critical" count={summary.critical_risk_count} color="bg-danger/20 text-danger" />
          <Badge label="High" count={summary.high_risk_count} color="bg-warning/20 text-warning" />
          <Badge label="Medium" count={summary.medium_risk_count} color="bg-warning/10 text-warning" />
          <Badge label="Low" count={summary.low_risk_count} color="bg-muted text-muted-foreground" />
        </div>
      )}

      {loadingRisks && <p className="text-sm text-muted-foreground">Loading risks...</p>}

      {risks && risks.length === 0 && (
        <p className="rounded-lg border border-border bg-muted/20 p-6 text-center text-sm text-muted-foreground">
          No risk calculations yet. Click "Recalculate all" to run the risk engine against your current assets.
        </p>
      )}

      {risks && risks.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Asset</th>
                <th className="px-4 py-2">Risk score</th>
                <th className="px-4 py-2">Band</th>
                <th className="px-4 py-2">Likelihood</th>
                <th className="px-4 py-2">EAL</th>
                <th className="px-4 py-2">VaR (95%)</th>
              </tr>
            </thead>
            <tbody>
              {risks.map((risk: Risk) => {
                const band = bandForScore(risk.risk_score);
                const isExpanded = expandedId === risk.id;
                const scenario = risk.scenarios.find((s) => s.name === "current");
                return (
                  <Fragment key={risk.id}>
                    <tr
                      onClick={() => setExpandedId(isExpanded ? null : risk.id)}
                      className="cursor-pointer border-t border-border hover:bg-muted/20"
                    >
                      <td className="px-4 py-2 font-medium">{assetName(risk.asset_id)}</td>
                      <td className="px-4 py-2">{risk.risk_score.toFixed(1)}</td>
                      <td className={`px-4 py-2 font-medium ${band.color}`}>{band.label}</td>
                      <td className="px-4 py-2">{(risk.likelihood * 100).toFixed(1)}%</td>
                      <td className="px-4 py-2">{fmtMoney(risk.expected_annual_loss)}</td>
                      <td className="px-4 py-2">{scenario ? fmtMoney(scenario.value_at_risk) : "—"}</td>
                    </tr>
                    {isExpanded && (
                      <tr className="border-t border-border bg-muted/10">
                        <td colSpan={6} className="px-4 py-4">
                          <div className="grid grid-cols-2 gap-6">
                            <div>
                              <h4 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Risk drivers</h4>
                              <ul className="space-y-1">
                                {risk.risk_drivers.map((d, i) => (
                                  <li key={i} className="flex items-center justify-between text-sm">
                                    <span>{d.factor}</span>
                                    <span className={`flex items-center gap-1 font-medium ${d.impact_pct > 0 ? "text-danger" : d.impact_pct < 0 ? "text-success" : "text-muted-foreground"}`}>
                                      {d.impact_pct > 0 ? <TrendingUp size={12} /> : d.impact_pct < 0 ? <TrendingDown size={12} /> : null}
                                      {d.impact_pct > 0 ? "+" : ""}{d.impact_pct.toFixed(1)}%
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                            {risk.financial_impact && (
                              <div>
                                <h4 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Financial impact breakdown</h4>
                                <ul className="space-y-1 text-sm">
                                  {Object.entries(risk.financial_impact)
                                    .filter(([key]) => key !== "total_impact")
                                    .map(([key, value]) => (
                                      <li key={key} className="flex items-center justify-between">
                                        <span className="capitalize text-muted-foreground">{key.replace(/_/g, " ")}</span>
                                        <span>{fmtMoney(value as number)}</span>
                                      </li>
                                    ))}
                                  <li className="flex items-center justify-between border-t border-border pt-1 font-medium">
                                    <span>Total (if fully realized)</span>
                                    <span>{fmtMoney(risk.financial_impact.total_impact)}</span>
                                  </li>
                                </ul>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${accent ?? ""}`}>{value}</p>
    </div>
  );
}

function Badge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <span className={`rounded-full px-3 py-1 ${color}`}>
      {label}: {count}
    </span>
  );
}
