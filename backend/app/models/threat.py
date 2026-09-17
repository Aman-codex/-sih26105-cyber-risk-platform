from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import Severity

# How relevant a threat (actor / technique) is to a specific asset —
# e.g. "APT-Kestrel using T1190 (Exploit Public-Facing Application)" is
# highly relevant to an internet-exposed web app, less so to an air-gapped
# internal tool. Feeds "threat exposure" in the Risk Engine (Phase 3).
threat_asset_relevance = Table(
    "threat_asset_relevance",
    Base.metadata,
    Column("threat_id", Integer, ForeignKey("threats.id"), primary_key=True),
    Column("asset_id", Integer, ForeignKey("assets.id"), primary_key=True),
    Column("relevance_score", Float, nullable=False, default=0.5),  # 0.0 - 1.0
)


class Threat(Base, TimestampMixin):
    """
    A threat actor / campaign / technique, ideally mapped to MITRE ATT&CK.
    """
    __tablename__ = "threats"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "APT-Kestrel"
    threat_actor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mitre_technique_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g. "T1190"
    mitre_tactic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g. "Initial Access"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    relevant_assets: Mapped[list["Asset"]] = relationship(  # noqa: F821
        "Asset", secondary=threat_asset_relevance, backref="relevant_threats"
    )


class ThreatEvent(Base, TimestampMixin):
    """
    A concrete, timestamped occurrence of a threat (an alert, an intel
    report of active exploitation, an actual incident). This is the
    trigger that drives "Continuous Recalculation" in later phases.
    """
    __tablename__ = "threat_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    threat_id: Mapped[int] = mapped_column(ForeignKey("threats.id"), nullable=False)
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id"), nullable=True)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "active_exploitation_detected"
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="threat_event_severity"), nullable=False, default=Severity.MEDIUM)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    threat: Mapped["Threat"] = relationship()
    asset: Mapped[Optional["Asset"]] = relationship()  # noqa: F821
