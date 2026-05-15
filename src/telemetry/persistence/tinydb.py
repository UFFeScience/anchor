import os
from pathlib import Path

from tinydb import TinyDB, Query


DB_DIR = Path(os.getenv("ANCHOR_OUTPUT_PATH", ".anchor"))
DB_DIR.mkdir(parents=True, exist_ok=True)
db = TinyDB(DB_DIR / "workflow_db.json")


workflow_def_table = db.table("workflow_definitions")
workflow_exec_table = db.table("workflow_executions")
capability_table = db.table("capabilities")
agent_table = db.table("agents")
tool_table = db.table("tools")
task_def_table = db.table("task_definitions")
task_exec_table = db.table("task_executions")
event_table = db.table("events")
interaction_table = db.table("interaction_table")
intention_table = db.table("intention_table")
entity_table = db.table("entity_table")

def serialize(model):
    return model.dict()


def save(table, model):
    data = model.dict()
    table.insert(data)


def update(table, model, id_field: str):
    data = model.model_dump(mode="json", by_alias=True)
    obj_id = data[id_field]

    q = Query()
    try:
        existing = table.get(q[id_field] == obj_id)
        if existing:
            table.update(data, q[id_field] == obj_id)
        else:
            table.insert(data)
    except:
        table.insert(data)


def get_by_id(table, field_name, value):
    q = Query()
    return table.get(q[field_name] == value)
