import enum


class BusinessCriticality(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Exploitability(str, enum.Enum):
    THEORETICAL = "theoretical"
    PROOF_OF_CONCEPT = "proof_of_concept"
    FUNCTIONAL = "functional"
    ACTIVELY_EXPLOITED = "actively_exploited"


class VulnerabilityStatus(str, enum.Enum):
    OPEN = "open"
    MITIGATED = "mitigated"
    ACCEPTED_RISK = "accepted_risk"
    FALSE_POSITIVE = "false_positive"


class ControlType(str, enum.Enum):
    MFA = "mfa"
    EDR = "edr"
    FIREWALL = "firewall"
    BACKUP = "backup"
    PATCH_MANAGEMENT = "patch_management"
    IAM = "iam"
    MONITORING = "monitoring"
    INCIDENT_RESPONSE = "incident_response"
    OTHER = "other"
