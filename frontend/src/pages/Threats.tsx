import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { threatsApi } from "@/api/entities";
import { SEVERITY_COLOR } from "@/types/entities";

export default function Threats() {
  const { data: threats, isLoading: loadingThreats } = useQuery({ queryKey: ["threats"], queryFn: threatsApi.list });
  const { data: events, isLoading: loadingEvents } = useQuery({ queryKey: ["threat-events"], queryFn: threatsApi.listEvents });

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold">Threat Intelligence</h2>
        <p className="text-sm text-muted-foreground">Threat actors and techniques mapped to MITRE ATT&CK.</p>
      </div>

      {loadingThreats && <p className="text-sm text-muted-foreground">Loading threats...</p>}
      {threats && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Threat</th>
                <th className="px-4 py-2">Actor</th>
                <th className="px-4 py-2">MITRE Technique</th>
                <th className="px-4 py-2">Tactic</th>
                <th className="px-4 py-2">Relevant assets</th>
              </tr>
            </thead>
            <tbody>
              {threats.map((t) => (
                <tr key={t.id} className="border-t border-border">
                  <td className="px-4 py-2 font-medium">{t.name}</td>
                  <td className="px-4 py-2 text-muted-foreground">{t.threat_actor ?? "—"}</td>
                  <td className="px-4 py-2 font-mono text-xs">{t.mitre_technique_id ?? "—"}</td>
                  <td className="px-4 py-2 text-muted-foreground">{t.mitre_tactic ?? "—"}</td>
                  <td className="px-4 py-2 text-muted-foreground">{t.relevant_asset_ids.length} asset(s)</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div>
        <h3 className="text-md font-semibold mb-2">Recent Threat Events</h3>
        {loadingEvents && <p className="text-sm text-muted-foreground">Loading events...</p>}
        {events && (
          <ul className="space-y-2">
            {events.map((e) => (
              <li key={e.id} className="flex items-start gap-3 rounded-lg border border-border bg-muted/20 p-3">
                <AlertTriangle size={16} className={SEVERITY_COLOR[e.severity]} />
                <div>
                  <p className="text-sm">
                    <span className={`font-medium capitalize ${SEVERITY_COLOR[e.severity]}`}>{e.severity}</span>{" "}
                    · {e.event_type.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-muted-foreground">{e.description}</p>
                  <p className="text-xs text-muted-foreground mt-1">{new Date(e.detected_at).toLocaleString()}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
