from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, Iterable, List, Mapping, Optional
from uuid import NAMESPACE_OID, UUID, uuid5

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor

from anchor.telemetry.persistence.tinydb import (
    capability_table,
    entity_table,
    intention_table,
    interaction_table,
    task_exec_table,
    update,
    workflow_def_table,
    workflow_exec_table,
)
from anchor.model.interaction_oriented import (
    Capability,
    CapabilityType,
    Entity,
    EntityType,
    ExecutionMetrics,
    Intention,
    IntentionConfidence,
    Interaction,
    InteractionType,
    ModelConfig,
    ModelMetrics,
    TaskExecution,
    TaskStatus,
    ToolSchema,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowModelMetrics,
    WorkflowStatus,
)


class ISpanCollector(SpanProcessor):
    pass


def _ns_to_datetime(timestamp_ns: Optional[int]) -> Optional[datetime]:
    if timestamp_ns is None:
        return None
    return datetime.fromtimestamp(timestamp_ns / 1e9, tz=timezone.utc)


def _status_ok(span: ReadableSpan) -> bool:
    status = getattr(span, "status", None)
    code = getattr(status, "status_code", status)
    if code is None:
        return True
    return str(code).upper().endswith("OK")


def _span_attributes(span: ReadableSpan) -> Mapping[str, Any]:
    attrs = getattr(span, "attributes", None)
    if attrs is None:
        return {}
    return attrs


def _attr_from_mapping(attrs: Mapping[str, Any], key: str) -> Any:
    if key in attrs:
        return attrs[key]

    current: Any = attrs
    for part in key.split("."):
        if isinstance(current, Mapping):
            if part not in current:
                return None
            current = current[part]
            continue
        current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _span_attr(span: ReadableSpan, key: str, default: Any = None) -> Any:
    value = _attr_from_mapping(_span_attributes(span), key)
    return default if value is None else value


def _resource_attr(span: ReadableSpan, key: str, default: Any = None) -> Any:
    resource = getattr(span, "resource", None)
    attrs = getattr(resource, "attributes", None)
    if attrs is None:
        return default
    value = _attr_from_mapping(attrs, key)
    return default if value is None else value


def _parse_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    candidate = value.strip()
    if not candidate or candidate[0] not in "{[":
        return value
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _extract_typed_value(span: ReadableSpan, value_key: str, mime_key: Optional[str] = None) -> Any:
    value = _span_attr(span, value_key)
    if value is None:
        return None

    mime_type = _span_attr(span, mime_key) if mime_key else None
    if mime_type == "application/json":
        value = _parse_json_string(value)
    else:
        value = _parse_json_string(value)

    return _jsonable(value)


def _extract_input(span: ReadableSpan) -> Any:
    for key, mime_key in (
        ("input.value", "input.mime_type"),
        ("input", None),
        ("llm.input_messages", None),
        ("message.input", None),
    ):
        value = _extract_typed_value(span, key, mime_key)
        if value is not None:
            return value
    return None


def _extract_output(span: ReadableSpan) -> Any:
    for key, mime_key in (
        ("output.value", "output.mime_type"),
        ("output", None),
        ("llm.output_messages", None),
        ("message.output", None),
    ):
        value = _extract_typed_value(span, key, mime_key)
        if value is not None:
            return value
    return None


def _to_compact_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in (
            "input",
            "task",
            "thoughts",
            "response",
            "output",
            "goal",
            "content",
            "text",
            "delta",
        ):
            compact = _to_compact_text(value.get(key))
            if compact:
                return compact
        return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True)
    if isinstance(value, list):
        texts = [_to_compact_text(item) for item in value]
        texts = [text for text in texts if text]
        return "\n".join(texts) if texts else None
    return str(value)


def _extract_workflow_goal(span: ReadableSpan) -> Optional[str]:
    return _to_compact_text(_extract_input(span))


def _extract_explicit_reasoning(span: ReadableSpan) -> Optional[str]:
    if _span_attr(span, "tool.name") == "think":
        input_value = _extract_input(span)
        return _to_compact_text(input_value)

    for key in (
        "metadata.reasoning",
        "metadata.thoughts",
        "reasoning",
        "thoughts",
    ):
        compact = _to_compact_text(_span_attr(span, key))
        if compact:
            return compact

    return None


def _extract_tool_schema(span: ReadableSpan) -> Optional[ToolSchema]:
    input_schema = _parse_json_string(_span_attr(span, "tool.parameters"))
    if input_schema is None:
        input_schema = _parse_json_string(_span_attr(span, "tool.json_schema"))
    output_schema = _parse_json_string(_span_attr(span, "tool.output_schema"))
    if input_schema is None and output_schema is None:
        return None
    return ToolSchema(
        input_schema=_jsonable(input_schema),
        output_schema=_jsonable(output_schema),
    )


