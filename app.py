
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response
import sqlite3, os, csv, io, datetime, uuid

APP_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(APP_DIR, "attendance.db")
ADMIN_PASSWORD = os.environ.get("FV_ADMIN_PASSWORD", "admin123")  # change in env for production

def init_db():
    first = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT,
        token TEXT UNIQUE,
        shift_start TEXT,
        shift_end TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY,
        employee_id INTEGER,
        action TEXT, -- IN or OUT
        timestamp TEXT,
        lat REAL,
        lon REAL,
        note TEXT
    )
    """)
    conn.commit()
    if first:
        # Prepopulate employees
        employees = [
            ("Ch. Aswad","token_aswad","09:00","00:00"),
            ("Muhammad Noor","token_noor","08:00","19:00"),
            ("Waheed Khan","token_waheed","08:00","19:00"),
            ("Muhammad Amir","token_amir","11:00","00:00"),
            ("Rashid Khan","token_rashid","09:00","12:00"),
            ("Saad","token_saad","09:00","12:00"),
            ("Zohaib Shah","token_zohaib","09:00","21:00")
        ]
        for name, token, s, e in employees:
            c.execute("INSERT OR IGNORE INTO employees (name, token, shift_start, shift_end) VALUES (?, ?, ?, ?)", (name, token, s, e))
        conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)
app.secret_key = os.environ.get("FV_SECRET_KEY", "devsecret")

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/link/<token>", methods=["GET","POST"])
def link(token):
    # employee check page
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM employees WHERE token=?", (token,))
    emp = c.fetchone()
    if not emp:
        conn.close()
        return "Invalid link/token", 404
    if request.method == "POST":
        action = request.form.get("action")
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        note = request.form.get("note","")
        ts = datetime.datetime.now().isoformat(timespec='seconds')
        c.execute("INSERT INTO records (employee_id, action, timestamp, lat, lon, note) VALUES (?, ?, ?, ?, ?, ?)",
                  (emp["id"], action, ts, lat or None, lon or None, note))
        conn.commit()
        conn.close()
        flash(f"{emp['name']} marked {action} at {ts}", "success")
        return redirect(url_for("link", token=token))
    # GET
    c.execute("SELECT * FROM records WHERE employee_id=? ORDER BY id DESC LIMIT 10", (emp["id"],))
    history = c.fetchall()
    conn.close()
    return render_template("employee.html", emp=emp, history=history)

@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        pw = request.form.get("password","")
        if pw == ADMIN_PASSWORD:
            resp = redirect(url_for("dashboard"))
            resp.set_cookie("fv_admin", "1")
            return resp
        flash("Invalid password", "danger")
    return render_template("admin_login.html")

def admin_required(f):
    from functools import wraps
    def wrapper(*args, **kwargs):
        if request.cookies.get("fv_admin") != "1":
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route("/admin/dashboard")
@admin_required
def dashboard():
    conn = get_db()
    c = conn.cursor()
    # today's date range
    today = datetime.date.today().isoformat()
    start = today + "T00:00:00"
    end = today + "T23:59:59"
    c.execute("""SELECT e.name, r.action, r.timestamp, r.lat, r.lon, r.note
                 FROM records r JOIN employees e ON r.employee_id=e.id
                 WHERE r.timestamp BETWEEN ? AND ?
                 ORDER BY r.timestamp DESC""", (start, end))
    rows = c.fetchall()
    # simple stats per employee
    c.execute("SELECT * FROM employees")
    emps = c.fetchall()
    stats = []
    for emp in emps:
        c.execute("SELECT COUNT(*) FROM records WHERE employee_id=? AND action='IN' AND timestamp BETWEEN ? AND ?", (emp["id"], start, end))
        ins = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM records WHERE employee_id=? AND action='OUT' AND timestamp BETWEEN ? AND ?", (emp["id"], start, end))
        outs = c.fetchone()[0]
        stats.append({"name": emp["name"], "ins": ins, "outs": outs})
    conn.close()
    return render_template("dashboard.html", rows=rows, stats=stats)

@app.route("/admin/export")
@admin_required
def export_csv():
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT r.id, e.name, r.action, r.timestamp, r.lat, r.lon, r.note
                 FROM records r JOIN employees e ON r.employee_id=e.id
                 ORDER BY r.timestamp DESC""")
    rows = c.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","name","action","timestamp","lat","lon","note"])
    for r in rows:
        writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6]])
    resp = Response(output.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=attendance_export.csv"
    conn.close()
    return resp

@app.route("/admin/employees")
@admin_required
def admin_employees():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM employees")
    emps = c.fetchall()
    conn.close()
    return render_template("employees.html", emps=emps)

@app.route("/admin/add_employee", methods=["POST"])
@admin_required
def add_employee():
    name = request.form.get("name")
    shift_start = request.form.get("shift_start","09:00")
    shift_end = request.form.get("shift_end","17:00")
    token = "token_" + uuid.uuid4().hex[:8]
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO employees (name, token, shift_start, shift_end) VALUES (?, ?, ?, ?)", (name, token, shift_start, shift_end))
    conn.commit()
    conn.close()
    flash("Added employee", "success")
    return redirect(url_for("admin_employees"))

if __name__ == "__main__":
    app.run(debug=True)
