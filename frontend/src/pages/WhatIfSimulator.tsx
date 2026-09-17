import { FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, FlaskConical } from "lucide-react";
import { controlsApi, vulnerabilitiesApi, whatIfApi, type WhatIfPayload } from "@/api/entities";
import { fmtMoney } from "@/lib/format";
import type { BudgetWhatIfResponse, WhatIfResponse } from "@/types/entities";

const SCENARIOS: { value: WhatIfPayload["scenario_type"]; label: string }[] = [
  { value: "add_control", label: "Add a new control" },
  { value: "remove_control", label: "Remove an active control" },
  { value: "fix_vulnerability", label: "Fix a vulnerability" },
  { value: "improve_control_effectiveness", label: "Improve a control's effectiveness" },
  { value: "increase_budget", label: "Change the cybersecurity budget" },
];

function isBudgetResponse(r: WhatIfResponse | BudgetWhatIfResponse): r is BudgetWhatIfResponse {
  return r.scenario_type === "increase_budget";
}

export default function WhatIfSimulator() {
  const [scenarioType, setScenarioType] = useState<WhatIfPayload["scenario_type"]>("add_control");

  const { data: controls } = useQuery({ queryKey: ["controls"], queryFn: controlsApi.list });
  const { data: vulnerabilities } = useQuery({ queryKey: ["vulnerabilities"], queryFn: vulnerabilitiesApi.list });

  const simulateMutation = useMutation({ mutationFn: whatIfApi.simulate });

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload: WhatIfPayload = { scenario_type: scenarioType };

    if (scenarioType === "add_control" || scenarioType === "remove_control" || scenarioType === "improve_control_effectiveness") {
      payload.control_id = Number(form.get("control_id"));
    }
    if (scenarioType === "improve_control_effectiveness") {
      payload.new_effectiveness = Number(form.get("new_effectiveness")) / 100;
    }
    if (scenarioType === "fix_vulnerability") {
      payload.vulnerability_id = Number(form.get("vulnerability_id"));
    }
    if (scenarioType === "increase_budget") {
      payload.new_budget = Number(form.get("new_budget"));
      const oldBudget = form.get("old_budget");
      if (oldBudget) payload.old_budget = Number(oldBudget);
    }

    simulateMutation.mutate(payload);
  }

  const result = simulateMutation.data;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">What-If Simulator</h2>
        <p className="text-sm text-muted-foreground">
          Explore a hypothetical change and see the before/after impact. Nothing here is saved — pure exploration.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-border bg-muted/20 p-4">
        <div>
          <label className="text-xs text-muted-foreground">Scenario</label>
          <select
            value={scenarioType}
            onChange={(e) => setScenarioType(e.target.value as WhatIfPayload["scenario_type"])}
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          >
            {SCENARIOS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {(scenarioType === "add_control" || scenarioType === "remove_control" || scenarioType === "improve_control_effectiveness") && (
          <div>
            <label className="text-xs text-muted-foreground">
              {scenarioType === "add_control" ? "Control to add (pick an inactive one for a real effect)" : "Control"}
            </label>
            <select name="control_id" required className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm">
              <option value="">Select a control...</option>
              {controls?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.is_active ? "active" : "inactive"}, {Math.round(c.effectiveness_score * 100)}% effective, {fmtMoney(c.annual_cost)}/yr)
                </option>
              ))}
            </select>
          </div>
        )}

        {scenarioType === "improve_control_effectiveness" && (
          <div>
            <label className="text-xs text-muted-foreground">New effectiveness (%)</label>
            <input name="new_effectiveness" type="number" min={0} max={100} required defaultValue={50}
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm" />
          </div>
        )}

        {scenarioType === "fix_vulnerability" && (
          <div>
            <label className="text-xs text-muted-foreground">Vulnerability to fix</label>
            <select name="vulnerability_id" required className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm">
              <option value="">Select a vulnerability...</option>
              {vulnerabilities?.filter((v) => v.status === "open").map((v) => (
                <option key={v.id} value={v.id}>{v.cve_id ?? v.title} (CVSS {v.cvss_score.toFixed(1)})</option>
              ))}
            </select>
          </div>
        )}

        {scenarioType === "increase_budget" && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground">Old budget (blank = current org budget)</label>
              <input name="old_budget" type="number" placeholder="e.g. 5000000"
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">New budget</label>
              <input name="new_budget" type="number" required placeholder="e.g. 8000000"
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm" />
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={simulateMutation.isPending}
          className="flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-60"
        >
          <FlaskConical size={14} /> {simulateMutation.isPending ? "Simulating..." : "Run simulation"}
        </button>
      </form>

      {simulateMutation.isError && (
        <p className="rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
          {(simulateMutation.error as any)?.response?.data?.detail ?? "Simulation failed."}
        </p>
      )}

      {result && !isBudgetResponse(result) && <AssetBasedResult result={result} />}
      {result && isBudgetResponse(result) && <BudgetResult result={result} />}
    </div>
  );
}

