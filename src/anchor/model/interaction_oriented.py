from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    agent = "agent"
    tool = "tool"
    user = "user"
    system = "system"


class ModelConfig(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    additional_params: Optional[Dict[str, Any]] = None


class ToolSchema(BaseModel):
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


class Entity(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entity_id: UUID = Field(default_factory=uuid4)
    type: EntityType
    name: str
    description: Optional[str] = None
    supervisor_id: Optional[UUID] = None
    model_config_data: Optional[ModelConfig] = Field(default=None, alias="model_config", serialization_alias="model_config")
    tool_schema: Optional[ToolSchema] = None


class CapabilityType(str, Enum):
    tool_access = "tool_access"
    agent_access = "agent_access"
    resource_access = "resource_access"


class Capability(BaseModel):
    capability_id: UUID = Field(default_factory=uuid4)
    owner_entity_id: UUID
    target_entity_id: UUID
    type: CapabilityType
    granted_by: Optional[UUID] = None
    granted_at: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    constraints: Optional[Dict[str, Any]] = None


class IntentionConfidence(str, Enum):
    explicit = "explicit"
    inferred = "inferred"
    assumed = "assumed"
    unknown = "unknown"


class Intention(BaseModel):
    intention_id: UUID = Field(default_factory=uuid4)
    created_by_entity_id: UUID
    goal: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: IntentionConfidence = IntentionConfidence.unknown
    evidence: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WorkflowStatus(str, Enum):
    created = "created"
    running = "running"
    failed = "failed"
    finished = "finished"


class WorkflowDefinition(BaseModel):
    workflow_def_id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None


class WorkflowModelMetrics(BaseModel):
    llm_call_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    prompt_cost_usd: Optional[float] = None
    completion_cost_usd: Optional[float] = None
    total_cost_usd: Optional[float] = None
    models: Optional[Dict[str, int]] = None
    providers: Optional[Dict[str, int]] = None


class WorkflowExecution(BaseModel):
    workflow_exec_id: UUID = Field(default_factory=uuid4)
    workflow_def_id: UUID
    root_interaction_id: Optional[UUID] = None
    goal: Optional[str] = None
    final_output: Optional[Union[Dict[str, Any], str]] = None
    status: WorkflowStatus = WorkflowStatus.created
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    error_message: Optional[str] = None
    aggregated_model_metrics: Optional[WorkflowModelMetrics] = None


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ExecutionMetrics(BaseModel):
    cpu_usage_percent: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    environment_vars: Optional[Dict[str, Any]] = None
    other_stats: Optional[Dict[str, Any]] = None


class TaskExecution(BaseModel):
    task_exec_id: UUID = Field(default_factory=uuid4)
    workflow_exec_id: UUID
    parent_task_exec_id: Optional[UUID] = None
    created_by_entity_id: UUID
    created_by_interaction_id: Optional[UUID] = None
    assigned_to_entity_id: Optional[UUID] = None
    status: TaskStatus = TaskStatus.pending
    input: Optional[Union[Dict[str, Any], str]] = None
    output: Optional[Union[Dict[str, Any], str]] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    metrics: Optional[ExecutionMetrics] = None


class InteractionType(str, Enum):
    delegation = "delegation"
    tool_invocation = "tool_invocation"
    model_invocation = "model_invocation"
    message = "message"
    negotiation = "negotiation"
    reflection = "reflection"
    observation = "observation"


class Interaction(BaseModel):
    interaction_id: UUID = Field(default_factory=uuid4)
    workflow_exec_id: UUID
    source_entity_id: UUID
    target_entity_id: Optional[UUID] = None
    type: InteractionType
    related_task_exec_id: Optional[UUID] = None
    based_on_intention_id: Optional[UUID] = None
    caused_by_interaction_id: Optional[UUID] = None
    payload: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModelMetrics(BaseModel):
    model_name: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: Optional[int] = None
    other_stats: Optional[Dict[str, Any]] = None
