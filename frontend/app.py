import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import os

API_URL = "http://localhost:8000"
CHARTS = ["bar", "line", "pie", "area", "number"]

st.set_page_config(page_title="Cube Manager", page_icon="📊", layout="wide")

def api(method, path, **kwargs):
    try:
        response = requests.request(method, API_URL + path, timeout=10, **kwargs)
        try:
            data = response.json()
        except ValueError:
            data = {"detail": response.text}
        return response, data
    except requests.RequestException:
        st.error("FastAPI is not running. Start: uvicorn backend.main:app --reload --port 8000")
        st.stop()

def reset_add_form():
    for key in ["add_name", "add_description", "add_metric", "add_dimension", "add_chart", "add_enabled"]:
        if key in st.session_state:
            del st.session_state[key]

health, _ = api("GET", "/health")
if not health.ok:
    st.stop()

st.title("📊 Cube Manager")

# ================= AI ASSISTANT =================

st.subheader("🤖 AI Cube Assistant")

st.caption(
    "Ask natural-language questions about your existing cube data. "
    "The assistant answers using the current SQLite cube catalog."
)

with st.container(border=True):

    st.markdown(
        """
        **Try asking:**

        💡 How many cubes are enabled?

        💡 Which cube uses employee_count?

        💡 Explain my cube configuration.

        💡 Show all cubes.
        """
    )

    ai_question = st.text_input(
        "Ask your question",
        placeholder="Example: How many cubes are enabled?"
    )

    if st.button(
        "🤖 Ask AI",
        type="primary"
    ):

        if not ai_question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner(
                "Analyzing your cube data..."
            ):

                ai_response, ai_data = api(
                    "POST",
                    "/ai/ask",
                    json={
                        "question": ai_question.strip()
                    }
                )

            if ai_response.ok:

                st.markdown("### 🤖 AI Answer")

                st.success(
                    ai_data.get(
                        "answer",
                        "No answer received."
                    )
                )

                st.caption(
                    f"Assistant: "
                    f"{ai_data.get('model', 'Rule-Based Python AI')} "
                    f"| Source: "
                    f"{ai_data.get('source', 'SQLite')}"
                )

            else:

                st.error(
                    ai_data.get(
                        "detail",
                        "AI request failed."
                    )
                )

st.divider()

# ================= CUBE METRICS =================

all_response, all_cubes = api("GET", "/cubes")
all_cubes = all_cubes if all_response.ok else []

a, b, c = st.columns(3)
a.metric("Total Cubes", len(all_cubes))
b.metric("Enabled", sum(x["enabled"] for x in all_cubes))
c.metric("Disabled", sum(not x["enabled"] for x in all_cubes))

st.divider()

with st.sidebar:
    st.header("Cube Form")
    mode = st.radio("Action", ["Add Cube", "Edit Cube"], horizontal=True)

    if mode == "Add Cube":
        
        name = st.text_input("Name *", key="add_name")
        description = st.text_area("Description", key="add_description", max_chars=300)
        metric = st.text_input("Metric *", key="add_metric")
        dimension = st.text_input("Dimension *", key="add_dimension")
        chart = st.selectbox("Chart Type", CHARTS, key="add_chart")
        enabled = st.checkbox("Enabled", value=True, key="add_enabled")

        if st.button("➕ Add Cube", type="primary", use_container_width=True):
            errors = []
            if len(name.strip()) < 2: errors.append("Name must contain at least 2 characters.")
            if len(metric.strip()) < 2: errors.append("Metric must contain at least 2 characters.")
            if len(dimension.strip()) < 2: errors.append("Dimension must contain at least 2 characters.")

            if errors:
                for error in errors:
                    st.warning(error)
            else:
                payload = {
                    "name": name.strip(),
                    "description": description.strip(),
                    "metric": metric.strip(),
                    "dimension": dimension.strip(),
                    "chart_type": chart,
                    "enabled": enabled
                }
                response, data = api("POST", "/cubes", json=payload)
                if response.ok:
                    reset_add_form()
                    st.success("Cube created successfully.")
                    st.rerun()
                else:
                    st.error(data.get("detail", "Unable to create cube."))

    else:
        edit_id = st.number_input("Cube ID", min_value=1, step=1, value=1)
        response, selected = api("GET", f"/cubes/{edit_id}")
        if not response.ok:
            st.warning("Enter an existing Cube ID.")
            selected = {}

        name = st.text_input("Name *", selected.get("name", ""))
        description = st.text_area("Description", selected.get("description", ""), max_chars=300)
        metric = st.text_input("Metric *", selected.get("metric", ""))
        dimension = st.text_input("Dimension *", selected.get("dimension", ""))
        current = selected.get("chart_type", "bar")
        chart = st.selectbox("Chart Type", CHARTS, index=CHARTS.index(current))
        enabled = st.checkbox("Enabled", selected.get("enabled", True))

        if st.button("💾 Update Cube", type="primary", use_container_width=True):
            errors = []
            if len(name.strip()) < 2: errors.append("Name must contain at least 2 characters.")
            if len(metric.strip()) < 2: errors.append("Metric must contain at least 2 characters.")
            if len(dimension.strip()) < 2: errors.append("Dimension must contain at least 2 characters.")
            if errors:
                for error in errors:
                    st.warning(error)
            else:
                payload = {
                    "name": name.strip(),
                    "description": description.strip(),
                    "metric": metric.strip(),
                    "dimension": dimension.strip(),
                    "chart_type": chart,
                    "enabled": enabled
                }
                response, data = api("PUT", f"/cubes/{edit_id}", json=payload)
                if response.ok:
                    st.success("Cube updated successfully.")
                    st.rerun()
                else:
                    st.error(data.get("detail", "Unable to update cube."))

