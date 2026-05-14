from flask import Flask, render_template, request
import pandas as pd
import networkx as nx
import os
import json
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import mysql.connector
import html

app = Flask(__name__)

# ================================
# MYSQL CONFIG
# ================================
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Coursesynergy2026',
    'database': 'course_synergy'
}

# ================================
# LOAD DATA + EXCEL SYNC
# ================================
def load_data():
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)

        courses = pd.read_sql("SELECT * FROM courses", connection)
        subjects = pd.read_sql("SELECT * FROM subjects", connection)
        careers = pd.read_sql("SELECT * FROM careers", connection)
        syllabus = pd.read_sql("SELECT * FROM syllabus", connection)

        connection.close()

         
        for df in [courses, subjects, careers, syllabus]:
            df.columns = df.columns.str.strip()

        os.makedirs("data", exist_ok=True)

        courses.to_excel("data/courses.xlsx", index=False)
        subjects.to_excel("data/subjects.xlsx", index=False)
        careers.to_excel("data/careers.xlsx", index=False)
        syllabus.to_excel("data/syllabus.xlsx", index=False)

        print("Data loaded from MySQL & synced to Excel")

        return courses, subjects, careers, syllabus

    except Exception as e:
        print("MySQL Error:", e)
        print("Using Excel fallback...")

        courses = pd.read_excel("data/courses.xlsx")
        subjects = pd.read_excel("data/subjects.xlsx")
        careers = pd.read_excel("data/careers.xlsx")
        syllabus = pd.read_excel("data/syllabus.xlsx")

        return courses, subjects, careers, syllabus


# ================================
# GRAPH FUNCTIONS
# ================================
def build_graph(subjects_list):
    G = nx.DiGraph()

    for row in subjects_list:
        G.add_node(row["subject_id"], label=row["name"])

    for row in subjects_list:
        prereq = str(row.get("prerequisites", "")).strip()
        if prereq and prereq.lower() not in ["nan", "none"]:
            for p in prereq.split(','):
                p = p.strip()
                if p in G.nodes():
                    G.add_edge(p, row["subject_id"])

    return G


def nx_to_plotly(G, labels, hover, custom=None, title="Graph"):
    pos = nx.spring_layout(G, seed=42)

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1),
        mode="lines"
    )

    node_x, node_y = [], []
    for n in G.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=labels,
        textposition="top center",
        hovertext=hover,
        customdata=custom,
        marker=dict(size=20)
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(title=title)

    return json.dumps(fig, cls=PlotlyJSONEncoder)

def build_interactive_graph(subjects_list):
    G = build_graph(subjects_list)
    labels = list(G.nodes())

    subj_map = {s["subject_id"]: s for s in subjects_list}

    hover = [
        f"{subj_map[n]['name']} (Sem {subj_map[n]['semester']})"
        for n in labels
    ]

    return nx_to_plotly(G, labels, hover, labels, "Prerequisite Graph")

def build_semester_graph(semesters):
    import plotly.graph_objs as go
    import json
    from plotly.utils import PlotlyJSONEncoder

    # Sort semesters ascending
    semesters = sorted(set(s["semester"] for s in semesters))

    colors = [
        "#6C5CE7", "#00B894", "#0984E3",
        "#FD79A8", "#FDCB6E", "#E17055",
    ]

    while len(colors) < len(semesters):
        colors.extend(colors)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=[1]*len(semesters),
        y=[f"Sem {s}" for s in semesters],
        orientation='h',
        
        text=[f"Semester {s}" for s in semesters],
        textposition="inside",
        insidetextanchor="middle",
        customdata=semesters,
        marker=dict(
            color=colors[:len(semesters)]
        ),

        textfont=dict(
            size=38,
            color="white"
        ),

        hoverinfo="text",
        hoverlabel=dict(
            font=dict(
                size=10
            )
        ),
        hovertext=[f"Click to open Semester {s}" for s in semesters]
        
    ))
    fig.update_layout(
        title="Semester Flow",

        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(
            autorange="reversed"   
        ),

        height=max(300, len(semesters)*155),

        margin=dict(l=20, r=20, t=60, b=20),
        width=1400,

        plot_bgcolor="white",
        paper_bgcolor="white"
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)


