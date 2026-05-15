import json
import os
from pathlib import Path

from prov.dot import prov_to_dot
from prov.model import PROV, Namespace, ProvAgent, ProvDocument

from .model.interaction_oriented import Capability, Entity, WorkflowExecution, Intention, TaskExecution, Interaction


# namespaces
SCHEMA = Namespace("schema", "http://schema.org/")
ENTITY = Namespace('entity', 'http://entity.example.org/')
INTENTION = Namespace('intention', 'http://intention.example.org/')
INTERACTION = Namespace('interaction', 'http://interaction.example.org/')
CAPABILITY = Namespace('capability', 'http://capability.example.org/')
WF_EXECUTION = Namespace('wf_execution', 'http://wf_execution.example.org/')
TASK_EXECUTION = Namespace('task_execution', 'http://task_execution.example.org/')


def _stringify(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def build_prov_document(workflow_example):
    doc = ProvDocument()
    doc.add_namespace(PROV)
    doc.add_namespace(ENTITY)
    doc.add_namespace(INTENTION)
    doc.add_namespace(INTERACTION)
    doc.add_namespace(CAPABILITY)
    doc.add_namespace(WF_EXECUTION)
    doc.add_namespace(TASK_EXECUTION)

    entity_map = {}
    task_map = {}
    interaction_map = {}

    # =========================
    # ENTITIES -> prov:Agent / prov:Entity
    # =========================

    for e in workflow_example["entities"]:

        e = Entity.model_validate(e)
        e: Entity

        attrs = {
            "prov:label": e.name,
            ENTITY["entity_id"]: str(e.entity_id),
            ENTITY["type"]: str(e.type),
            ENTITY["name"]: str(e.name),
        }

        if e.description:
            attrs[ENTITY["description"]] = e.description
    
        if e.type in ["agent", "user", "system"]:
            if e.type == "agent":
                if e.model_config_data:
                    attrs[ENTITY["model_config"]] = e.model_config_data.model_dump_json()
            
            aux = str(e.name) + str(e.entity_id)[:6]
            id_ = ENTITY[aux]
            prov_obj = doc.agent(id_, attrs)

            if e.supervisor_id:
                supervisor = entity_map.get(e.supervisor_id)
                if supervisor is not None:
                    doc.actedOnBehalfOf(prov_obj, supervisor)
        else:
            if e.tool_schema:
                attrs[ENTITY["tool_schema"]] = e.tool_schema.model_dump_json()
            aux = str(e.name) + str(e.entity_id)[:6]
            id_ = ENTITY[aux]
            prov_obj = doc.entity(id_, attrs)

        entity_map[e.entity_id] = prov_obj

    # =========================
    # CAPABILITY -> prov:actedOnBehalfOf or prov:wasAttributedTo
    # =========================

    for capability in workflow_example["capabilities"]:
        
        capability = Capability.model_validate(capability)
        capability: Capability
        
        attrs = {
            CAPABILITY["type"]: str(capability.type),
            CAPABILITY["capability_id"]: str(capability.capability_id),
        }
        if capability.granted_at:
            attrs[CAPABILITY["granted_at"]] = capability.granted_at
        if capability.granted_by:
            attrs[CAPABILITY["granted_by_id"]] = str(capability.granted_by)
        if capability.valid_from:
            attrs[CAPABILITY["valid_from"]] = capability.valid_from
        if capability.valid_until:
            attrs[CAPABILITY["valid_until"]] = capability.valid_until
        if capability.constraints:
            attrs[CAPABILITY["constraints"]] = _stringify(capability.constraints)

        entity = entity_map.get(capability.owner_entity_id)
        entity_b = entity_map.get(capability.target_entity_id)
        if entity and entity_b:
            if isinstance(entity, ProvAgent):
                doc.actedOnBehalfOf(entity_b, entity, other_attributes=attrs) # ATTENTION: capacity or supervision/hierarchy
            else: 
                doc.wasAttributedTo(entity_b, entity, other_attributes=attrs)

    # =========================
    # WORKFLOW EXECUTION
    # =========================

    for w in workflow_example["workflow_execution"]:

        w = WorkflowExecution.model_validate(w)

        wid = WF_EXECUTION[str(w.workflow_exec_id)]

        attrs = {
            "prov:label": f"workflow_execution:{w.workflow_exec_id}",
            "prov:startTime": w.started_at,
            WF_EXECUTION["status"]: str(w.status),
        }

        if w.ended_at:
            attrs["prov:endTime"] = w.ended_at
        if w.goal:
            attrs[WF_EXECUTION["goal"]] = w.goal
        final_output = _stringify(w.final_output)
        if final_output:
            attrs[WF_EXECUTION["final_output"]] = final_output

        workflow_activity = doc.entity(identifier=wid, other_attributes=attrs)

    # =========================
    # INTENTIONS -> prov:Entity
    # =========================

    intention_map = {}
    for i in workflow_example["intentions"]:
        i = Intention.model_validate(i)

        attrs = {
            "prov:label": i.goal or str(i.intention_id),
            INTENTION["confidence"]: i.confidence
        }
        if i.reasoning:
            attrs[INTENTION["reasoning"]] = i.reasoning
        evidence = _stringify(i.evidence)
        if evidence:
            attrs[INTENTION["evidence"]] = evidence

        ent = doc.entity(INTENTION[str(i.intention_id)], attrs)

        creator = entity_map.get(i.created_by_entity_id)

        if creator is not None:
            doc.wasAttributedTo(ent, creator)

        intention_map[i.intention_id] = ent

    # =========================
    # TASKS -> prov:Activity
    # =========================

    for t in workflow_example["tasks"]:
        t = TaskExecution.model_validate(t)

        tid = TASK_EXECUTION[str(t.task_exec_id)]
        aux = next(iter(entity_map[t.created_by_entity_id].get_attribute('prov:label'))) + str(t.task_exec_id)[:5]
        tid = TASK_EXECUTION[aux]

        attrs = {
            TASK_EXECUTION["status"]: t.status,
            "prov:label": f"task_execution:{t.task_exec_id}",
        }
        task_input = _stringify(t.input)
        task_output = _stringify(t.output)
        if task_input:
            attrs[ENTITY["input"]] = task_input
        if task_output:
            attrs[ENTITY["output"]] = task_output
        if t.started_at:
            attrs["prov:startTime"] = t.started_at
        if t.ended_at:
            attrs["prov:endTime"] = t.ended_at

        act = doc.activity(tid, t.started_at, t.ended_at, attrs)

        task_map[t.task_exec_id] = act

        # Agent association.
        if t.created_by_entity_id:
            agent = entity_map.get(t.created_by_entity_id)
            if agent is not None:
                doc.wasAssociatedWith(act, agent, other_attributes={INTERACTION["role"]: "created_by_entity_id"})

        if t.assigned_to_entity_id:
            agent = entity_map.get(t.assigned_to_entity_id, None)
            if isinstance(agent, ProvAgent):
                doc.wasAssociatedWith(act, agent, other_attributes={INTERACTION["role"]: "assigned_to_entity_id"})
            else:
                if agent:
                    doc.used(act, agent, other_attributes={INTERACTION["role"]: "assigned_to_entity_id"})

        # Inputs.
        # if t.input:
        #     input_entity = doc.entity(
        #         ENTITY[f"input_{str(t.task_exec_id)}"],
        #         {ENTITY["data"]: str(t.input)}
        #     )
        #     doc.used(act, input_entity)

        # Task hierarchy.
        if t.parent_task_exec_id:
            parent = task_map.get(t.parent_task_exec_id)
            if parent:
                doc.wasInformedBy(act, parent, other_attributes={INTERACTION["role"]: "parent_task_exec_id"})

    # =========================
    # INTERACTIONS -> prov:Activity
    # =========================

    for inter in workflow_example["interactions"]:

        inter = Interaction.model_validate(inter)

        iid = INTERACTION[str(inter.interaction_id)]
        aux=str(inter.type) + str(inter.interaction_id)[:5]
        iid = INTERACTION[aux]
        

        attrs = {
            "prov:label": f"{inter.type}:{inter.interaction_id}",
            INTERACTION["type"]: inter.type
        }
        payload = _stringify(inter.payload)
        if payload:
            attrs[INTERACTION["payload"]] = payload

        act = doc.activity(iid, inter.timestamp, None, attrs)

        interaction_map[inter.interaction_id] = act

        source = entity_map.get(inter.source_entity_id)

        if source is not None:
            doc.wasAssociatedWith(act, source, other_attributes={INTERACTION["role"]: "created_by_entity_id"})

        # Target entity.
        if inter.target_entity_id:

            target = entity_map.get(inter.target_entity_id)

            if target is None:
                pass
            elif inter.type == "tool_invocation":
                doc.used(act, target)
            else:
                doc.wasAssociatedWith(act, target, other_attributes={INTERACTION["role"]: "assigned_to_entity_id"})
            # elif inter.type == "message":
            #     msg = doc.entity(
            #         INTERACTION[f"message_{inter.interaction_id}"],
            #         {"ex:payload": str(inter.payload)}
            #     )

            #     doc.wasGeneratedBy(msg, act)

            #     doc.wasAttributedTo(msg, source)

        # Link with the related task.
        if inter.related_task_exec_id:
            task = task_map.get(inter.related_task_exec_id)
            if task:
                doc.wasInformedBy(act, task, other_attributes={INTERACTION["type"]: "related_task_exec_id"})

        # Associated intention.
        if inter.based_on_intention_id:
            intention = intention_map.get(inter.based_on_intention_id)
            if intention:
                # doc.wasInfluencedBy(act, intention)
                doc.used(act, intention)

        # Link root interactions to the workflow execution.
        if inter.caused_by_interaction_id is None:
            doc.wasGeneratedBy(workflow_activity, act)

    for inter in workflow_example["interactions"]:
        inter = Interaction.model_validate(inter)

        # Link child interactions to parent interactions.
        parent_interaction = interaction_map.get(inter.caused_by_interaction_id, None)
        interaction = interaction_map.get(inter.interaction_id, None)
        if parent_interaction is not None and interaction is not None:
            doc.wasInformedBy(interaction, parent_interaction, other_attributes={INTERACTION["type"]: "caused_by_interaction_id"})

    # Link tasks to the interactions that created them.
    for t in workflow_example["tasks"]:
        t = TaskExecution.model_validate(t)

        if t.created_by_interaction_id:
            interaction = interaction_map.get(t.created_by_interaction_id)
            task = task_map.get(t.task_exec_id)
            if interaction is not None and task is not None:
                doc.wasInformedBy(task, interaction, other_attributes={INTERACTION["role"]: "created_by_interaction_id"})

    return doc

def anchor2prov(path=None):
    anchor_output_path = Path(os.getenv("ANCHOR_OUTPUT_PATH", ".anchor"))
    path = Path(path) if path else anchor_output_path / "workflow_db.json"
    
    with open(path, 'r') as file:
        content = json.load(file)

    workflow = {
        "entities": list(content.get('entity_table', {}).values()),
        "capabilities": list(content.get('capabilities', {}).values()),
        "tasks": list(content.get('task_executions', {}).values()),
        "intentions": list(content.get('intention_table', {}).values()),
        "interactions": list(content.get('interaction_table', {}).values()),
        "workflow_execution": list(content.get('workflow_executions', {}).values())
    }
    
    return build_prov_document(workflow)


if __name__ == '__main__':
    doc = anchor2prov()
    output_dir = Path(os.getenv("ANCHOR_OUTPUT_PATH", ".anchor"))
    output_dir.mkdir(parents=True, exist_ok=True)

    doc.serialize(output_dir / "prov.json")

    dot = prov_to_dot(doc, direction="LR", show_element_attributes=False, show_relation_attributes=False)
    dot.set_ratio("compress")
    dot.set_ranksep("0.1")
    dot.set_nodesep("0.1")
    dot.write_png(output_dir / "workflow_prov.png")