st.subheader("Cube Catalog")

f1, f2 = st.columns([3, 1])
with f1:
    search = st.text_input("🔎 Search", placeholder="Search name, metric or dimension")
with f2:
    status = st.selectbox("Status", ["All", "Enabled", "Disabled"])

params = {}
if search.strip():
    params["search"] = search.strip()
if status == "Enabled":
    params["enabled"] = "true"
elif status == "Disabled":
    params["enabled"] = "false"

response, cubes = api("GET", "/cubes", params=params)
if not response.ok:
    st.error(cubes.get("detail", "Unable to load cubes."))
    st.stop()

if not cubes:
    st.info("No cubes match the current filters.")
else:
    columns = st.columns(3)
    for i, cube in enumerate(cubes):
        with columns[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {cube['name']}")
                st.caption(cube["description"] or "No description")
                st.write(f"**Metric:** `{cube['metric']}`")
                st.write(f"**Dimension:** `{cube['dimension']}`")
                st.write(f"**Chart Type:** `{cube['chart_type'].title()}`")
                st.write(f"**Status:** {'🟢 Enabled' if cube['enabled'] else '⚪ Disabled'}")
                st.caption(f"Cube ID: {cube['id']}")

                # Demo data only for chart preview. Replace with Cube.dev/API data later.
                chart_df = pd.DataFrame({
                    "Department": ["Engineering", "HR", "Finance", "Sales", "Marketing"],
                    "Employees": [42, 18, 12, 31, 24]
                })

                st.markdown("**Chart Preview**")
                ct = cube["chart_type"]

                if ct == "bar":
                    fig = px.bar(chart_df, x="Department", y="Employees", title="Employees by Department")
                    fig.update_layout(height=280, margin=dict(l=10, r=10, t=45, b=10))
                   
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_bar_{cube['id']}")
                elif ct == "line":
                    fig = px.line(chart_df, x="Department", y="Employees", markers=True, title="Employees by Department")
                    fig.update_layout(height=280, margin=dict(l=10, r=10, t=45, b=10))
                   
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_line_{cube['id']}")
                elif ct == "area":
                    fig = px.area(chart_df, x="Department", y="Employees", title="Employees by Department")
                    fig.update_layout(height=280, margin=dict(l=10, r=10, t=45, b=10))
                    # st.plotly_chart(fig, use_container_width=True)
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_area_{cube['id']}")
                elif ct == "pie":
                    fig = px.pie(chart_df, names="Department", values="Employees", title="Employee Distribution")
                    fig.update_layout(height=300, margin=dict(l=10, r=10, t=45, b=10))
                    # st.plotly_chart(fig, use_container_width=True)
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_pie_{cube['id']}")
                else:
                    st.metric("Employee Count", int(chart_df["Employees"].sum()))

                with st.expander("Delete"):
                    st.warning("This action cannot be undone.")
                    confirm = st.checkbox("I confirm deletion", key=f"confirm_{cube['id']}")
                    if st.button("Delete Cube", key=f"delete_{cube['id']}", disabled=not confirm):
                        delete_response, delete_data = api("DELETE", f"/cubes/{cube['id']}")
                        if delete_response.ok:
                            st.rerun()
                        else:
                            st.error(delete_data.get("detail", "Delete failed."))
                            
st.divider()

