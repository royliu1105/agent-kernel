"""SQLAlchemy storage models for the execution lifecycle."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kernel_core import AgentStatus, RunEventType, RunStatus, RunStepStatus, RunStepType, utc_now
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel_storage.base import Base


class AgentRecord(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=AgentStatus.ACTIVE.value
    )
    prompt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    default_model_policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    memory_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    tool_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    runs: Mapped[list[RunRecord]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default=RunStatus.CREATED.value)
    input_payload: Mapped[dict[str, Any]] = mapped_column(
        "input", JSON, nullable=False, default=dict
    )
    output_payload: Mapped[dict[str, Any] | None] = mapped_column("output", JSON, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    input_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    agent: Mapped[AgentRecord] = relationship(back_populates="runs")
    steps: Mapped[list[RunStepRecord]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    events: Mapped[list[RunEventRecord]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunEventRecord.sequence"
    )


class RunStepRecord(Base):
    __tablename__ = "run_steps"
    __table_args__ = (Index("ix_run_steps_run_id_index", "run_id", "index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(
        String(64), nullable=False, default=RunStepType.MODEL_CALL.value
    )
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=RunStepStatus.CREATED.value
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(
        "input", JSON, nullable=False, default=dict
    )
    output_payload: Mapped[dict[str, Any] | None] = mapped_column("output", JSON, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    span_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    run: Mapped[RunRecord] = relationship(back_populates="steps")


class RunEventRecord(Base):
    __tablename__ = "run_events"
    __table_args__ = (Index("ix_run_events_run_id_sequence", "run_id", "sequence", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(
        String(64), nullable=False, default=RunEventType.RUN_CREATED.value
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    run: Mapped[RunRecord] = relationship(back_populates="events")