def build_semester_subject_graph(subjects):
    
    # Different colors for each bar
    colors = ['#0b63d8', '#6c5ce7', '#00b894', '#e17055', "#a77518", 
              '#0984e3', '#a29bfe', '#55efc4', '#fab1a0', "#efcb56"]
    
  
    while len(colors) < len(subjects):
        colors.extend(colors)
    
    bar_text = [f"{s['subject_id']}:{s['name']}" for s in subjects]
    fig = go.Figure()
    fig.add_trace(go.Bar(
       
        x=[1] * len(subjects),
        text=bar_text,
        textposition="inside",
        insidetextanchor="middle",
        orientation='h',
        customdata=[s.get("subject_id", "") for s in subjects],
        marker=dict(
            color=colors[:len(subjects)],
            line=dict(color='#ffffff', width=1)
        ),
        textfont=dict(size=38, color='white'),
        hoverinfo='text',
        hovertext=[f"<b>{s['name']}</b><br>Subject ID: {s['subject_id']}<br>Click to view syllabus" for s in subjects],
        hoverlabel=dict(
            font=dict(
                size=10
            )
        )
    ))
    
    fig.update_layout(
    hoverlabel=dict(
        font=dict(
            size=10,
            color="white"
        ),
        bgcolor="black",
        bordercolor="white"
    ),

    title=dict(
        text="Semester Subjects (Click to view syllabus)",
        font=dict(size=45)
    ),

    xaxis_title="",
    yaxis_title="",
    height=max(300, len(subjects) * 155),

    xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    yaxis=dict(autorange="reversed"),

    margin=dict(l=100, r=50, t=90, b=20),

    plot_bgcolor="white",
    paper_bgcolor="white"
)
    
    return json.dumps(fig, cls=PlotlyJSONEncoder)

def build_syllabus_graph(units):
    units = sorted(units, key=lambda x: int(x["unit_no"]))

    colors = ['#0b63d8', '#6c5ce7', '#00b894', '#e17055', '#fdcb6e',
              '#0984e3', '#a29bfe', '#55efc4', '#fab1a0', '#ffeaa7']

    while len(colors) < len(units):
        colors.extend(colors)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=[1] * len(units),

        text=[u["unit_title"] for u in units],
        textposition="inside",
        insidetextanchor="middle",
        orientation="h",

        customdata=[u["content"] for u in units],

        marker=dict(color=colors[:len(units)]),

        textfont=dict(size=38, color="white"),

        hoverinfo="text"
    ))

    fig.update_layout(
        hoverlabel=dict(
        font=dict(
            size=10,
            color="white"
        ),
        bgcolor="black",
        bordercolor="white"
    ),
        yaxis=dict(autorange="reversed"),
        title="Syllabus Units (Click to view content)",
        title_font=dict(size=45),

        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),

        height=max(300, len(units) * 155),

        margin=dict(l=100, r=50, t=80, b=30),

        plot_bgcolor="white",
        paper_bgcolor="white"
    )

    return json.dumps(fig, cls=PlotlyJSONEncoder)

def build_career_graph(course_id, careers):
    row = careers[careers["course_id"].str.upper() == course_id.upper()]

    if row.empty:
        return json.dumps({"data": [], "layout": {}})

    jobs = str(row.iloc[0]["job"]).split(",")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=jobs, y=[1]*len(jobs)))

    fig.update_layout(title="Career Options")

    return json.dumps(fig, cls=PlotlyJSONEncoder)


# ================================
# ROUTES
# ================================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/qualifications")
def qualification_page():
    return render_template("qualifications.html")


