import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, MinusCircle, XCircle, HelpCircle, Ban } from "lucide-react";
import { complianceApi } from "@/api/entities";
import { useAuth } from "@/hooks/useAuth";
import {
  COMPLIANCE_STATUS_COLOR,
  COMPLIANCE_STATUS_LABEL,
  type ComplianceMapping,
  type ComplianceStatusValue,
} from "@/types/entities";

const WRITE_ROLES = ["admin", "ciso", "compliance_officer"];
const STATUS_OPTIONS: ComplianceStatusValue[] = ["compliant", "partially_compliant", "non_compliant", "not_applicable", "not_assessed"];

const STATUS_ICON: Record<ComplianceStatusValue, JSX.Element> = {
  compliant: <CheckCircle2 size={16} className="text-success" />,
  partially_compliant: <MinusCircle size={16} className="text-warning" />,
  non_compliant: <XCircle size={16} className="text-danger" />,
  not_applicable: <Ban size={16} className="text-muted-foreground" />,
  not_assessed: <HelpCircle size={16} className="text-muted-foreground" />,
};

export default function Compliance() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [selectedFrameworkId, setSelectedFrameworkId] = useState<number | null>(null);

  const { data: frameworks, isLoading: loadingFrameworks } = useQuery({
    queryKey: ["compliance-frameworks"],
    queryFn: complianceApi.listFrameworks,
  });

  const activeFrameworkId = selectedFrameworkId ?? frameworks?.[0]?.id ?? null;

  const { data: gapAnalysis, isLoading: loadingGaps } = useQuery({
    queryKey: ["compliance-gap-analysis", activeFrameworkId],
    queryFn: () => complianceApi.gapAnalysis(activeFrameworkId as number),
    enabled: activeFrameworkId !== null,
  });

  const { data: allMappings, isLoading: loadingMappings } = useQuery({
    queryKey: ["compliance-full-mappings", activeFrameworkId],
    queryFn: () => complianceApi.getFrameworkMappings(activeFrameworkId as number),
    enabled: activeFrameworkId !== null,
  });

  const upsertMutation = useMutation({
    mutationFn: complianceApi.upsertMapping,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance-gap-analysis"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-full-mappings"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-summary"] });
    },
  });

  const canWrite = user && WRITE_ROLES.includes(user.role);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Compliance Mapping</h2>
        <p className="text-sm text-muted-foreground">
          Self-reported mapping against industry frameworks. This is not an official regulatory certification or audit finding.
        </p>
      </div>

      {loadingFrameworks && <p className="text-sm text-muted-foreground">Loading frameworks...</p>}

      {frameworks && (
        <div className="flex flex-wrap gap-2">
          {frameworks.map((f) => (
            <button
              key={f.id}
              onClick={() => setSelectedFrameworkId(f.id)}
              className={`rounded-full px-4 py-1.5 text-sm border ${
                activeFrameworkId === f.id
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:bg-muted/30"
              }`}
            >
              {f.name} <span className="opacity-60">({f.requirement_count})</span>
            </button>
          ))}
        </div>
      )}

      {loadingGaps && <p className="text-sm text-muted-foreground">Loading gap analysis...</p>}

      {gapAnalysis && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <div className="rounded-lg border border-border bg-muted/20 p-4 col-span-2 md:col-span-1">
            <p className="text-xs text-muted-foreground">Compliance score</p>
            <p className="mt-1 text-2xl font-semibold">{gapAnalysis.compliance_score}%</p>
          </div>
          <StatBadge label="Compliant" count={gapAnalysis.compliant_count} color="text-success" />
          <StatBadge label="Partial" count={gapAnalysis.partially_compliant_count} color="text-warning" />
          <StatBadge label="Non-Compliant" count={gapAnalysis.non_compliant_count} color="text-danger" />
          <StatBadge label="Not Assessed" count={gapAnalysis.not_assessed_count} color="text-muted-foreground" />
        </div>
      )}

      {loadingMappings && <p className="text-sm text-muted-foreground">Loading requirements...</p>}

      {allMappings && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Code</th>
                <th className="px-4 py-2">Requirement</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Notes</th>
                <th className="px-4 py-2">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {allMappings.map((m) => (
                <tr key={m.requirement_id} className="border-t border-border align-top">
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{m.requirement.code}</td>
                  <td className="px-4 py-2">
                    <p className="font-medium">{m.requirement.title}</p>
                    {m.requirement.category && <p className="text-xs text-muted-foreground">{m.requirement.category}</p>}
                  </td>
                  <td className="px-4 py-2">
                    {canWrite ? (
                      <select
                        value={m.status}
                        onChange={(e) =>
                          upsertMutation.mutate({
                            requirement_id: m.requirement_id,
                            status: e.target.value as ComplianceStatusValue,
                            notes: m.notes,
                          })
                        }
                        className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>{COMPLIANCE_STATUS_LABEL[s]}</option>
                        ))}
                      </select>
                    ) : (
                      <span className={`flex items-center gap-1 font-medium ${COMPLIANCE_STATUS_COLOR[m.status]}`}>
                        {STATUS_ICON[m.status]} {COMPLIANCE_STATUS_LABEL[m.status]}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-muted-foreground max-w-xs">{m.notes ?? "—"}</td>
                  <td className="px-4 py-2 text-muted-foreground">{m.evidence.length} item(s)</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatBadge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${color}`}>{count}</p>
    </div>
  );
}
