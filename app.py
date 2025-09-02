from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for sessions

DB_NAME = "luggage.db"

# ---------- DATABASE INITIALIZATION ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # Lost luggage reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lost_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        passenger_id INTEGER,
        flight_no TEXT,
        description TEXT,
        last_seen TEXT,
        date_lost TEXT,
        status TEXT DEFAULT 'Pending',
        remarks TEXT
    )
    """)

    # Found luggage reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS found_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finder_name TEXT,
        contact TEXT,
        description TEXT,
        place_found TEXT,
        date_found TEXT
    )
    """)

    conn.commit()
    conn.close()


# Call init_db when starting
init_db()

# ---------- HOME ROUTE ----------
@app.route("/")
def home():
    return render_template("home.html")
    # ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = "passenger"  # default role for registration

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                           (name, email, password, role))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered!", "danger")
        finally:
            conn.close()

    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["name"] = user[1]
            session["role"] = user[4]

            flash("Login successful!", "success")

            if session["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("passenger_dashboard"))
        else:
            flash("Invalid credentials!", "danger")

    return render_template("login.html")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

# ---------- PASSENGER DASHBOARD ----------
@app.route("/passenger/dashboard")
def passenger_dashboard():
    if "user_id" not in session or session["role"] != "passenger":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lost_reports WHERE passenger_id=?", (session["user_id"],))
    reports = cursor.fetchall()
    conn.close()

    return render_template("passenger_dashboard.html", reports=reports, name=session["name"])


# ---------- REPORT LOST LUGGAGE ----------
@app.route("/passenger/report", methods=["GET", "POST"])
def report_luggage():
    if "user_id" not in session or session["role"] != "passenger":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        flight_no = request.form["flight_no"]
        description = request.form["description"]
        last_seen = request.form["last_seen"]
        date_lost = request.form["date_lost"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO lost_reports 
                          (passenger_id, flight_no, description, last_seen, date_lost, status, remarks) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (session["user_id"], flight_no, description, last_seen, date_lost, "Pending", ""))
        conn.commit()

        report_id = cursor.lastrowid
        conn.close()

        flash(f"Report submitted successfully! Your Report ID is {report_id}", "success")
        return redirect(url_for("passenger_dashboard"))

    return render_template("report_luggage.html")


# ---------- TRACK LUGGAGE ----------
@app.route("/passenger/track", methods=["GET", "POST"])
def track_luggage():
    status_data = None
    if request.method == "POST":
        report_id = request.form["report_id"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lost_reports WHERE id=?", (report_id,))
        status_data = cursor.fetchone()
        conn.close()

        if not status_data:
            flash("Invalid Report ID!", "danger")

    return render_template("track_luggage.html", status_data=status_data)

# ---------- ADMIN DASHBOARD ----------
@app.route("/admin/dashboard")
def admin_dashboard():
    if "user_id" not in session or session["role"] != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""SELECT lost_reports.id, users.name, lost_reports.flight_no, 
                      lost_reports.description, lost_reports.status, lost_reports.remarks
                      FROM lost_reports 
                      JOIN users ON lost_reports.passenger_id = users.id""")
    reports = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", reports=reports)


# ---------- UPDATE STATUS ----------
@app.route("/admin/update/<int:report_id>", methods=["GET", "POST"])
def update_status(report_id):
    if "user_id" not in session or session["role"] != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lost_reports WHERE id=?", (report_id,))
    report = cursor.fetchone()

    if request.method == "POST":
        new_status = request.form["status"]
        remarks = request.form["remarks"]
        cursor.execute("UPDATE lost_reports SET status=?, remarks=? WHERE id=?",
                       (new_status, remarks, report_id))
        conn.commit()
        conn.close()
        flash("Status updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    conn.close()
    return render_template("update_status.html", report=report)

# ---------- FINDER: Report Found Luggage ----------
@app.route("/finder/report", methods=["GET", "POST"])
def finder_report():
    if request.method == "POST":
        finder_name = request.form["finder_name"]
        contact = request.form["contact"]
        description = request.form["description"]
        place_found = request.form["place_found"]
        date_found = request.form["date_found"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO found_reports 
                          (finder_name, contact, description, place_found, date_found) 
                          VALUES (?, ?, ?, ?, ?)""",
                       (finder_name, contact, description, place_found, date_found))
        conn.commit()
        conn.close()

        flash("Thank you! Your found luggage report has been submitted.", "success")
        return redirect(url_for("finder_report"))

    return render_template("finder_report.html")
# ---------- ADMIN: View Found Luggage ----------
@app.route("/admin/found_reports")
def admin_found_reports():
    if "role" not in session or session["role"] != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("home"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM found_reports")
    reports = cursor.fetchall()
    conn.close()

    return render_template("admin_found_reports.html", reports=reports)

# ---------- ADMIN: Match Found to Lost ----------
@app.route("/admin/match/<int:found_id>", methods=["GET", "POST"])
def match_luggage(found_id):
    if "role" not in session or session["role"] != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("home"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Get found luggage details
    cursor.execute("SELECT * FROM found_reports WHERE id=?", (found_id,))
    found_item = cursor.fetchone()

    # Get all lost luggage reports still pending
    cursor.execute("SELECT id, description, last_seen, status FROM lost_reports WHERE status='Pending'")
    lost_reports = cursor.fetchall()

    if request.method == "POST":
        lost_id = request.form["lost_id"]

        # Update lost report status
        cursor.execute("UPDATE lost_reports SET status=?, remarks=? WHERE id=?",
                       ("Found", f"Matched with found report #{found_id}", lost_id))
        conn.commit()
        conn.close()

        flash(f"Lost report {lost_id} matched with found item {found_id}", "success")
        return redirect(url_for("admin_found_reports"))

    conn.close()
    return render_template("match_luggage.html", found_item=found_item, lost_reports=lost_reports)

# ---------- ADMIN: View Lost Reports ----------
@app.route("/admin/lost_reports")
def admin_lost_reports():
    if "role" not in session or session["role"] != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("home"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lost_reports")
    reports = cursor.fetchall()
    conn.close()

    return render_template("admin_lost_reports.html", reports=reports)


if __name__ == "__main__":
    app.run(debug=True)
