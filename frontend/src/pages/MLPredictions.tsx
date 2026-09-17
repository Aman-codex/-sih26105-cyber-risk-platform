import { useState, Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Brain, ChevronDown, ChevronRight } from "lucide-react";
import { mlApi } from "@/api/entities";

function probColor(p: number) {
  if (p >= 0.7) return "text-danger";
  if (p >= 0.4) return "text-warning";
  return "text-success";
}

export default function MLPredictions() {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["ml-predictions"], queryFn: () => mlApi.predictions() });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">ML Incident Likelihood Prediction</h2>
        <p className="text-sm text-muted-foreground">
          An interpretable model (Logistic Regression) predicting incident probability per asset, with feature-level explanations.
        </p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Training model and scoring assets...</p>}

      {data && (
        <>
          <div className="flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/10 p-4">
            <AlertTriangle size={18} className="mt-0.5 flex-shrink-0 text-warning" />
            <div>
              <p className="text-sm font-medium text-warning">Synthetic training data</p>
              <p className="text-xs text-muted-foreground mt-1">{data.model_info.caveat}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <InfoCard label="Model" value={data.model_info.model_type} />
            <InfoCard label="Training samples" value={String(data.model_info.training_samples)} />
            <InfoCard label="Test accuracy" value={`${(data.model_info.test_accuracy * 100).toFixed(1)}%`} />
            <InfoCard label="Test ROC AUC" value={data.model_info.test_roc_auc.toFixed(2)} />
          </div>

          {data.predictions.length === 0 ? (
            <p className="rounded-lg border border-border bg-muted/20 p-6 text-center text-sm text-muted-foreground">
              No assets to predict on yet — add assets first.
            </p>
          ) : (
            <div className="overflow-hidden rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2"></th>
                    <th className="px-4 py-2">Asset</th>
                    <th className="px-4 py-2">Predicted incident probability</th>
                  </tr>
                </thead>
                <tbody>
                  {data.predictions.map((p) => {
                    const isExpanded = expandedId === p.asset_id;
                    return (
                      <Fragment key={p.asset_id}>
                        <tr
                          onClick={() => setExpandedId(isExpanded ? null : p.asset_id)}
                          className="cursor-pointer border-t border-border hover:bg-muted/20"
                        >
                          <td className="px-4 py-2 text-muted-foreground">
                            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          </td>
                          <td className="px-4 py-2 font-medium">{p.asset_name}</td>
                          <td className={`px-4 py-2 font-semibold ${probColor(p.predicted_probability)}`}>
                            {(p.predicted_probability * 100).toFixed(1)}%
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="border-t border-border bg-muted/10">
                            <td colSpan={3} className="px-4 py-4">
                              <div className="flex items-center gap-1 mb-2 text-xs font-semibold uppercase text-muted-foreground">
                                <Brain size={12} /> Feature contributions (largest impact first)
                              </div>
                              <ul className="space-y-1">
                                {p.contributions.map((c, i) => (
                                  <li key={i} className="flex items-center justify-between text-sm">
                                    <span className="capitalize text-muted-foreground">{c.feature.replace(/_/g, " ")} (value: {c.value})</span>
                                    <span className={c.contribution > 0 ? "text-danger" : c.contribution < 0 ? "text-success" : "text-muted-foreground"}>
                                      {c.contribution > 0 ? "+" : ""}{c.contribution.toFixed(3)}
                                    </span>
                                  </li>
                                ))}
                              </ul>
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
        </>
      )}
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}
