import os
from flask import Flask, request, jsonify
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DB_URL = os.getenv("DATABASE_URL")
#skibidi
def db_conn():
    return psycopg2.connect(DB_URL)

def init_db():
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id SERIAL PRIMARY KEY,
            ip TEXT,
            country TEXT,
            region TEXT,
            city TEXT,
            isp TEXT,
            user_agent TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        conn.commit()

init_db()

def client_ip():
    if request.headers.get("CF-Connecting-IP"):
        return request.headers.get("CF-Connecting-IP")
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    if request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    return request.remote_addr or "unknown"

def geo_lookup(ip=None):
    url = f"http://ip-api.com/json/{ip or ''}?fields=status,message,query,country,regionName,city,isp"
    r = requests.get(url, timeout=5)
    data = r.json()
    if data.get("status") != "success":
        return {"error": data.get("message", "lookup failed")}
    return data

def save_to_db(data):
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO visitors (ip, country, region, city, isp, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (
            data.get("query"),
            data.get("country"),
            data.get("regionName"),
            data.get("city"),
            data.get("isp"),
            request.headers.get("User-Agent", "")
        ))
        conn.commit()

@app.route("/")
def home():
    data = geo_lookup()
    save_to_db(data)
    return (
        f"Your Public IP: {data.get('query')}\n"
        f"Country: {data.get('country')}\n"
        f"Region: {data.get('regionName')}\n"
        f"City: {data.get('city')}\n"
        f"ISP: {data.get('isp')}\n",
        200, {"Content-Type": "text/plain; charset=utf-8"}
    )

@app.route("/json")
def as_json():
    data = geo_lookup()
    save_to_db(data)
    return jsonify(data)

@app.route("/txt")
def as_txt():
    data = geo_lookup()
    save_to_db(data)
    return (data.get("query","unknown") + "\n", 200, {"Content-Type":"text/plain; charset=utf-8"})

@app.route("/stats")
def stats():
    with db_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS total FROM visitors;")
        total = cur.fetchone()["total"]
        cur.execute("""
            SELECT ip, country, region, city, isp, user_agent, created_at
            FROM visitors
            ORDER BY id DESC
            LIMIT 10;
        """)
        rows = cur.fetchall()
    return jsonify({"total": total, "latest": rows})

if __name__ == "__main__":
    # 本地測試用；在 Render 會用 gunicorn 啟動
    app.run(host="0.0.0.0", port=8000)