@app.route("/courses")
def courses_page():
    courses, subjects, careers, syllabus = load_data()

    qual = request.args.get("qual", "10th")
    course_records = courses.to_dict(orient="records")

    mlt_ids = {"MLT"}
    blocked_lateral_ids = {"MLT", "GT", "OMCA", "T&T"}

    filtered = []
    lateral_entry_allowed = {}

    for c in course_records:
        cid = str(c["course_id"]).upper()

    # Hide MLT for ALL except PCB
        if qual != "12_pcb" and cid == "MLT":
            continue

    #CASE 1: PCB → show ALL courses, NO lateral entry
        if qual == "12_pcb":
            lateral_entry_allowed[cid] = False
            filtered.append(c)
            continue

    #CASE 2: PCM → lateral entry allowed only for some
        if qual == "12_pcm":
            if cid not in {"GT", "OMCA", "T&T"}:
                lateral_entry_allowed[cid] = True
            else:
                lateral_entry_allowed[cid] = False

            filtered.append(c)
            continue

    #CASE 3: 10th / Arts-Commerce → no lateral entry
        elif qual in {"10th", "12_arts_commerce"}:
            lateral_entry_allowed[cid] = False
            
            filtered.append(c)

    return render_template(
        "courses.html",
        courses=filtered,
        qual=qual,
        lateral_entry_allowed=lateral_entry_allowed
    )


@app.route("/roadmap/<course_id>")
def roadmap(course_id):
    courses, subjects, careers, syllabus = load_data()

    course_subjects = subjects[
        subjects["course_id"].str.upper() == course_id.upper()
    ]

    subjects_list = course_subjects.to_dict(orient="records")

    prereq_json = build_interactive_graph(subjects_list)
    sem_json = build_semester_graph(subjects_list)
    row = careers[
        careers["course_id"].str.upper() == course_id.upper()
    ]

    career_data = {
        "job": row.iloc[0]["job"],
        "education": row.iloc[0]["education"],
        "entrepreneurship": row.iloc[0]["entrepreneurship"]
}

    course_row = courses[courses["course_id"].str.upper() == course_id.upper()]

    course_name = course_row.iloc[0]["name"] if not course_row.empty else course_id
    course_info = course_row.iloc[0].to_dict() if not course_row.empty else None

    return render_template(
        "detail.html",
        course_id=course_id,
        course_name=course_name,
        course_info=course_info,
        prereq_json=prereq_json,
        sem_graph_json=sem_json,
        career_data=career_data        
    )


@app.route("/semester/<course_id>/<int:sem>")
def semester_view(course_id, sem):
    course_id = html.unescape(course_id)
    courses, subjects, careers, syllabus = load_data()

    sem_sub = subjects[
        (subjects["course_id"].str.upper() == course_id.upper()) &
        (subjects["semester"] == sem)
    ]

    subjects_list = sem_sub.to_dict(orient="records")
    graph_json = build_semester_subject_graph(subjects_list)

    return render_template(
        "semester.html",
        course_id=course_id,
        semester=sem,
        subjects=subjects_list,
        subject_graph_json=graph_json
    )


@app.route("/syllabus/<path:subject_id>")
def syllabus_view(subject_id):
    courses, subjects, careers, syllabus = load_data()

    subject_row = subjects[
        subjects["subject_id"].str.upper() == subject_id.upper()
    ]

    if subject_row.empty:
        return "Subject not found", 404

    subject = subject_row.iloc[0].to_dict()
    course_id = str(subject.get("course_id")).strip().upper()

    # MAIN FILTER
    units = syllabus[
        (syllabus["subject_id"].str.strip().str.upper() == subject_id.upper()) &
        (syllabus["course_id"].str.strip().str.upper() == course_id)
    ]

    # FALLBACK
    if units.empty:
        units = syllabus[
            syllabus["subject_id"].str.strip().str.upper() == subject_id.upper()
        ]

    # SORT + CLEAN
    units = units.sort_values(by="unit_no")
    units = units.drop_duplicates(subset=["subject_id", "course_id", "unit_no"])

    units_list = units.to_dict(orient="records")

    graph_json = build_syllabus_graph(units_list)

    # ✅ ALWAYS OUTSIDE ALL CONDITIONS
    return render_template(
        "syllabus.html",
        subject=subject,
        units=units_list,
        syllabus_graph_json=graph_json
    )

    
# ================================
# RUN
# ================================
if __name__ == "__main__":
    import os

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )