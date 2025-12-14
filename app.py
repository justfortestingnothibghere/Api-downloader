from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
import requests
import datetime
import sqlite3
import threading
import time
from functools import wraps

app = Flask(__name__)
app.secret_key = 'change_this_to_a_strong_random_secret_key'

# ==================== CONFIG ====================
YOUR_SITE_URL = "https://teamdev-sapi.onrender.com"
PING_INTERVAL = 10

DOWNLOADER_API = "https://socialdownloder2.anshapi.workers.dev/?url={}"

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect('api.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            created_at TIMESTAMP,
            created_by TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_used TEXT,
            url TEXT,
            timestamp TIMESTAMP,
            ip TEXT
        )
    ''')
    c.execute(
        'INSERT OR IGNORE INTO keys VALUES (?, ?, ?)',
        ('teamdevf', datetime.datetime.now(), 'initial')
    )
    conn.commit()
    conn.close()

init_db()

# ==================== AUTO PING ====================
def auto_ping():
    while True:
        try:
            requests.get(YOUR_SITE_URL + "/ping", timeout=10)
        except:
            pass
        time.sleep(PING_INTERVAL)

threading.Thread(target=auto_ping, daemon=True).start()

# ==================== PING ====================
@app.route('/ping')
def ping():
    return "pong", 200

# ==================== DECORATORS ====================
def require_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.args.get('key')
        if not key:
            return jsonify({
                "statusCode": 400,
                "error": "Missing key",
                "message": "Contact For Key - @MR_ARMAN_08"
            }), 400

        conn = sqlite3.connect('api.db')
        c = conn.cursor()
        c.execute('SELECT key FROM keys WHERE key = ?', (key,))
        valid = c.fetchone()
        conn.close()

        if not valid:
            return jsonify({
                "statusCode": 401,
                "error": "Invalid key",
                "message": "Contact For Key - @MR_ARMAN_08"
            }), 401

        return f(key, *args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ==================== MAIN API ====================
@app.route('/api/v1/teamdev/')
@require_key
def download(key):
    url = request.args.get('url')
    if not url:
        return jsonify({
            "statusCode": 400,
            "error": "Missing url parameter"
        }), 400

    conn = sqlite3.connect('api.db')
    c = conn.cursor()
    c.execute(
        'INSERT INTO logs (key_used, url, timestamp, ip) VALUES (?, ?, ?, ?)',
        (key, url, datetime.datetime.now(), request.remote_addr)
    )
    conn.commit()
    conn.close()

    try:
        encoded_url = requests.utils.quote(url, safe='')
        resp = requests.get(DOWNLOADER_API.format(encoded_url), timeout=30)

        data = resp.json()

        if data.get('statusCode') != 200:
            return jsonify({
                "statusCode": 500,
                "error": "Downloader service error"
            }), 500

        # ✅ FIXED VIDEO FILTER
        video_medias = [
            m for m in data.get('medias', [])
            if m.get('type') == 'video' and m.get('extension') == 'mp4'
        ]

        if not video_medias:
            return jsonify({
                "statusCode": 404,
                "error": "No downloadable video found"
            }), 404

        # Take first available video (Instagram usually gives best first)
        best_video = video_medias[0]

        return jsonify({
            "statusCode": 200,
            "download_link": best_video.get('url'),
            "credits": "https://teamdev.sbs"
        })

    except Exception as e:
        return jsonify({
            "statusCode": 500,
            "error": "Internal server error"
        }), 500

# ==================== ADMIN PANEL ====================
@app.route('/teamdev/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == 'ad@ad':
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        return "Invalid password"

    return '''
    <form method="post">
        <input type="password" name="password">
        <input type="submit">
    </form>
    '''

@app.route('/teamdev/admin')
@require_admin
def admin_panel():
    conn = sqlite3.connect('api.db')
    c = conn.cursor()
    c.execute('SELECT * FROM keys')
    keys = c.fetchall()
    c.execute('SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50')
    logs = c.fetchall()
    conn.close()

    return render_template_string("""
    <h2>Keys</h2>
    {{ keys }}
    <h2>Logs</h2>
    {{ logs }}
    """, keys=keys, logs=logs)

@app.route('/teamdev/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# ==================== RUN ====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