def _iter_tools_in_value(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        tools = value.get("tools")
        if isinstance(tools, list):
            for tool in tools:
                if isinstance(tool, Mapping):
                    yield tool
        for child in value.values():
            yield from _iter_tools_in_value(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_tools_in_value(item)


def _extract_declared_capability_specs(span: ReadableSpan) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []

    input_value = _extract_input(span)
    for tool in _iter_tools_in_value(input_value):
        name = tool.get("name")
        if not name:
            continue
        input_schema = tool.get("input_schema") or tool.get("parameters")
        specs.append(
            {
                "name": str(name),
                "capability_type": CapabilityType.tool_access,
                "description": tool.get("description"),
                "tool_schema": ToolSchema(
                    input_schema=_jsonable(input_schema) if input_schema is not None else None,
                    output_schema=None,
                ) if input_schema is not None else None,
            }
        )

    invocation_params = _parse_json_string(_span_attr(span, "llm.invocation_parameters"))
    if not isinstance(invocation_params, Mapping):
        return specs

    any_of = (
        invocation_params.get("response_format", {})
        .get("json_schema", {})
        .get("schema", {})
        .get("anyOf", [])
    )
    if not isinstance(any_of, list):
        return specs

    for item in any_of:
        if not isinstance(item, Mapping):
            continue
        properties = item.get("properties")
        if not isinstance(properties, Mapping):
            continue

        name_prop = properties.get("name")
        parameters_prop = properties.get("parameters")
        if not isinstance(name_prop, Mapping):
            continue

        name = name_prop.get("const") or item.get("title")
        if not name:
            continue

        parameters_title = parameters_prop.get("title") if isinstance(parameters_prop, Mapping) else None
        capability_type = (
            CapabilityType.agent_access
            if parameters_title == "HandoffSchema"
            else CapabilityType.tool_access
        )
        description = (
            item.get("description")
            or name_prop.get("description")
            or (parameters_prop.get("description") if isinstance(parameters_prop, Mapping) else None)
        )
        tool_schema = None
        if capability_type == CapabilityType.tool_access and isinstance(parameters_prop, Mapping):
            tool_schema = ToolSchema(
                input_schema=_jsonable(parameters_prop),
                output_schema=None,
            )

        specs.append(
            {
                "name": str(name),
                "capability_type": capability_type,
                "description": description,
                "tool_schema": tool_schema,
            }
        )

    return specs


def _extract_model_config(span: ReadableSpan) -> Optional[ModelConfig]:
    invocation_params = _parse_json_string(_span_attr(span, "llm.invocation_parameters"))
    if not isinstance(invocation_params, Mapping):
        invocation_params = {}

    provider = _span_attr(span, "llm.provider")
    model_name = _span_attr(span, "llm.model_name")
    temperature = _span_attr(span, "llm.temperature")
    if temperature is None:
        temperature = invocation_params.get("temperature")
    max_tokens = _span_attr(span, "llm.max_tokens")
    tool_choice = invocation_params.get("tool_choice")
    additional_params = {"tool_choice": tool_choice} if tool_choice is not None else None
    if all(value is None for value in (provider, model_name, temperature, max_tokens, additional_params)):
        return None
    return ModelConfig(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        additional_params=additional_params,
    )


def _extract_model_metrics(span: ReadableSpan) -> Optional[ModelMetrics]:
    model_name = _span_attr(span, "llm.model_name")
    provider = _span_attr(span, "llm.provider")
    prompt_tokens = _span_attr(span, "llm.token_count.prompt")
    completion_tokens = _span_attr(span, "llm.token_count.completion")
    total_tokens = _span_attr(span, "llm.token_count.total")

    if any(value is None for value in (model_name, provider, prompt_tokens, completion_tokens, total_tokens)):
        return None

    latency_ms = None
    start_time = getattr(span, "start_time", None)
    end_time = getattr(span, "end_time", None)
    if start_time is not None and end_time is not None:
        latency_ms = int((end_time - start_time) / 1_000_000)

    other_stats = {
        "llm_system": _span_attr(span, "llm.system"),
        "prompt_cost_usd": _span_attr(span, "llm.cost.prompt"),
        "completion_cost_usd": _span_attr(span, "llm.cost.completion"),
        "total_cost_usd": _span_attr(span, "llm.cost.total"),
        "invocation_parameters": _parse_json_string(_span_attr(span, "llm.invocation_parameters")),
    }

    return ModelMetrics(
        model_name=model_name,
        provider=provider,
        prompt_tokens=int(prompt_tokens),
        completion_tokens=int(completion_tokens),
        total_tokens=int(total_tokens),
        latency_ms=latency_ms,
        other_stats={k: _jsonable(v) for k, v in other_stats.items() if v is not None},
    )


def _is_handoff_tool_span(span: ReadableSpan) -> bool:
    kind = str(_span_attr(span, "openinference.span.kind", "")).upper()
    if kind != "TOOL":
        return False
    if _span_attr(span, "metadata.class_name") == "HandoffTool":
        return True
    schema = _parse_json_string(_span_attr(span, "tool.json_schema"))
    return isinstance(schema, Mapping) and schema.get("title") == "HandoffSchema"


def _is_internal_beeai_agent_lifecycle_span(span: ReadableSpan) -> bool:
    kind = str(_span_attr(span, "openinference.span.kind", "")).upper()
    if kind != "AGENT":
        return False
    if _span_attr(span, "agent.name"):
        return False
    metadata_path = _span_attr(span, "metadata.path")
    return metadata_path in {
        "agent.requirement.requirement.init",
        "agent.requirement.final_answer",
    }


def _infer_interaction_type(span: ReadableSpan) -> Optional[InteractionType]:
    kind = str(_span_attr(span, "openinference.span.kind", "")).upper()
    if kind == "TOOL":
        return InteractionType.tool_invocation
    if kind == "LLM":
        return InteractionType.model_invocation
    return None


def _task_status(span: ReadableSpan) -> TaskStatus:
    return TaskStatus.completed if _status_ok(span) else TaskStatus.failed


def _workflow_status(root_span: ReadableSpan) -> WorkflowStatus:
    return WorkflowStatus.finished if _status_ok(root_span) else WorkflowStatus.failed


def _aggregate_workflow_model_metrics(spans: Iterable[ReadableSpan]) -> Optional[WorkflowModelMetrics]:
    llm_metrics = [_extract_model_metrics(span) for span in spans]
    llm_metrics = [metrics for metrics in llm_metrics if metrics is not None]
    if not llm_metrics:
        return None

    prompt_cost = 0.0
    completion_cost = 0.0
    total_cost = 0.0
    has_prompt_cost = False
    has_completion_cost = False
    has_total_cost = False
    models: Dict[str, int] = defaultdict(int)
    providers: Dict[str, int] = defaultdict(int)

    for metrics in llm_metrics:
        models[metrics.model_name] += 1
        providers[metrics.provider] += 1
        other_stats = metrics.other_stats or {}
        if other_stats.get("prompt_cost_usd") is not None:
            prompt_cost += float(other_stats["prompt_cost_usd"])
            has_prompt_cost = True
        if other_stats.get("completion_cost_usd") is not None:
            completion_cost += float(other_stats["completion_cost_usd"])
            has_completion_cost = True
        if other_stats.get("total_cost_usd") is not None:
            total_cost += float(other_stats["total_cost_usd"])
            has_total_cost = True

    return WorkflowModelMetrics(
        llm_call_count=len(llm_metrics),
        prompt_tokens=sum(metrics.prompt_tokens for metrics in llm_metrics),
        completion_tokens=sum(metrics.completion_tokens for metrics in llm_metrics),
        total_tokens=sum(metrics.total_tokens for metrics in llm_metrics),
        prompt_cost_usd=prompt_cost if has_prompt_cost else None,
        completion_cost_usd=completion_cost if has_completion_cost else None,
        total_cost_usd=total_cost if has_total_cost else None,
        models=dict(models),
        providers=dict(providers),
    )


def _extract_span_events(span: ReadableSpan) -> List[Dict[str, Any]]:
    events_payload: List[Dict[str, Any]] = []
    for event in getattr(span, "events", []) or []:
        events_payload.append(
            {
                "name": getattr(event, "name", None),
                "timestamp": (
                    _ns_to_datetime(getattr(event, "timestamp", None)).isoformat()
                    if getattr(event, "timestamp", None) is not None
                    else None
                ),
                "attributes": _jsonable(dict(getattr(event, "attributes", {}) or {})),
            }
        )
    return events_payload


def _extract_agent_execution_payload(span: Optional[ReadableSpan]) -> Optional[Dict[str, Any]]:
    if span is None:
        return None

    payload: Dict[str, Any] = {
        "span_name": span.name,
        "agent_name": _span_attr(span, "agent.name") or _span_attr(span, "session.name") or span.name,
    }

    input_value = _extract_input(span)
    output_value = _extract_output(span)
    if input_value is not None:
        payload["input"] = input_value
        compact_input = _to_compact_text(input_value)
        if compact_input:
            payload["input_text"] = compact_input
    if output_value is not None:
        payload["output"] = output_value
        compact_output = _to_compact_text(output_value)
        if compact_output:
            payload["output_text"] = compact_output

    events = _extract_span_events(span)
    if events:
        payload["events"] = events

    return payload


@dataclass
class TraceSemanticBundle:
    workflow_definition: WorkflowDefinition
    workflow_execution: WorkflowExecution
    entities: List[Entity] = field(default_factory=list)
    capabilities: List[Capability] = field(default_factory=list)
    intentions: List[Intention] = field(default_factory=list)
    tasks: List[TaskExecution] = field(default_factory=list)
    interactions: List[Interaction] = field(default_factory=list)


class SpanBuffer:
    def __init__(self) -> None:
        self.traces: Dict[int, List[ReadableSpan]] = defaultdict(list)
        self.spans: List[ReadableSpan] = []

    def add(self, span: ReadableSpan) -> None:
        self.traces[span.context.trace_id].append(span)
        self.spans.append(span)

    def pop_trace(self, trace_id: int) -> List[ReadableSpan]:
        return self.traces.pop(trace_id, [])

    def trace_ids(self) -> List[int]:
        return list(self.traces.keys())


class TracePersistence:
    def persist(self, bundle: TraceSemanticBundle) -> None:
        update(workflow_def_table, bundle.workflow_definition, "workflow_def_id")
        update(workflow_exec_table, bundle.workflow_execution, "workflow_exec_id")

        for entity in bundle.entities:
            update(entity_table, entity, "entity_id")

        for capability in bundle.capabilities:
            update(capability_table, capability, "capability_id")

        for intention in bundle.intentions:
            update(intention_table, intention, "intention_id")

        for task in bundle.tasks:
            update(task_exec_table, task, "task_exec_id")

        for interaction in bundle.interactions:
            update(interaction_table, interaction, "interaction_id")


class SpanTranslator:
    def __init__(self) -> None:
        self.system_entity = Entity(
            entity_id=uuid5(NAMESPACE_OID, "entity:system:openinference"),
            type=EntityType.system,
            name="OpenInference System",
            description="Synthetic orchestration entity derived from OpenInference spans.",
        )
        self.user_entity = Entity(
            entity_id=uuid5(NAMESPACE_OID, "entity:user:workflow-owner"),
            type=EntityType.user,
            name="Workflow User",
            description="Synthetic workflow owner entity inferred from the root input span.",
        )
        self.entity_registry: Dict[UUID, Entity] = {
            self.system_entity.entity_id: self.system_entity,
            self.user_entity.entity_id: self.user_entity,
        }

    def translate_trace(self, spans: Iterable[ReadableSpan]) -> Optional[TraceSemanticBundle]:
        ordered_spans = sorted(spans, key=lambda span: (span.start_time or 0, span.end_time or 0))
        if not ordered_spans:
            return None

        root_span = next((span for span in ordered_spans if span.parent is None), ordered_spans[0])
        trace_id = root_span.context.trace_id
        workflow_exec_id = uuid5(NAMESPACE_OID, f"trace:{trace_id}")
        root_output = _extract_output(root_span)

        service_name = _resource_attr(root_span, "service.name") or _span_attr(root_span, "session.name") or "openinference-trace"
        workflow_def = WorkflowDefinition(
            workflow_def_id=uuid5(NAMESPACE_OID, f"workflow-definition:{service_name}"),
            name=str(service_name),
            description=f"Workflow inferred from OpenInference trace {trace_id}.",
        )

        workflow_exec = WorkflowExecution(
            workflow_exec_id=workflow_exec_id,
            workflow_def_id=workflow_def.workflow_def_id,
            goal=_extract_workflow_goal(root_span),
            final_output=root_output,
            status=_workflow_status(root_span),
            started_at=_ns_to_datetime(root_span.start_time) or datetime.now(timezone.utc),
            ended_at=_ns_to_datetime(root_span.end_time),
            error_message=None if _status_ok(root_span) else getattr(root_span.status, "description", None),
            aggregated_model_metrics=_aggregate_workflow_model_metrics(ordered_spans),
        )

        bundle = TraceSemanticBundle(
            workflow_definition=workflow_def,
            workflow_execution=workflow_exec,
            entities=[self.system_entity, self.user_entity],
        )
        children_by_parent_id: Dict[Optional[int], List[ReadableSpan]] = defaultdict(list)
        for span in ordered_spans:
            parent_span_id = getattr(getattr(span, "parent", None), "span_id", None)
            children_by_parent_id[parent_span_id].append(span)
        span_by_id: Dict[int, ReadableSpan] = {span.context.span_id: span for span in ordered_spans}

        span_interaction_ids: Dict[int, UUID] = {}
        span_effective_interaction_ids: Dict[int, UUID] = {}
        last_child_interaction_by_parent_id: Dict[Optional[int], UUID] = {}
        span_agent_ids: Dict[int, UUID] = {}
        tool_task_ids: Dict[int, UUID] = {}
        intention_by_span_id: Dict[int, UUID] = {}

        root_agent = self._get_or_create_agent(root_span, bundle, span_by_id)
        root_input = _extract_input(root_span)
        root_goal_text = _to_compact_text(root_input)
        root_agent_span = next(
            (
                child
                for child in children_by_parent_id.get(root_span.context.span_id, [])
                if str(_span_attr(child, "openinference.span.kind", "")).upper() == "AGENT"
                and not _is_internal_beeai_agent_lifecycle_span(child)
            ),
            root_span if str(_span_attr(root_span, "openinference.span.kind", "")).upper() == "AGENT" else None,
        )

        root_message: Optional[Interaction] = None
        if root_input is not None:
            root_message = Interaction(
                interaction_id=uuid5(NAMESPACE_OID, f"interaction:root-message:{trace_id}"),
                workflow_exec_id=workflow_exec_id,
                source_entity_id=self.user_entity.entity_id,
                target_entity_id=self.system_entity.entity_id,
                type=InteractionType.message,
                payload={"content": root_goal_text or root_input},
                timestamp=_ns_to_datetime(root_span.start_time) or datetime.now(timezone.utc),
            )
            bundle.interactions.append(root_message)

        root_delegation: Optional[Interaction] = None
        if root_agent:
            root_delegation = Interaction(
                interaction_id=uuid5(NAMESPACE_OID, f"interaction:root-delegation:{trace_id}"),
                workflow_exec_id=workflow_exec_id,
                source_entity_id=self.system_entity.entity_id,
                target_entity_id=root_agent.entity_id,
                type=InteractionType.delegation,
                caused_by_interaction_id=root_message.interaction_id if root_message else None,
                payload={"goal": root_goal_text or root_input} if root_input is not None else None,
                timestamp=_ns_to_datetime(root_span.start_time) or datetime.now(timezone.utc),
            )
            agent_execution = _extract_agent_execution_payload(root_agent_span)
            if agent_execution is not None:
                if root_delegation.payload is None:
                    root_delegation.payload = {}
                root_delegation.payload["delegated_agent_execution"] = agent_execution
            bundle.interactions.append(root_delegation)

        workflow_exec.root_interaction_id = (
            root_message.interaction_id
            if root_message
            else root_delegation.interaction_id if root_delegation else None
        )

        for span in ordered_spans:
            agent = self._get_or_create_agent(span, bundle, span_by_id) or root_agent
            if agent is not None:
                span_agent_ids[span.context.span_id] = agent.entity_id
                self._register_declared_capabilities(span, agent, bundle)

            parent_span_id = getattr(getattr(span, "parent", None), "span_id", None)
            parent_context_interaction_id = span_interaction_ids.get(parent_span_id) or span_effective_interaction_ids.get(parent_span_id)
            parent_interaction_id = last_child_interaction_by_parent_id.get(parent_span_id) or parent_context_interaction_id
            if parent_interaction_id is None:
                parent_interaction_id = root_delegation.interaction_id if root_delegation else root_message.interaction_id if root_message else None

            task = self._create_tool_task(
                span=span,
                agent=agent,
                workflow_exec_id=workflow_exec_id,
                parent_interaction_id=parent_interaction_id,
                bundle=bundle,
            )
            if task is not None:
                tool_task_ids[span.context.span_id] = task.task_exec_id

            intention = self._create_span_intention(span, agent, bundle, parent_span_id)
            if intention:
                intention_by_span_id[span.context.span_id] = intention.intention_id

            interaction = self._create_span_interaction(
                span=span,
                workflow_exec_id=workflow_exec_id,
                agent=agent,
                task=task,
                bundle=bundle,
                caused_by_interaction_id=parent_interaction_id,
                intention_id=intention_by_span_id.get(span.context.span_id) or intention_by_span_id.get(parent_span_id),
                children_by_parent_id=children_by_parent_id,
                span_by_id=span_by_id,
            )
            if interaction:
                bundle.interactions.append(interaction)
                span_interaction_ids[span.context.span_id] = interaction.interaction_id
                span_effective_interaction_ids[span.context.span_id] = interaction.interaction_id
                last_child_interaction_by_parent_id[parent_span_id] = interaction.interaction_id
            elif parent_interaction_id is not None:
                span_effective_interaction_ids[span.context.span_id] = parent_interaction_id

        bundle.entities = list(self.entity_registry.values())
        return bundle

    def _entity_id(self, prefix: str, name: str) -> UUID:
        return uuid5(NAMESPACE_OID, f"{prefix}:{name}")

    def _assign_supervisor(self, entity: Optional[Entity], supervisor_id: Optional[UUID]) -> None:
        if entity is None or supervisor_id is None:
            return
        if entity.type != EntityType.agent:
            return
        if entity.supervisor_id is None:
            entity.supervisor_id = supervisor_id

    def _register_declared_capabilities(
        self,
        span: ReadableSpan,
        owner: Optional[Entity],
        bundle: TraceSemanticBundle,
    ) -> None:
        if owner is None or owner.type != EntityType.agent:
            return

        for spec in _extract_declared_capability_specs(span):
            target_name = spec["name"]
            capability_type = spec["capability_type"]

            if capability_type == CapabilityType.agent_access:
                target_entity_id = self._entity_id("agent", target_name)
                target_entity = self.entity_registry.get(target_entity_id)
                if target_entity is None:
                    target_entity = Entity(
                        entity_id=target_entity_id,
                        type=EntityType.agent,
                        name=target_name,
                        description=spec.get("description"),
                    )
                    self.entity_registry[target_entity_id] = target_entity
                    bundle.entities.append(target_entity)
            else:
                target_entity_id = self._entity_id("tool", target_name)
                target_entity = self.entity_registry.get(target_entity_id)
                if target_entity is None:
                    target_entity = Entity(
                        entity_id=target_entity_id,
                        type=EntityType.tool,
                        name=target_name,
                        description=spec.get("description"),
                        tool_schema=spec.get("tool_schema"),
                    )
                    self.entity_registry[target_entity_id] = target_entity
                    bundle.entities.append(target_entity)
                elif target_entity.tool_schema is None and spec.get("tool_schema") is not None:
                    target_entity.tool_schema = spec["tool_schema"]

            capability_id = uuid5(
                NAMESPACE_OID,
                f"capability:declared:{capability_type.value}:{owner.entity_id}:{target_entity_id}",
            )
            if capability_id in {cap.capability_id for cap in bundle.capabilities}:
                continue
            bundle.capabilities.append(
                Capability(
                    capability_id=capability_id,
                    owner_entity_id=owner.entity_id,
                    target_entity_id=target_entity_id,
                    type=capability_type,
                    granted_by=self.system_entity.entity_id,
                    granted_at=_ns_to_datetime(span.start_time),
                    constraints={"source": "declared_in_prompt_or_model_invocation"},
                )
            )

    def _resolve_agent_span(
        self,
        span: ReadableSpan,
        span_by_id: Mapping[int, ReadableSpan],
    ) -> Optional[ReadableSpan]:
        current: Optional[ReadableSpan] = span
        while current is not None:
            if not _is_internal_beeai_agent_lifecycle_span(current):
                name = _span_attr(current, "agent.name") or _span_attr(current, "session.name")
                if name:
                    return current
            parent_span_id = getattr(getattr(current, "parent", None), "span_id", None)
            current = span_by_id.get(parent_span_id)
        return None

    def _merge_agent_details(self, entity: Entity, span: ReadableSpan) -> None:
        if entity.type != EntityType.agent:
            return
        description = _span_attr(span, "metadata.agent_description") or _span_attr(span, "agent.description")
        if entity.description is None and description is not None:
            entity.description = description
        model_config = _extract_model_config(span)
        if model_config is None:
            return
        if entity.model_config_data is None:
            entity.model_config_data = model_config
            return
        current = entity.model_config_data
        if current.provider is None and model_config.provider is not None:
            current.provider = model_config.provider
        if current.model_name is None and model_config.model_name is not None:
            current.model_name = model_config.model_name
        if current.temperature is None and model_config.temperature is not None:
            current.temperature = model_config.temperature
        if current.max_tokens is None and model_config.max_tokens is not None:
            current.max_tokens = model_config.max_tokens
        if current.additional_params is None and model_config.additional_params is not None:
            current.additional_params = model_config.additional_params

    def _get_or_create_agent(
        self,
        span: ReadableSpan,
        bundle: TraceSemanticBundle,
        span_by_id: Mapping[int, ReadableSpan],
    ) -> Optional[Entity]:
        agent_span = self._resolve_agent_span(span, span_by_id)
        if agent_span is None:
            return None
        name = _span_attr(agent_span, "agent.name") or _span_attr(agent_span, "session.name")
        if not name:
            return None

        entity_id = self._entity_id("agent", str(name))
        existing = self.entity_registry.get(entity_id)
        if existing:
            self._merge_agent_details(existing, span)
            if agent_span is not span:
                self._merge_agent_details(existing, agent_span)
            return existing

        entity = Entity(
            entity_id=entity_id,
            type=EntityType.agent,
            name=str(name),
            description=_span_attr(agent_span, "metadata.agent_description") or _span_attr(agent_span, "agent.description"),
            model_config_data=_extract_model_config(span) or _extract_model_config(agent_span),
        )
        self.entity_registry[entity_id] = entity
        bundle.entities.append(entity)
        return entity

    def _get_or_create_tool(self, span: ReadableSpan, bundle: TraceSemanticBundle) -> Optional[Entity]:
        if _is_handoff_tool_span(span):
            return None
        kind = str(_span_attr(span, "openinference.span.kind", "")).upper()
        if kind != "TOOL":
            return None

        name = _span_attr(span, "tool.name") or span.name
        if not name:
            return None

        entity_id = self._entity_id("tool", str(name))
        existing = self.entity_registry.get(entity_id)
        if existing:
            return existing

        entity = Entity(
            entity_id=entity_id,
            type=EntityType.tool,
            name=str(name),
            description=_span_attr(span, "tool.description"),
            tool_schema=_extract_tool_schema(span),
        )
        self.entity_registry[entity_id] = entity
        bundle.entities.append(entity)
        return entity

    def _create_tool_task(
        self,
        span: ReadableSpan,
        agent: Optional[Entity],
        workflow_exec_id: UUID,
        parent_interaction_id: Optional[UUID],
        bundle: TraceSemanticBundle,
    ) -> Optional[TaskExecution]:
        if str(_span_attr(span, "openinference.span.kind", "")).upper() != "TOOL":
            return None
        if _is_handoff_tool_span(span):
            return None

        source_entity_id = agent.entity_id if agent else self.system_entity.entity_id
        task = TaskExecution(
            task_exec_id=uuid5(NAMESPACE_OID, f"task:tool:{workflow_exec_id}:{span.context.span_id}"),
            workflow_exec_id=workflow_exec_id,
            parent_task_exec_id=None,
            created_by_entity_id=source_entity_id,
            created_by_interaction_id=parent_interaction_id,
            assigned_to_entity_id=source_entity_id,
            status=_task_status(span),
            input=_extract_input(span),
            output=_extract_output(span),
            started_at=_ns_to_datetime(span.start_time),
            ended_at=_ns_to_datetime(span.end_time),
            metrics=ExecutionMetrics(
                start_time=_ns_to_datetime(span.start_time),
                end_time=_ns_to_datetime(span.end_time),
                other_stats={
                    "source_span_id": str(span.context.span_id),
                    "span_name": span.name,
                    "span_kind": _span_attr(span, "openinference.span.kind"),
                },
            ),
        )
        bundle.tasks.append(task)
        return task

    def _create_span_intention(
        self,
        span: ReadableSpan,
        agent: Optional[Entity],
        bundle: TraceSemanticBundle,
        parent_span_id: Optional[int],
    ) -> Optional[Intention]:
        if agent is None:
            return None

        reasoning = _extract_explicit_reasoning(span)
        if not reasoning:
            return None

        intention = Intention(
            intention_id=uuid5(NAMESPACE_OID, f"intention:{span.context.trace_id}:{span.context.span_id}"),
            created_by_entity_id=agent.entity_id,
            goal=_to_compact_text(_extract_input(span)) or span.name,
            reasoning=reasoning,
            confidence=IntentionConfidence.explicit,
            evidence={
                "source_span_id": str(span.context.span_id),
                "span_name": span.name,
                "span_kind": _span_attr(span, "openinference.span.kind"),
                "source": "explicit_reasoning",
            },
            timestamp=_ns_to_datetime(span.start_time) or datetime.now(timezone.utc),
        )
        bundle.intentions.append(intention)
        return intention

    def _create_span_interaction(
        self,
        span: ReadableSpan,
        workflow_exec_id: UUID,
        agent: Optional[Entity],
        task: Optional[TaskExecution],
        bundle: TraceSemanticBundle,
        caused_by_interaction_id: Optional[UUID],
        intention_id: Optional[UUID],
        children_by_parent_id: Dict[Optional[int], List[ReadableSpan]],
        span_by_id: Mapping[int, ReadableSpan],
    ) -> Optional[Interaction]:
        if _is_internal_beeai_agent_lifecycle_span(span):
            return None

        interaction_type = _infer_interaction_type(span)
        if interaction_type is None:
            return None

        source_entity_id = agent.entity_id if agent else self.system_entity.entity_id
        target_entity_id = None
        payload: Dict[str, Any] = {
            "span_name": span.name,
            "span_kind": _span_attr(span, "openinference.span.kind"),
        }

        input_value = _extract_input(span)
        output_value = _extract_output(span)
        if input_value is not None:
            payload["input"] = input_value
        if output_value is not None:
            payload["output"] = output_value
        events = _extract_span_events(span)
        if events:
            payload["events"] = events

        if _is_handoff_tool_span(span):
            child_agent_span = next(
                (
                    child
                    for child in children_by_parent_id.get(span.context.span_id, [])
                    if str(_span_attr(child, "openinference.span.kind", "")).upper() == "AGENT"
                ),
                None,
            )
            target_agent = self._get_or_create_agent(child_agent_span, bundle, span_by_id) if child_agent_span is not None else None
            if target_agent is not None:
                self._assign_supervisor(target_agent, source_entity_id)
                interaction_type = InteractionType.delegation
                target_entity_id = target_agent.entity_id
                payload["handoff_tool_name"] = _span_attr(span, "tool.name") or span.name
                handoff_args = _parse_json_string(_span_attr(span, "metadata.context.tool_call_msg.args"))
                if handoff_args is not None:
                    payload["handoff_arguments"] = _jsonable(handoff_args)
                delegated_agent_execution = _extract_agent_execution_payload(child_agent_span)
                if delegated_agent_execution is not None:
                    payload["delegated_agent_execution"] = delegated_agent_execution
                capability = Capability(
                    capability_id=uuid5(NAMESPACE_OID, f"capability:agent:{source_entity_id}:{target_entity_id}"),
                    owner_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    type=CapabilityType.agent_access,
                    granted_by=self.system_entity.entity_id,
                    granted_at=_ns_to_datetime(span.start_time),
                )
                if capability.capability_id not in {cap.capability_id for cap in bundle.capabilities}:
                    bundle.capabilities.append(capability)
                interaction = Interaction(
                    interaction_id=uuid5(NAMESPACE_OID, f"interaction:span:{span.context.trace_id}:{span.context.span_id}"),
                    workflow_exec_id=workflow_exec_id,
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    type=interaction_type,
                    related_task_exec_id=None,
                    based_on_intention_id=intention_id,
                    caused_by_interaction_id=caused_by_interaction_id,
                    payload=payload,
                    timestamp=_ns_to_datetime(span.start_time) or datetime.now(timezone.utc),
                )
                return interaction

        if interaction_type == InteractionType.tool_invocation:
            tool = self._get_or_create_tool(span, bundle)
            if tool is not None:
                target_entity_id = tool.entity_id
                capability = Capability(
                    capability_id=uuid5(NAMESPACE_OID, f"capability:{source_entity_id}:{target_entity_id}"),
                    owner_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    type=CapabilityType.tool_access,
                    granted_by=self.system_entity.entity_id,
                    granted_at=_ns_to_datetime(span.start_time),
                )
                if capability.capability_id not in {cap.capability_id for cap in bundle.capabilities}:
                    bundle.capabilities.append(capability)

        if interaction_type == InteractionType.model_invocation:
            metrics = _extract_model_metrics(span)
            if metrics is not None:
                payload["model_metrics"] = metrics.model_dump(mode="json")

        return Interaction(
            interaction_id=uuid5(NAMESPACE_OID, f"interaction:span:{span.context.trace_id}:{span.context.span_id}"),
            workflow_exec_id=workflow_exec_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            type=interaction_type,
            related_task_exec_id=task.task_exec_id if task is not None else None,
            based_on_intention_id=intention_id,
            caused_by_interaction_id=caused_by_interaction_id,
            payload=payload,
            timestamp=_ns_to_datetime(span.start_time) or datetime.now(timezone.utc),
        )

class InMemorySpanCollector(ISpanCollector):
    def __init__(self) -> None:
        self.buffer = SpanBuffer()
        self.translator = SpanTranslator()
        self.persistence = TracePersistence()
        self.pydantic_objs: List[Any] = []

    @property
    def spans(self) -> List[ReadableSpan]:
        return self.buffer.spans

    def on_start(self, span: ReadableSpan, parent_context: Optional[Any] = None) -> None:
        return None

    def on_end(self, span: ReadableSpan) -> None:
        self.buffer.add(span)
        if span.parent is None:
            self.process_trace(span.context.trace_id)

    def shutdown(self) -> None:
        for trace_id in self.buffer.trace_ids():
            self.process_trace(trace_id)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        for trace_id in self.buffer.trace_ids():
            self.process_trace(trace_id)
        return True

    def process_trace(self, trace_id: int) -> Optional[TraceSemanticBundle]:
        spans = self.buffer.pop_trace(trace_id)
        if not spans:
            return None

        bundle = self.translator.translate_trace(spans)
        if bundle is None:
            return None

        self.persistence.persist(bundle)
        self.pydantic_objs.extend(
            [
                bundle.workflow_definition,
                bundle.workflow_execution,
                *bundle.entities,
                *bundle.capabilities,
                *bundle.intentions,
                *bundle.tasks,
                *bundle.interactions,
            ]
        )
        return bundle
