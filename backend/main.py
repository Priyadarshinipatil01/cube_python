from typing import Optional
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from backend.database import get_connection, init_db
import os


app = FastAPI(title="Cube CRUD API", version="2.1.0")
init_db()

ALLOWED_CHARTS = {"bar", "line", "pie", "area", "number"}

class CubeBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    description: str = Field(default="", max_length=300)
    metric: str = Field(..., min_length=2, max_length=80)
    dimension: str = Field(..., min_length=2, max_length=80)
    chart_type: str = "bar"
    enabled: bool = True

    @field_validator("name", "metric", "dimension")
    @classmethod
    def clean_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("chart_type")
    @classmethod
    def validate_chart(cls, value):
        if value not in ALLOWED_CHARTS:
            raise ValueError("Invalid chart type")
        return value

class CubeCreate(CubeBase):
    pass

class CubeUpdate(CubeBase):
    pass

def row_to_dict(row):
    data = dict(row)
    data["enabled"] = bool(data["enabled"])
    return data

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/cubes")
def list_cubes(search: Optional[str] = None, enabled: Optional[bool] = None):
    conn = get_connection()
    query = "SELECT * FROM cubes WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR metric LIKE ? OR dimension LIKE ?)"
        term = f"%{search.strip()}%"
        params += [term, term, term]
    if enabled is not None:
        query += " AND enabled = ?"
        params.append(int(enabled))
    query += " ORDER BY id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.get("/cubes/{cube_id}")
def get_cube(cube_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM cubes WHERE id=?", (cube_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Cube not found")
    return row_to_dict(row)

@app.post("/cubes", status_code=201)
def create_cube(cube: CubeCreate):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO cubes (name,description,metric,dimension,chart_type,enabled) VALUES (?,?,?,?,?,?)",
            (cube.name, cube.description, cube.metric, cube.dimension, cube.chart_type, int(cube.enabled))
        )
        conn.commit()
        row = conn.execute("SELECT * FROM cubes WHERE id=?", (cur.lastrowid,)).fetchone()
        return row_to_dict(row)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "A cube with this name already exists")
    finally:
        conn.close()

