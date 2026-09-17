import os
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

try:
    from supabase import create_client
except Exception:
    create_client = None

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Neural@123")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
USE_SUPABASE = bool(
    SUPABASE_URL
    and SUPABASE_KEY
    and create_client
    and "YOUR_PROJECT" not in SUPABASE_URL
    and "YOUR_SUPABASE_SERVICE_ROLE_KEY" not in SUPABASE_KEY
)

DEMO_DB = os.path.join(os.path.dirname(__file__), "neural_nexus_demo.db")


def db_init():
    con = sqlite3.connect(DEMO_DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_code TEXT,
        name TEXT NOT NULL,
        register_no TEXT,
        college TEXT,
        course TEXT,
        department TEXT,
        year TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        role TEXT,
        status TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_code TEXT,
        title TEXT NOT NULL,
        student_id INTEGER,
        domain TEXT,
        technology TEXT,
        staff_id INTEGER,
        priority TEXT DEFAULT 'Normal',
        status TEXT DEFAULT 'Enquiry',
        start_date TEXT,
        deadline TEXT,
        amount REAL DEFAULT 0,
        github_url TEXT,
        drive_url TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        student_id INTEGER,
        amount REAL NOT NULL DEFAULT 0,
        payment_date TEXT,
        method TEXT,
        transaction_id TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Seed only when the local demo database is empty.
    if cur.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO staff(name,email,phone,role,status) VALUES(?,?,?,?,?)",
            ("Neural Nexus Admin", "neuralnexus092@gmail.com", "9567088095", "Administrator", "Active")
        )
    if cur.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        cur.execute(
            """INSERT INTO students(student_code,name,register_no,college,course,department,year,phone,email)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            ("NN-STU-001", "Demo Student", "NN2026-001", "Demo College",
             "B.Tech", "Computer Science", "Final Year", "9999999999", "student@example.com")
        )
    if cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
        cur.execute(
            """INSERT INTO projects(project_code,title,student_id,domain,technology,staff_id,priority,status,
               start_date,deadline,amount,notes)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("NN-PRJ-001", "AI Smart Surveillance System", 1, "Artificial Intelligence",
             "Python, OpenCV, PyTorch", 1, "High", "Development", str(date.today()),
             str(date.today()), 25000, "Demo project record. Replace with real data.")
        )
    con.commit()
    con.close()


