from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SRID = 32643
EMBED_DIM = 1024


class Base(DeclarativeBase):
    pass


class Role(enum.StrEnum):
    officer = "officer"
    reviewer = "reviewer"
    admin = "admin"


class Zone(enum.StrEnum):
    core = "core"
    buffer = "buffer"
    outside = "outside"


class ChangeType(enum.StrEnum):
    NEW_CONSTRUCTION = "NEW_CONSTRUCTION"
    VERTICAL_ADDITION = "VERTICAL_ADDITION"
    DEMOLITION = "DEMOLITION"
    FACADE_ALTERATION = "FACADE_ALTERATION"


class ChangeStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    escalated = "escalated"
    dropped = "dropped"
    needs_human_rewrite = "needs_human_rewrite"


class Severity(enum.StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class Decision(enum.StrEnum):
    approve = "approve"
    reject = "reject"
    escalate = "escalate"


class VisitStatus(enum.StrEnum):
    scheduled = "scheduled"
    done = "done"
    cancelled = "cancelled"


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Officer(Base):
    __tablename__ = "officers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"))
    display_name: Mapped[str] = mapped_column(String(128))
    locale: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running")
    epoch_before: Mapped[date] = mapped_column(Date)
    epoch_after: Mapped[date] = mapped_column(Date)
    git_sha: Mapped[str] = mapped_column(String(40))
    config_hash: Mapped[str] = mapped_column(String(64))
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class Tile(Base):
    __tablename__ = "tiles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    geom: Mapped[object] = mapped_column(Geometry("POLYGON", srid=SRID))
    centroid_lon: Mapped[float] = mapped_column(Float)
    centroid_lat: Mapped[float] = mapped_column(Float)
    zone: Mapped[Zone] = mapped_column(Enum(Zone, name="zone"))
    chowkri_id: Mapped[str | None] = mapped_column(String(32))
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    residual_px: Mapped[float | None] = mapped_column(Float)
    season_mismatch: Mapped[bool] = mapped_column(Boolean, default=False)


class Building(Base):
    """Synthetic building identity. Never linked to ownership, tax, or occupancy."""

    __tablename__ = "buildings"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    footprint: Mapped[object] = mapped_column(Geometry("POLYGON", srid=SRID))
    zone: Mapped[Zone] = mapped_column(Enum(Zone, name="zone"))
    chowkri_id: Mapped[str | None] = mapped_column(String(32))
    source_ref: Mapped[str] = mapped_column(String(64))


class Change(Base):
    __tablename__ = "changes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"))
    tile_id: Mapped[str] = mapped_column(ForeignKey("tiles.id"))
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"))
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=SRID))
    zone: Mapped[Zone] = mapped_column(Enum(Zone, name="zone"))
    chowkri_id: Mapped[str | None] = mapped_column(String(32))
    epoch_before: Mapped[date] = mapped_column(Date)
    epoch_after: Mapped[date] = mapped_column(Date)
    change_prob: Mapped[float] = mapped_column(Float)
    calibration_date: Mapped[date | None] = mapped_column(Date)
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType, name="change_type"))
    facade_class: Mapped[str | None] = mapped_column(String(32))
    before_uri: Mapped[str] = mapped_column(String(512))
    after_uri: Mapped[str] = mapped_column(String(512))
    mask_uri: Mapped[str] = mapped_column(String(512))
    triage_decision: Mapped[str | None] = mapped_column(String(32))
    triage_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ChangeStatus] = mapped_column(
        Enum(ChangeStatus, name="change_status"), default=ChangeStatus.pending
    )
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    verifier_verdict: Mapped[str | None] = mapped_column(String(8))
    verifier_notes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Clause(Base):
    __tablename__ = "clauses"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    regulation: Mapped[str] = mapped_column(String(256))
    section: Mapped[str] = mapped_column(String(32))
    clause: Mapped[str] = mapped_column(String(32))
    path: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    applies_to_zone: Mapped[list[str]] = mapped_column(ARRAY(String(16)))
    applies_to_change_type: Mapped[list[str]] = mapped_column(ARRAY(String(32)))
    source_page: Mapped[int] = mapped_column(Integer)
    source_doc_sha256: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM))


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    change_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("changes.id"))
    claim: Mapped[str] = mapped_column(Text)
    clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id"))
    evidence_ref: Mapped[str] = mapped_column(String(512))
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)


class OfficerDecision(Base):
    __tablename__ = "decisions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    change_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("changes.id"))
    officer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("officers.id"))
    decision: Mapped[Decision] = mapped_column(Enum(Decision, name="decision"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Append-only. A database trigger rejects UPDATE and DELETE (see migration)."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    change_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    git_sha: Mapped[str | None] = mapped_column(String(40))
    model_ids: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    prompt_versions: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    officer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("officers.id"))
    kind: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text)
    change_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("changes.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SiteVisit(Base):
    __tablename__ = "site_visits"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    change_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("changes.id"))
    scheduled_for: Mapped[date] = mapped_column(Date)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("officers.id"))
    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus, name="visit_status"), default=VisitStatus.scheduled
    )
    field_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
