import { apiClient } from "@/api/client";
import type {
  Asset, BudgetWhatIfResponse, ComplianceMapping, ComplianceStatusValue, FrameworkGapAnalysis, ComplianceFramework,
  ComplianceSummary, InvestmentCandidate, MLPredictionsResponse, Recommendation, Risk, RiskSummary, SecurityControl,
  Threat, ThreatEvent, Vulnerability, WhatIfResponse,
} from "@/types/entities";

export const assetsApi = {
  list: () => apiClient.get<Asset[]>("/assets").then((r) => r.data),
  create: (payload: Partial<Asset> & { name: string; asset_type: string }) =>
    apiClient.post<Asset>("/assets", payload).then((r) => r.data),
  remove: (id: number) => apiClient.delete(`/assets/${id}`),
};

export const vulnerabilitiesApi = {
  list: () => apiClient.get<Vulnerability[]>("/vulnerabilities").then((r) => r.data),
  create: (payload: {
    title: string; cve_id?: string | null; cvss_score: number;
    exploitability: string; status: string; affected_asset_ids: number[];
  }) => apiClient.post<Vulnerability>("/vulnerabilities", payload).then((r) => r.data),
  remove: (id: number) => apiClient.delete(`/vulnerabilities/${id}`),
};

export const threatsApi = {
  list: () => apiClient.get<Threat[]>("/threats").then((r) => r.data),
  listEvents: () => apiClient.get<ThreatEvent[]>("/threats/events").then((r) => r.data),
};

export const controlsApi = {
  list: () => apiClient.get<SecurityControl[]>("/controls").then((r) => r.data),
};

export const risksApi = {
  list: () => apiClient.get<Risk[]>("/risks").then((r) => r.data),
  summary: () => apiClient.get<RiskSummary>("/financial-risk/summary").then((r) => r.data),
  recalculateAll: () => apiClient.post<Risk[]>("/risks/recalculate").then((r) => r.data),
};

export const complianceApi = {
  listFrameworks: () => apiClient.get<ComplianceFramework[]>("/compliance/frameworks").then((r) => r.data),
  getFrameworkMappings: (frameworkId: number) =>
    apiClient.get<ComplianceMapping[]>(`/compliance/frameworks/${frameworkId}/mappings`).then((r) => r.data),
  gapAnalysis: (frameworkId: number) =>
    apiClient.get<FrameworkGapAnalysis>(`/compliance/frameworks/${frameworkId}/gap-analysis`).then((r) => r.data),
  summary: () => apiClient.get<ComplianceSummary>("/compliance/summary").then((r) => r.data),
  upsertMapping: (payload: { requirement_id: number; status: ComplianceStatusValue; control_id?: number | null; notes?: string | null }) =>
    apiClient.post<ComplianceMapping>("/compliance/mappings", payload).then((r) => r.data),
  addEvidence: (mappingId: number, payload: { description: string; url?: string | null }) =>
    apiClient.post(`/compliance/mappings/${mappingId}/evidence`, payload).then((r) => r.data),
};

export const optimizationApi = {
  listInvestments: () => apiClient.get<InvestmentCandidate[]>("/investments").then((r) => r.data),
  recommend: (budget?: number) =>
    apiClient.post<Recommendation>("/optimization/recommend", budget !== undefined ? { budget } : {}).then((r) => r.data),
  history: () => apiClient.get<Recommendation[]>("/optimization/recommendations").then((r) => r.data),
};

export interface WhatIfPayload {
  scenario_type: "add_control" | "remove_control" | "fix_vulnerability" | "improve_control_effectiveness" | "increase_budget";
  control_id?: number;
  asset_ids?: number[];
  vulnerability_id?: number;
  new_effectiveness?: number;
  new_budget?: number;
  old_budget?: number;
}

export const whatIfApi = {
  simulate: (payload: WhatIfPayload) =>
    apiClient.post<WhatIfResponse | BudgetWhatIfResponse>("/what-if/simulate", payload).then((r) => r.data),
};

export const mlApi = {
  predictions: (assetId?: number) =>
    apiClient.get<MLPredictionsResponse>("/ml/predictions", { params: assetId ? { asset_id: assetId } : {} }).then((r) => r.data),
};
