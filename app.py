import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from home.routes import home_bp
from geralayout.routes import geralayout_bp
from documentos.routes import documentos_bp
from manuais.routes import manuais_bp
from comandos.routes import comandos_bp
from videos.routes import videos_bp


app = Flask(__name__)
app.secret_key = "chave-secreta"
DATABASE = "atividades.db"

# Rotas
app.register_blueprint(home_bp)
app.register_blueprint(geralayout_bp, url_prefix='/geralayout')
app.register_blueprint(documentos_bp, url_prefix='/documentos')
app.register_blueprint(manuais_bp, url_prefix='/manuais')
app.register_blueprint(comandos_bp, url_prefix='/comanados')
app.register_blueprint(videos_bp, url_prefix='/videos')


# Pastas
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GENERATED_FOLDER'] = 'generated'
DOCS_FOLDER = os.path.join(app.config['GENERATED_FOLDER'], 'docs')
####VIDEO_FOLDER = os.path.join('static', 'videos')
DOCS_FOLDER = os.path.join(app.config['GENERATED_FOLDER'], 'docs')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
###os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(DOCS_FOLDER, exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)


# -------------------- Atividades / Calendário --------------------
def init_db_activities():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        activity_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        break_hours TEXT DEFAULT '00:00',
        description TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db_activities()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/atividades")
def atividades():
    return render_template("atividades.html")

@app.route("/api/activities", methods=["GET", "POST"])
def api_activities():
    if request.method == "GET":
        date = request.args.get("date")
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM activities WHERE activity_date=? ORDER BY start_time", (date,)).fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    if request.method == "POST":
        data = request.get_json()
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO activities (company_id, project_id, activity_date, start_time, end_time, break_hours, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("company_id"),
            data.get("project_id"),
            data.get("activity_date"),
            data.get("start_time"),
            data.get("end_time"),
            data.get("break_hours", "00:00"),
            data.get("description", "")
        ))
        conn.commit()
        conn.close()
        return jsonify({"status":"ok"})

@app.route("/api/activities/<int:id>", methods=["DELETE"])
def api_delete_activity(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM activities WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status":"ok"})

# -------------------- Indicadores Mensais --------------------
def hhmm_to_minutes(hhmm):
    h, m = map(int, hhmm.split(":"))
    return h*60 + m

@app.route('/api/month_summary')
def month_summary():
    year = request.args.get('year')
    month = request.args.get('month')
    if not year or not month:
        return jsonify({"error": "Ano ou mês não informado"}), 400
    try:
        year = int(year)
        month = int(month)
    except ValueError:
        return jsonify({"error": "Ano ou mês inválido"}), 400
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT start_time, end_time, break_hours
        FROM activities
        WHERE strftime('%Y', activity_date)=? AND strftime('%m', activity_date)=?
    """, (str(year), f"{month:02d}")).fetchall()
    conn.close()
    total_activities = len(rows)
    total_minutes = 0
    for row in rows:
        try:
            start_min = hhmm_to_minutes(row["start_time"])
            end_min = hhmm_to_minutes(row["end_time"])
            break_min = hhmm_to_minutes(row["break_hours"] or "00:00")
            total_minutes += max(end_min - start_min - break_min, 0)
        except:
            continue
    total_hours_decimal = round(total_minutes / 60, 2)
    return jsonify({
        "total_activities": total_activities,
        "total_hours": total_hours_decimal
    })

# -------------------- Indicadores Diários para calendário --------------------
@app.route("/api/summary")
def api_summary():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        return jsonify({"events": [], "daysWithActivity": []})

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT activity_date, start_time, end_time, break_hours, id, company_id, project_id, description
        FROM activities
        WHERE activity_date BETWEEN ? AND ?
        ORDER BY activity_date, start_time
    """, (start, end)).fetchall()
    conn.close()

    events = []
    days_dict = {}

    def hhmm_to_decimal(hhmm):
        h, m = map(int, hhmm.split(":"))
        return h + m/60

    for row in rows:
        events.append({
            ##"id": row["id"],
            ##"title": f"{row['start_time']} - {row['end_time']} ({row['company_id']}/{row['project_id']})",
            ##"start": f"{row['activity_date']}T{row['start_time']}",
            ##"end": f"{row['activity_date']}T{row['end_time']}",
            ##"description": row["description"]
        }) 

        # Resumo por dia
        total_min = hhmm_to_decimal(row["end_time"]) - hhmm_to_decimal(row["start_time"])
        break_h = hhmm_to_decimal(row["break_hours"] or "00:00")
        total_hours = max(total_min - break_h, 0)

        if row["activity_date"] not in days_dict:
            days_dict[row["activity_date"]] = {"total_activities": 0, "total_hours": 0}
        days_dict[row["activity_date"]]["total_activities"] += 1
        days_dict[row["activity_date"]]["total_hours"] += total_hours

    # Formatar daysWithActivity
    daysWithActivity = [
        {"date": date, "total_activities": info["total_activities"], "total_hours": round(info["total_hours"], 2)}
        for date, info in days_dict.items()
    ]

    return jsonify({"events": events, "daysWithActivity": daysWithActivity})

# -------------------- Run --------------------
if __name__ == '__main__':
    app.run(debug=True)
