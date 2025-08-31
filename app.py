from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

def client_ip():
    # Prefer proxy headers if you run behind Cloudflare/Nginx
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

@app.route("/")
def home():
    data = geo_lookup()
    return (
        f"Your Public IP: {data.get('query')}\n"
        f"Country: {data.get('country')}\n"
        f"Region: {data.get('regionName')}\n"
        f"City: {data.get('city')}\n"
        f"ISP: {data.get('isp')}\n"
    ), 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route("/json")
def as_json():
    return jsonify(geo_lookup())

@app.route("/txt")
def as_txt():
    data = geo_lookup()
    return (data.get("query","unknown") + "\n", 200, {"Content-Type":"text/plain; charset=utf-8"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
