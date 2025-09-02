from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for sessions

DB_NAME = "luggage.db"

# ---------- DATABASE INITIALIZATION ----------
def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Users table (Passengers + Admins)
        cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('passenger', 'admin'))
        )
        """)

        # Lost luggage reports
        cursor.execute("""
        CREATE TABLE lost_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id INTEGER,
            description TEXT,
            location TEXT,
            date_lost TEXT,
            status TEXT DEFAULT 'Pending',
            remarks TEXT,
            FOREIGN KEY(passenger_id) REFERENCES users(id)
        )
        """)

        # Found luggage reports (by public/finder)
        cursor.execute("""
        CREATE TABLE found_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            location TEXT,
            date_found TEXT,
            contact TEXT
        )
        """)

        conn.commit()
        conn.close()
        print("Database initialized!")

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


if __name__ == "__main__":
    app.run(debug=True)
