from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
import requests
import datetime
import sqlite3
import threading
import time
from functools import wraps

app = Flask(__name__)
app.secret_key = 'change_this_to_a_strong_random_secret_key'  # CHANGE THIS!

# ==================== CONFIG ====================
YOUR_SITE_URL = "https://teamdev-sapi.onrender.com"  # CHANGE TO YOUR ACTUAL SITE URL (e.g. https://teamdev.sbs)
PING_INTERVAL = 10  # seconds

# Database initialization
def init_db():
    conn = sqlite3.connect('api.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (
        key TEXT PRIMARY KEY,
        created_at TIMESTAMP,
        created_by TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_used TEXT,
        url TEXT,
        timestamp TIMESTAMP,
        ip TEXT
    )''')
    # Insert default key if not exists
    c.execute('INSERT OR IGNORE INTO keys (key, created_at, created_by) VALUES (?, ?, ?)',
              ('teamdevf', datetime.datetime.now(), 'initial'))
    conn.commit()
    conn.close()

init_db()

DOWNLOADER_API = "https://socialdownloder2.anshapi.workers.dev/?url={}"

# ==================== AUTO PING SYSTEM ====================
def auto_ping():
    while True:
        try:
            requests.get(YOUR_SITE_URL + "/ping", timeout=10)
            print(f"[{datetime.datetime.now()}] Auto-ping sent to {YOUR_SITE_URL}/ping")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Auto-ping failed: {e}")
        time.sleep(PING_INTERVAL)

# Start auto-ping in background
threading.Thread(target=auto_ping, daemon=True).start()

# ==================== PING ROUTE ====================
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
        if c.fetchone() is None:
            conn.close()
            return jsonify({
                "statusCode": 401,
                "error": "Invalid or revoked key",
                "message": "Contact For Key - @MR_ARMAN_08"
            }), 401
        conn.close()
        
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
    
    ip = request.remote_addr or 'unknown'
    timestamp = datetime.datetime.now()
    
    # Log the request
    conn = sqlite3.connect('api.db')
    c = conn.cursor()
    c.execute('INSERT INTO logs (key_used, url, timestamp, ip) VALUES (?, ?, ?, ?)',
              (key, url, timestamp, ip))
    conn.commit()
    conn.close()
    
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            encoded_url = requests.utils.quote(url, safe='')
            resp = requests.get(DOWNLOADER_API.format(encoded_url), timeout=30)
            data = resp.json()
            
            # Check if downloader returned error
            if data.get('statusCode') != 200:
                if attempt < max_retries:
                    time.sleep(2)  # wait before retry
                    continue
                else:
                    return jsonify({
                        "statusCode": 500,
                        "error": "Video not found or service unavailable",
                        "message": "Contact For Key - @MR_ARMAN_08"
                    }), 500
            
            # Extract video medias
            video_medias = [m for m in data.get('medias', []) if m['type'] == 'video' and not m.get('is_audio', False)]
            if not video_medias:
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                else:
                    return jsonify({
                        "statusCode": 404,
                        "error": "No downloadable video found",
                        "message": "Contact For Key - @MR_ARMAN_08"
                    }), 404
            
            # Select highest quality (highest bandwidth)
            best_video = max(video_medias, key=lambda m: m.get('bandwidth', 0))
            download_link = best_video['url']
            
            return jsonify({
                "statusCode": 200,
                "download_link": download_link,
                "credits": "https://teamdev.sbs"
            })
        
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            else:
                return jsonify({
                    "statusCode": 500,
                    "error": "Internal server error after retries",
                    "message": "Contact For Key - @MR_ARMAN_08"
                }), 500

# ==================== ADMIN PANEL ====================
@app.route('/teamdev/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'ad@ad':
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            return '<h3>Invalid password!</h3><a href="/teamdev/admin/login">Try again</a>'
    
    return '''
    <h2>Admin Login</h2>
    <form method="post">
        Password: <input type="password" name="password"><br><br>
        <input type="submit" value="Login">
    </form>
    '''

@app.route('/teamdev/admin')
@require_admin
def admin_panel():
    conn = sqlite3.connect('api.db')
    c = conn.cursor()
    
    c.execute('SELECT key, created_at, created_by FROM keys ORDER BY created_at DESC')
    keys = c.fetchall()
    
    c.execute('SELECT id, key_used, url, timestamp, ip FROM logs ORDER BY timestamp DESC LIMIT 100')
    logs = c.fetchall()
    
    conn.close()
    
    return render_template_string('''
    <h1>TeamDev Admin Panel</h1>
    <p><a href="{{ url_for('admin_logout') }}">Logout</a></p>
    
    <h2>API Keys</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>Key</th><th>Created At</th><th>Created By</th><th>Actions</th></tr>
        {% for k in keys %}
        <tr>
            <td>{{ k[0] }}</td>
            <td>{{ k[1] }}</td>
            <td>{{ k[2] }}</td>
            <td>
                <form method="post" action="{{ url_for('delete_key') }}" style="display:inline;">
                    <input type="hidden" name="key" value="{{ k[0] }}">
                    <button type="submit" onclick="return confirm('Delete this key?')">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
    
    <h3>Create New Key</h3>
    <form method="post" action="{{ url_for('create_key') }}">
        New Key: <input type="text" name="new_key" required>
        <input type="submit" value="Create Key">
    </form>
    
    <h2>Recent Activities (Last 100)</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>ID</th><th>Key</th><th>URL</th><th>Time</th><th>IP</th></tr>
        {% for log in logs %}
        <tr>
            <td>{{ log[0] }}</td>
            <td>{{ log[1] }}</td>
            <td><a href="{{ log[2] }}" target="_blank">{{ log[2][:60] }}...</a></td>
            <td>{{ log[3] }}</td>
            <td>{{ log[4] }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <hr>
    <p>Credits: <a href="https://teamdev.sbs">https://teamdev.sbs</a></p>
    <p>Telegram: <a href="https://t.me/team_x_og">t.me/team_x_og</a> | Contact: @MR_ARMAN_08</p>
    ''', keys=keys, logs=logs)

@app.route('/teamdev/admin/create_key', methods=['POST'])
@require_admin
def create_key():
    new_key = request.form.get('new_key')
    if new_key:
        conn = sqlite3.connect('api.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO keys (key, created_at, created_by) VALUES (?, ?, ?)',
                      (new_key, datetime.datetime.now(), 'admin'))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/teamdev/admin/delete_key', methods=['POST'])
@require_admin
def delete_key():
    key_to_delete = request.form.get('key')
    if key_to_delete and key_to_delete != 'teamdevf':  # optional: protect default key
        conn = sqlite3.connect('api.db')
        c = conn.cursor()
        c.execute('DELETE FROM keys WHERE key = ?', (key_to_delete,))
        conn.commit()
        conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/teamdev/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
