import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, TrendingDown } from "lucide-react";
import { optimizationApi } from "@/api/entities";
import { useAuth } from "@/hooks/useAuth";
import { fmtMoney } from "@/lib/format";

const WRITE_ROLES = ["admin", "ciso", "risk_analyst"];

export default function InvestmentOptimization() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [budgetInput, setBudgetInput] = useState<string>("");

  const { data: candidates, isLoading: loadingCandidates } = useQuery({
    queryKey: ["investment-candidates"],
    queryFn: optimizationApi.listInvestments,
  });

  const { data: history } = useQuery({
    queryKey: ["recommendation-history"],
    queryFn: optimizationApi.history,
  });

  const latest = history && history.length > 0 ? history[0] : null;

  const recommendMutation = useMutation({
    mutationFn: () => optimizationApi.recommend(budgetInput ? Number(budgetInput) : undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investment-candidates"] });
      queryClient.invalidateQueries({ queryKey: ["recommendation-history"] });
    },
  });

  const canRun = user && WRITE_ROLES.includes(user.role);
  const selectedIds = new Set((recommendMutation.data ?? latest)?.selected_investments.map((i) => i.control_id) ?? []);
  const result = recommendMutation.data ?? latest;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Investment Optimization</h2>
        <p className="text-sm text-muted-foreground">
          Given a fixed budget, recommends which not-yet-deployed controls give the best risk reduction, solved exactly with Google OR-Tools.
        </p>
      </div>

      {canRun && (
        <div className="flex items-end gap-3 rounded-lg border border-border bg-muted/20 p-4">
          <div>
            <label className="text-xs text-muted-foreground">Budget (leave blank to use org default)</label>
            <input
              type="number"
              value={budgetInput}
              onChange={(e) => setBudgetInput(e.target.value)}
              placeholder="e.g. 500000"
              className="mt-1 w-56 rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={() => recommendMutation.mutate()}
            disabled={recommendMutation.isPending}
            className="flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-60"
          >
            <Sparkles size={14} />
            {recommendMutation.isPending ? "Optimizing..." : "Run optimization"}
          </button>
        </div>
      )}

      {recommendMutation.isError && (
        <p className="rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
          {(recommendMutation.error as any)?.response?.data?.detail ?? "Optimization failed — no candidate investments available."}
        </p>
      )}

      {result && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <SummaryCard label="Budget" value={fmtMoney(result.budget)} />
          <SummaryCard label="Recommended Investment" value={fmtMoney(result.total_investment)} accent="text-primary" />
          <SummaryCard label="Risk Reduction" value={fmtMoney(result.total_risk_reduction)} accent="text-success" />
          <SummaryCard label="Remaining Risk" value={fmtMoney(result.remaining_risk)} accent="text-warning" />
          <SummaryCard label="ROSI" value={`${result.rosi_percent.toFixed(0)}%`} accent="text-success" />
        </div>
      )}

      <div>
        <h3 className="mb-2 text-sm font-semibold text-muted-foreground">Candidate Investments</h3>
        {loadingCandidates && <p className="text-sm text-muted-foreground">Loading...</p>}
        {candidates && candidates.length === 0 && (
          <p className="rounded-lg border border-border bg-muted/20 p-6 text-center text-sm text-muted-foreground">
            No candidate investments yet — run an optimization to estimate not-yet-deployed controls, or add inactive controls to your catalog first.
          </p>
        )}
        {candidates && candidates.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-left text-muted-foreground">
                <tr>
                  <th className="px-4 py-2">Control</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Annual cost</th>
                  <th className="px-4 py-2">Est. risk reduction (alone)</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => (
                  <tr key={c.id} className="border-t border-border">
                    <td className="px-4 py-2 font-medium">{c.control_name}</td>
                    <td className="px-4 py-2 text-muted-foreground capitalize">{c.control_type.replace(/_/g, " ")}</td>
                    <td className="px-4 py-2">{fmtMoney(c.estimated_annual_cost)}</td>
                    <td className="px-4 py-2 flex items-center gap-1">
                      <TrendingDown size={14} className="text-success" /> {fmtMoney(c.estimated_risk_reduction)}
                    </td>
                    <td className="px-4 py-2">
                      {selectedIds.has(c.control_id) && (
                        <span className="rounded-full bg-success/20 px-2 py-0.5 text-xs font-medium text-success">Recommended</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="border-t border-border bg-muted/10 px-4 py-2 text-xs text-muted-foreground">
              "Risk reduction (alone)" shows each control's impact if deployed by itself — deploying several together does not simply add these up (see the combined totals above, which are recomputed exactly for the selected set).
            </p>
          </div>
        )}
      </div>
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