function AssetBasedResult({ result }: { result: WhatIfResponse }) {
  return (
    <div className="space-y-4">
      <p className="text-sm font-medium">{result.description}</p>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <SummaryCard label="Total EAL before" value={fmtMoney(result.total_eal_before)} />
        <SummaryCard label="Total EAL after" value={fmtMoney(result.total_eal_after)} accent={result.eal_change < 0 ? "text-success" : "text-danger"} />
        <SummaryCard
          label="Change"
          value={`${result.eal_change < 0 ? "−" : "+"}${fmtMoney(Math.abs(result.eal_change))}`}
          accent={result.eal_change < 0 ? "text-success" : "text-danger"}
        />
        <SummaryCard
          label="Investment change"
          value={`${result.investment_change < 0 ? "−" : "+"}${fmtMoney(Math.abs(result.investment_change))}`}
        />
      </div>

      {result.rosi_percent !== null && (
        <p className="text-sm text-muted-foreground">Return on Security Investment (ROSI): <span className="font-semibold text-success">{result.rosi_percent.toFixed(0)}%</span></p>
      )}

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left text-muted-foreground">
            <tr>
              <th className="px-4 py-2">Asset</th>
              <th className="px-4 py-2">Risk score (before → after)</th>
              <th className="px-4 py-2">Likelihood (before → after)</th>
              <th className="px-4 py-2">EAL (before → after)</th>
            </tr>
          </thead>
          <tbody>
            {result.before.map((b, i) => {
              const a = result.after[i];
              return (
                <tr key={b.asset_id} className="border-t border-border">
                  <td className="px-4 py-2 font-medium">{b.asset_name}</td>
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-1">{b.risk_score.toFixed(1)} <ArrowRight size={12} className="text-muted-foreground" /> {a.risk_score.toFixed(1)}</span>
                  </td>
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-1">{(b.likelihood * 100).toFixed(1)}% <ArrowRight size={12} className="text-muted-foreground" /> {(a.likelihood * 100).toFixed(1)}%</span>
                  </td>
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-1">{fmtMoney(b.expected_annual_loss)} <ArrowRight size={12} className="text-muted-foreground" /> {fmtMoney(a.expected_annual_loss)}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BudgetResult({ result }: { result: BudgetWhatIfResponse }) {
  return (
    <div className="space-y-4">
      <p className="text-sm font-medium">{result.description}</p>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <SummaryCard label="Old investment" value={fmtMoney(result.old_total_investment)} />
        <SummaryCard label="New investment" value={fmtMoney(result.new_total_investment)} accent="text-primary" />
        <SummaryCard label="Old risk reduction" value={fmtMoney(result.old_risk_reduction)} />
        <SummaryCard label="New risk reduction" value={fmtMoney(result.new_risk_reduction)} accent="text-success" />
      </div>
      <p className="text-sm text-muted-foreground">
        Additional risk reduction unlocked: <span className="font-semibold text-success">{fmtMoney(result.additional_risk_reduction)}</span>
      </p>
      {result.newly_affordable_controls.length > 0 ? (
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Newly affordable controls:</p>
          <ul className="list-disc pl-5 text-sm">
            {result.newly_affordable_controls.map((name) => <li key={name}>{name}</li>)}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No new controls become affordable at this budget level.</p>
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