@app.put("/cubes/{cube_id}")
def update_cube(cube_id: int, cube: CubeUpdate):
    conn = get_connection()
    if not conn.execute("SELECT id FROM cubes WHERE id=?", (cube_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Cube not found")
    try:
        conn.execute(
            "UPDATE cubes SET name=?,description=?,metric=?,dimension=?,chart_type=?,enabled=? WHERE id=?",
            (cube.name, cube.description, cube.metric, cube.dimension, cube.chart_type, int(cube.enabled), cube_id)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM cubes WHERE id=?", (cube_id,)).fetchone()
        return row_to_dict(row)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Another cube already uses this name")
    finally:
        conn.close()

@app.delete("/cubes/{cube_id}")
def delete_cube(cube_id: int):
    conn = get_connection()
    cur = conn.execute("DELETE FROM cubes WHERE id=?", (cube_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "Cube not found")
    return {"message": "Cube deleted successfully"}


# ================= AI ASSISTANT =================

class AIRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000
    )


def get_all_cubes_for_ai():
    conn = get_connection()

    rows = conn.execute(
        "SELECT * FROM cubes ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return [row_to_dict(row) for row in rows]


def rule_based_ai(question: str, cubes: list):
    q = question.lower().strip()

    total = len(cubes)
    enabled_cubes = [c for c in cubes if c["enabled"]]
    disabled_cubes = [c for c in cubes if not c["enabled"]]

    # -----------------------------------------
    # Empty database
    # -----------------------------------------

    if total == 0:
        return (
            "There are currently no cubes in the Cube Manager."
        )

    

    # -----------------------------------------
    # Enabled cube count
    # -----------------------------------------

    if (
    "how many cubes are enabled" in q
    or "how many enabled cubes" in q
    or "how many enabled" in q
    or "enabled cubes" in q
    or "active cubes" in q
    or "how many active" in q
    ):
        return (
            f"There are {len(enabled_cubes)} enabled cubes "
            f"out of {total} total cubes."
        )

    # -----------------------------------------
    # Disabled cube count
    # -----------------------------------------

    if (
    "how many cubes are disabled" in q
    or "how many disabled cubes" in q
    or "how many disabled" in q
    or "disabled cubes" in q
    or "inactive cubes" in q
    or "how many inactive" in q
    ):
        return (
            f"There are {len(disabled_cubes)} disabled cubes "
            f"out of {total} total cubes."
        )

    # -----------------------------------------
    # Total cube count
    # -----------------------------------------

    if (
        "how many cubes" in q
        or "total cubes" in q
        or "number of cubes" in q
        or "count cubes" in q
    ):
        return (
            f"There are {total} cubes in the Cube Manager."
        )

    # -----------------------------------------
    # List all cubes
    # -----------------------------------------

    if (
        "list cubes" in q
        or "show cubes" in q
        or "all cubes" in q
        or "cube list" in q
    ):
        result = ["Here are the current cubes:"]

        for cube in cubes:
            status = "Enabled" if cube["enabled"] else "Disabled"

            result.append(
                f"- {cube['name']} "
                f"(ID: {cube['id']}, Status: {status})"
            )

        return "\n".join(result)

    # -----------------------------------------
    # List enabled cubes
    # -----------------------------------------

    if (
        "show enabled" in q
        or "list enabled" in q
        or "enabled cube names" in q
    ):
        if not enabled_cubes:
            return "There are no enabled cubes."

        result = ["Enabled cubes:"]

        for cube in enabled_cubes:
            result.append(
                f"- {cube['name']} (ID: {cube['id']})"
            )

        return "\n".join(result)

    # -----------------------------------------
    # List disabled cubes
    # -----------------------------------------

    if (
        "show disabled" in q
        or "list disabled" in q
        or "disabled cube names" in q
    ):
        if not disabled_cubes:
            return "There are no disabled cubes."

        result = ["Disabled cubes:"]

        for cube in disabled_cubes:
            result.append(
                f"- {cube['name']} (ID: {cube['id']})"
            )

        return "\n".join(result)

    # -----------------------------------------
    # Metric search
    # -----------------------------------------

    metric_matches = []

    for cube in cubes:
        metric = str(cube["metric"]).lower()

        if metric in q or q.replace(" ", "_") in metric:
            metric_matches.append(cube)

    if metric_matches:

        result = ["Cubes using the requested metric:"]

        for cube in metric_matches:
            result.append(
                f"- {cube['name']} "
                f"(ID: {cube['id']}) "
                f"uses metric `{cube['metric']}`."
            )

        return "\n".join(result)

    # -----------------------------------------
    # Dimension search
    # -----------------------------------------

    dimension_matches = []

    for cube in cubes:
        dimension = str(cube["dimension"]).lower()

        if dimension in q or q.replace(" ", "_") in dimension:
            dimension_matches.append(cube)

    if dimension_matches:

        result = ["Cubes using the requested dimension:"]

        for cube in dimension_matches:
            result.append(
                f"- {cube['name']} "
                f"(ID: {cube['id']}) "
                f"uses dimension `{cube['dimension']}`."
            )

        return "\n".join(result)

    # -----------------------------------------
    # Specific cube name search
    # -----------------------------------------

    name_matches = []

    for cube in cubes:
        name = str(cube["name"]).lower()

        if name in q:
            name_matches.append(cube)

    if name_matches:

        cube = name_matches[0]

        status = (
            "Enabled"
            if cube["enabled"]
            else "Disabled"
        )

        return (
            f"Cube: {cube['name']}\n"
            f"ID: {cube['id']}\n"
            f"Description: {cube['description'] or 'No description'}\n"
            f"Metric: {cube['metric']}\n"
            f"Dimension: {cube['dimension']}\n"
            f"Chart Type: {cube['chart_type'].title()}\n"
            f"Status: {status}"
        )

    # -----------------------------------------
    # Configuration question
    # -----------------------------------------

    if (
        "configuration" in q
        or "config" in q
        or "details" in q
        or "information" in q
    ):

        result = [
            f"Cube Manager currently contains {total} cubes.",
            f"Enabled: {len(enabled_cubes)}",
            f"Disabled: {len(disabled_cubes)}",
            "",
            "Cube configurations:"
        ]

        for cube in cubes:
            status = (
                "Enabled"
                if cube["enabled"]
                else "Disabled"
            )

            result.append(
                f"- {cube['name']}: "
                f"Metric={cube['metric']}, "
                f"Dimension={cube['dimension']}, "
                f"Chart={cube['chart_type']}, "
                f"Status={status}"
            )

        return "\n".join(result)

    # -----------------------------------------
    # Chart type question
    # -----------------------------------------

    chart_matches = []

    for cube in cubes:

        chart = str(cube["chart_type"]).lower()

        if chart in q:
            chart_matches.append(cube)

    if chart_matches:

        result = [
            "Cubes using the requested chart type:"
        ]

        for cube in chart_matches:
            result.append(
                f"- {cube['name']} "
                f"uses a {cube['chart_type']} chart."
            )

        return "\n".join(result)

    # -----------------------------------------
    # Help
    # -----------------------------------------

    if (
        "help" in q
        or "what can you do" in q
        or "what can i ask" in q
    ):
        return """
You can ask me questions such as:

• How many cubes do I have?
• How many cubes are enabled?
• How many cubes are disabled?
• Show all cubes.
• Show enabled cubes.
• Show disabled cubes.
• Which cube uses employee_count?
• Which cube uses department?
• Explain my cube configuration.
• Tell me about Sales Cube.
• Which cubes use bar charts?
"""

    # -----------------------------------------
    # Default response
    # -----------------------------------------

    return """
I couldn't understand that question.

Try asking:

• How many cubes are enabled?
• Show all cubes.
• Which cube uses employee_count?
• Explain my cube configuration.
• Tell me about Sales Cube.
"""


@app.post("/ai/ask")
def ai_ask(request: AIRequest):

    cubes = get_all_cubes_for_ai()

    answer = rule_based_ai(
        request.question,
        cubes
    )

    return {
        "answer": answer,
        "model": "Rule-Based Python AI",
        "source": "SQLite Cube Database"
    }

    