def local_query(sql, params=()):
    con = sqlite3.connect(DEMO_DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(sql, params).fetchall()
    con.close()
    return [dict(r) for r in rows]


def local_one(sql, params=()):
    rows = local_query(sql, params)
    return rows[0] if rows else None


def local_exec(sql, params=()):
    con = sqlite3.connect(DEMO_DB)
    cur = con.execute(sql, params)
    con.commit()
    last_id = cur.lastrowid
    con.close()
    return last_id


def sb():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def data(table, order="created_at", desc=True, filters=None):
    if USE_SUPABASE:
        q = sb().table(table).select("*")
        if filters:
            for key, value in filters.items():
                if value not in (None, ""):
                    q = q.eq(key, value)
        try:
            return q.order(order, desc=desc).execute().data or []
        except Exception:
            return []
    return local_query(f"SELECT * FROM {table} ORDER BY {order} {'DESC' if desc else 'ASC'}")


def one(table, item_id):
    if USE_SUPABASE:
        try:
            res = sb().table(table).select("*").eq("id", item_id).limit(1).execute()
            return (res.data or [None])[0]
        except Exception:
            return None
    return local_one(f"SELECT * FROM {table} WHERE id=?", (item_id,))


def insert(table, payload):
    if USE_SUPABASE:
        return sb().table(table).insert(payload).execute().data
    cols = list(payload.keys())
    marks = ",".join(["?"] * len(cols))
    return [local_one(
        f"SELECT * FROM {table} WHERE id=?",
        (local_exec(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({marks})",
                    tuple(payload[c] for c in cols)),)
    )]


def update(table, item_id, payload):
    if USE_SUPABASE:
        return sb().table(table).update(payload).eq("id", item_id).execute().data
    assignments = ",".join([f"{k}=?" for k in payload])
    local_exec(f"UPDATE {table} SET {assignments} WHERE id=?",
               tuple(payload.values()) + (item_id,))
    return []


def delete(table, item_id):
    if USE_SUPABASE:
        return sb().table(table).delete().eq("id", item_id).execute().data
    local_exec(f"DELETE FROM {table} WHERE id=?", (item_id,))
    return []


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_globals():
    return {
        "brand_name": "Neural Nexus",
        "today": date.today().isoformat(),
        "using_supabase": USE_SUPABASE,
        "status_options": [
            "Enquiry", "Confirmed", "Requirements", "Development",
            "Testing", "Documentation", "Completed", "Delivered"
        ]
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["logged_in"] = True
            session["username"] = username
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    students = data("students")
    projects = data("projects")
    staff = data("staff")
    payments = data("payments")

    total_amount = sum(float(p.get("amount") or 0) for p in projects)
    collected = sum(float(p.get("amount") or 0) for p in payments)
    outstanding = max(total_amount - collected, 0)

    status_counts = {s: sum(1 for p in projects if p.get("status") == s) for s in
                     ["Enquiry", "Confirmed", "Requirements", "Development", "Testing",
                      "Documentation", "Completed", "Delivered"]}

    return render_template(
        "dashboard.html",
        students=students, projects=projects, staff=staff, payments=payments,
        total_amount=total_amount, collected=collected, outstanding=outstanding,
        status_counts=status_counts
    )


@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip().lower()
    rows = data("students")
    if q:
        rows = [r for r in rows if q in " ".join(str(r.get(k) or "") for k in
                 ["name","register_no","college","course","phone","email"]).lower()]
    return render_template("students.html", students=rows, q=q)


@app.route("/students/new", methods=["GET", "POST"])
@login_required
def student_new():
    if request.method == "POST":
        payload = {k: request.form.get(k, "").strip() for k in [
            "student_code","name","register_no","college","course","department","year","phone","email","address"
        ]}
        if not payload["name"]:
            flash("Student name is required.", "danger")
        else:
            insert("students", payload)
            flash("Student added successfully.", "success")
            return redirect(url_for("students"))
    return render_template("student_form.html", student=None, form_title="Add Student")


@app.route("/students/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def student_edit(item_id):
    student = one("students", item_id)
    if not student:
        return redirect(url_for("students"))
    if request.method == "POST":
        payload = {k: request.form.get(k, "").strip() for k in [
            "student_code","name","register_no","college","course","department","year","phone","email","address"
        ]}
        update("students", item_id, payload)
        flash("Student updated.", "success")
        return redirect(url_for("students"))
    return render_template("student_form.html", student=student, form_title="Edit Student")


@app.post("/students/<int:item_id>/delete")
@login_required
def student_delete(item_id):
    delete("students", item_id)
    flash("Student deleted.", "success")
    return redirect(url_for("students"))


@app.route("/projects")
@login_required
def projects():
    rows = data("projects")
    students_list = data("students")
    staff_list = data("staff")
    smap = {s["id"]: s["name"] for s in students_list}
    fmap = {s["id"]: s["name"] for s in staff_list}
    for r in rows:
        r["student_name"] = smap.get(r.get("student_id"), "Unassigned")
        r["staff_name"] = fmap.get(r.get("staff_id"), "Unassigned")
    q = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "").strip()
    if q:
        rows = [r for r in rows if q in " ".join(str(r.get(k) or "") for k in
                 ["project_code","title","domain","technology","student_name","staff_name"]).lower()]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return render_template("projects.html", projects=rows, q=q, status=status)


@app.route("/projects/new", methods=["GET", "POST"])
@login_required
def project_new():
    students_list = data("students")
    staff_list = data("staff")
    if request.method == "POST":
        payload = {
            "project_code": request.form.get("project_code","").strip(),
            "title": request.form.get("title","").strip(),
            "student_id": int(request.form["student_id"]) if request.form.get("student_id") else None,
            "domain": request.form.get("domain","").strip(),
            "technology": request.form.get("technology","").strip(),
            "staff_id": int(request.form["staff_id"]) if request.form.get("staff_id") else None,
            "priority": request.form.get("priority","Normal"),
            "status": request.form.get("status","Enquiry"),
            "start_date": request.form.get("start_date") or None,
            "deadline": request.form.get("deadline") or None,
            "amount": float(request.form.get("amount") or 0),
            "github_url": request.form.get("github_url","").strip(),
            "drive_url": request.form.get("drive_url","").strip(),
            "notes": request.form.get("notes","").strip(),
        }
        if not payload["title"]:
            flash("Project title is required.", "danger")
        else:
            insert("projects", payload)
            flash("Project created.", "success")
            return redirect(url_for("projects"))
    return render_template("project_form.html", project=None, students=students_list,
                           staff=staff_list, form_title="Add Project")


@app.route("/projects/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def project_edit(item_id):
    project = one("projects", item_id)
    if not project:
        return redirect(url_for("projects"))
    students_list = data("students")
    staff_list = data("staff")
    if request.method == "POST":
        payload = {
            "project_code": request.form.get("project_code","").strip(),
            "title": request.form.get("title","").strip(),
            "student_id": int(request.form["student_id"]) if request.form.get("student_id") else None,
            "domain": request.form.get("domain","").strip(),
            "technology": request.form.get("technology","").strip(),
            "staff_id": int(request.form["staff_id"]) if request.form.get("staff_id") else None,
            "priority": request.form.get("priority","Normal"),
            "status": request.form.get("status","Enquiry"),
            "start_date": request.form.get("start_date") or None,
            "deadline": request.form.get("deadline") or None,
            "amount": float(request.form.get("amount") or 0),
            "github_url": request.form.get("github_url","").strip(),
            "drive_url": request.form.get("drive_url","").strip(),
            "notes": request.form.get("notes","").strip(),
        }
        update("projects", item_id, payload)
        flash("Project updated.", "success")
        return redirect(url_for("projects"))
    return render_template("project_form.html", project=project, students=students_list,
                           staff=staff_list, form_title="Edit Project")


@app.post("/projects/<int:item_id>/delete")
@login_required
def project_delete(item_id):
    delete("projects", item_id)
    flash("Project deleted.", "success")
    return redirect(url_for("projects"))


@app.route("/payments")
@login_required
def payments():
    rows = data("payments")
    projects_list = data("projects")
    students_list = data("students")
    pmap = {p["id"]: p["title"] for p in projects_list}
    smap = {s["id"]: s["name"] for s in students_list}
    for r in rows:
        r["project_title"] = pmap.get(r.get("project_id"), "—")
        r["student_name"] = smap.get(r.get("student_id"), "—")
    return render_template("payments.html", payments=rows, projects=projects_list, students=students_list)


@app.post("/payments/new")
@login_required
def payment_new():
    payload = {
        "project_id": int(request.form["project_id"]) if request.form.get("project_id") else None,
        "student_id": int(request.form["student_id"]) if request.form.get("student_id") else None,
        "amount": float(request.form.get("amount") or 0),
        "payment_date": request.form.get("payment_date") or str(date.today()),
        "method": request.form.get("method","UPI"),
        "transaction_id": request.form.get("transaction_id","").strip(),
        "notes": request.form.get("notes","").strip(),
    }
    if payload["amount"] <= 0:
        flash("Payment amount must be greater than zero.", "danger")
    else:
        insert("payments", payload)
        flash("Payment recorded.", "success")
    return redirect(url_for("payments"))


@app.post("/payments/<int:item_id>/delete")
@login_required
def payment_delete(item_id):
    delete("payments", item_id)
    flash("Payment deleted.", "success")
    return redirect(url_for("payments"))


@app.route("/staff")
@login_required
def staff():
    return render_template("staff.html", staff=data("staff"))


@app.post("/staff/new")
@login_required
def staff_new():
    payload = {k: request.form.get(k,"").strip() for k in ["name","email","phone","role","status"]}
    if payload["name"]:
        insert("staff", payload)
        flash("Staff member added.", "success")
    return redirect(url_for("staff"))


@app.post("/staff/<int:item_id>/delete")
@login_required
def staff_delete(item_id):
    delete("staff", item_id)
    flash("Staff member deleted.", "success")
    return redirect(url_for("staff"))


@app.route("/reports")
@login_required
def reports():
    projects_list = data("projects")
    payments_list = data("payments")
    students_list = data("students")
    staff_list = data("staff")
    total = sum(float(p.get("amount") or 0) for p in projects_list)
    paid = sum(float(p.get("amount") or 0) for p in payments_list)
    by_status = {}
    for p in projects_list:
        by_status[p.get("status","Unknown")] = by_status.get(p.get("status","Unknown"), 0) + 1
    return render_template("reports.html", projects=projects_list, payments=payments_list,
                           students=students_list, staff=staff_list, total=total, paid=paid,
                           outstanding=max(total-paid,0), by_status=by_status)


@app.get("/api/summary")
@login_required
def api_summary():
    projects_list = data("projects")
    payments_list = data("payments")
    return jsonify({
        "students": len(data("students")),
        "projects": len(projects_list),
        "staff": len(data("staff")),
        "collected": sum(float(x.get("amount") or 0) for x in payments_list),
        "project_value": sum(float(x.get("amount") or 0) for x in projects_list),
    })


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


db_init()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8000)
