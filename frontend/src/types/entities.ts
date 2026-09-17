export type BusinessCriticality = "low" | "medium" | "high" | "critical";
export type Severity = "low" | "medium" | "high" | "critical";
export type Exploitability = "theoretical" | "proof_of_concept" | "functional" | "actively_exploited";
export type VulnerabilityStatus = "open" | "mitigated" | "accepted_risk" | "false_positive";
export type ControlType =
  | "mfa" | "edr" | "firewall" | "backup" | "patch_management" | "iam" | "monitoring" | "incident_response" | "other";

export interface Asset {
  id: number;
  organization_id: number;
  name: string;
  asset_type: string;
  description: string | null;
  business_criticality: BusinessCriticality;
  business_value: number;
  internet_exposure: boolean;
  depends_on_ids: number[];
}

export interface Vulnerability {
  id: number;
  organization_id: number;
  cve_id: string | null;
  title: string;
  description: string | null;
  cvss_score: number;
  severity: Severity;
  exploitability: Exploitability;
  status: VulnerabilityStatus;
  published_date: string | null;
  affected_asset_ids: number[];
}

export interface Threat {
  id: number;
  organization_id: number;
  name: string;
  threat_actor: string | null;
  mitre_technique_id: string | null;
  mitre_tactic: string | null;
  description: string | null;
  relevant_asset_ids: number[];
}

export interface ThreatEvent {
  id: number;
  organization_id: number;
  threat_id: number;
  asset_id: number | null;
  event_type: string;
  severity: Severity;
  description: string | null;
  detected_at: string;
}

export interface SecurityControl {
  id: number;
  organization_id: number;
  name: string;
  control_type: ControlType;
  description: string | null;
  annual_cost: number;
  effectiveness_score: number;
  is_active: boolean;
  protected_asset_ids: number[];
}

export interface RiskDriver {
  factor: string;
  impact_pct: number;
}

export interface FinancialImpact {
  business_interruption: number;
  data_loss: number;
  recovery_cost: number;
  incident_response: number;
  legal_regulatory: number;
  revenue_impact: number;
  other_cost: number;
  total_impact: number;
}

export interface RiskScenario {
  id: number;
  name: string;
  likelihood: number;
  expected_annual_loss: number;
  value_at_risk: number;
  confidence_level: number;
}

export interface Risk {
  id: number;
  organization_id: number;
  asset_id: number;
  calculated_at: string;
  likelihood: number;
  risk_score: number;
  primary_vulnerability_id: number | null;
  expected_annual_loss: number;
  financial_impact_given_incident: number;
  risk_drivers: RiskDriver[];
  financial_impact: FinancialImpact | null;
  scenarios: RiskScenario[];
}

export interface RiskSummary {
  total_expected_annual_loss: number;
  total_value_at_risk: number;
  total_financial_exposure: number;
  asset_count: number;
  critical_risk_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  top_risks: Risk[];
}

export interface ComplianceRequirement {
  id: number;
  framework_id: number;
  code: string;
  category: string | null;
  title: string;
  description: string | null;
}

export interface ComplianceFramework {
  id: number;
  name: string;
  short_code: string;
  version: string | null;
  description: string | null;
  requirement_count: number;
}

export interface Evidence {
  id: number;
  description: string;
  url: string | null;
  uploaded_at: string;
  uploaded_by_user_id: number | null;
}

export type ComplianceStatusValue = "compliant" | "partially_compliant" | "non_compliant" | "not_applicable" | "not_assessed";

export interface ComplianceMapping {
  id: number | null;
  organization_id: number;
  requirement_id: number;
  control_id: number | null;
  status: ComplianceStatusValue;
  notes: string | null;
  requirement: ComplianceRequirement;
  evidence: Evidence[];
}

export interface FrameworkGapAnalysis {
  framework: ComplianceFramework;
  compliance_score: number;
  compliant_count: number;
  partially_compliant_count: number;
  non_compliant_count: number;
  not_applicable_count: number;
  not_assessed_count: number;
  gaps: ComplianceMapping[];
}

export interface ComplianceSummary {
  overall_score: number;
  frameworks: FrameworkGapAnalysis[];
}

export const COMPLIANCE_STATUS_COLOR: Record<ComplianceStatusValue, string> = {
  compliant: "text-success",
  partially_compliant: "text-warning",
  non_compliant: "text-danger",
  not_applicable: "text-muted-foreground",
  not_assessed: "text-muted-foreground",
};

export const COMPLIANCE_STATUS_LABEL: Record<ComplianceStatusValue, string> = {
  compliant: "Compliant",
  partially_compliant: "Partially Compliant",
  non_compliant: "Non-Compliant",
  not_applicable: "Not Applicable",
  not_assessed: "Not Assessed",
};

export interface InvestmentCandidate {
  id: number;
  organization_id: number;
  control_id: number;
  estimated_annual_cost: number;
  estimated_risk_reduction: number;
  calculated_at: string;
  control_name: string;
  control_type: string;
}

export interface Recommendation {
  id: number;
  organization_id: number;
  budget: number;
  baseline_total_eal: number;
  total_investment: number;
  total_risk_reduction: number;
  remaining_risk: number;
  rosi_percent: number;
  created_at: string;
  selected_investments: InvestmentCandidate[];
}

export interface WhatIfAssetSnapshot {
  asset_id: number;
  asset_name: string;
  risk_score: number;
  likelihood: number;
  expected_annual_loss: number;
}

export interface WhatIfResponse {
  scenario_type: string;
  description: string;
  before: WhatIfAssetSnapshot[];
  after: WhatIfAssetSnapshot[];
  total_eal_before: number;
  total_eal_after: number;
  eal_change: number;
  investment_change: number;
  rosi_percent: number | null;
  affected_asset_ids: number[];
}

export interface BudgetWhatIfResponse {
  scenario_type: "increase_budget";
  description: string;
  old_budget: number;
  new_budget: number;
  old_total_investment: number;
  new_total_investment: number;
  old_risk_reduction: number;
  new_risk_reduction: number;
  additional_risk_reduction: number;
  newly_affordable_controls: string[];
}

export interface MLFeatureContribution {
  feature: string;
  value: number;
  contribution: number;
}

export interface MLAssetPrediction {
  asset_id: number;
  asset_name: string;
  predicted_probability: number;
  contributions: MLFeatureContribution[];
}

export interface MLModelInfo {
  model_type: string;
  is_synthetic_data: boolean;
  training_samples: number;
  test_accuracy: number;
  test_roc_auc: number;
  coefficients: Record<string, number>;
  caveat: string;
}

export interface MLPredictionsResponse {
  model_info: MLModelInfo;
  predictions: MLAssetPrediction[];
}

export const CRITICALITY_COLOR: Record<BusinessCriticality, string> = {
  low: "text-muted-foreground",
  medium: "text-warning",
  high: "text-warning",
  critical: "text-danger",
};

export const SEVERITY_COLOR: Record<Severity, string> = {
  low: "text-muted-foreground",
  medium: "text-warning",
  high: "text-warning",
  critical: "text-danger",
};
