from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import math
import webbrowser
import os
import bcrypt      # pip install bcrypt

app = Flask(_name_, template_folder='templates')
CORS(app)

# --- MySQL connection (edit creds if needed) ---
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="hida@1234",
        database="cynlock"
    )

# --- Keystroke similarity (more sensitive) ---
def keystroke_similarity(stored, current):
    try:
        sd = float(stored.get('avgDwell', 0))
        sf = float(stored.get('avgFlight', 0))
        cd = float(current.get('avgDwell', 0))
        cf = float(current.get('avgFlight', 0))

        dwell_diff = abs(sd - cd)
        flight_diff = abs(sf - cf)

        # make dwell more important
        weighted_diff = (dwell_diff * 0.75) + (flight_diff * 0.25)

        # Convert difference to score: 100 at perfect match, 0 when weighted_diff >= 120
        # (tune 120 multiplier to be stricter/looser)
        score = max(0.0, 100.0 - (weighted_diff * 1.2))
        return round(score, 2)
    except Exception as e:
        print("keystroke_similarity error:", e)
        return 0.0

# --- Face similarity placeholder (lower default if missing) ---
def face_score_from_value(val):
    # If frontend sends a face_score use it (0-100)
    if val is None:
        return 40.0   # lower default if no face provided
    try:
        return float(val)
    except:
        return 40.0

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/enroll', methods=['POST'])
def enroll():
    """
    Expects JSON:
    {
      "username": "alice",
      "password": "plainpassword",
      "keystroke": {"avgDwell": number, "avgFlight": number},
      "geo": {"lat": number, "lon": number},
      "face": "data:image/...base64..."   (optional)
    }
    """
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')   # plaintext from frontend (temporarily over localhost)
        ks = data.get('keystroke', {})
        geo = data.get('geo', {})
        face = data.get('face')

        if not username or not password:
            return jsonify({'error': 'username and password required'}), 400

        # Hash password with bcrypt
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        avgDwell = float(ks.get('avgDwell', 0))
        avgFlight = float(ks.get('avgFlight', 0))
        lat = float(geo.get('lat', 0))
        lon = float(geo.get('lon', 0))

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, password_hash, avgDwell, avgFlight, face, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              password_hash = VALUES(password_hash),
              avgDwell = VALUES(avgDwell),
              avgFlight = VALUES(avgFlight),
              face = VALUES(face),
              latitude = VALUES(latitude),
              longitude = VALUES(longitude)
        """, (username, password_hash, avgDwell, avgFlight, face, lat, lon))
        conn.commit()
        cur.close()
        conn.close()

        print(f"[ENROLL] {username} | dwell={avgDwell}, flight={avgFlight}, lat={lat}, lon={lon}")
        return jsonify({'message': f'User {username} enrolled successfully!'}), 200

    except Exception as e:
        print("Enroll error:", e)
        return jsonify({'error': 'Enrollment failed', 'details': str(e)}), 500

@app.route('/verify', methods=['POST'])
def verify():
    """
    Expects JSON:
    {
      "username": "alice",
      "password": "plainpassword",   # optional: can be required if you want to validate password
      "keystroke": {...},
      "geo": {...},
      "face": "..." or "face_score": number (0-100)
    }
    """
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')   # optional: check if provided
        ks = data.get('keystroke', {})
        geo = data.get('geo', {})
        face = data.get('face')
        face_score_override = data.get('face_score')  # optional numeric from frontend

        if not username:
            return jsonify({'error': 'username required'}), 400

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            print(f"[VERIFY] user {username} not found")
            return jsonify({'result': 'block', 'reason': 'user not found'}), 404

        # OPTIONAL: verify password if provided (recommended)
        if password:
            stored_hash = user.get('password_hash', '')
            if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                print(f"[VERIFY] password mismatch for {username}")
                return jsonify({'result': 'block', 'reason': 'password incorrect'}), 403

        # keystroke score
        kscore = keystroke_similarity({'avgDwell': user['avgDwell'], 'avgFlight': user['avgFlight']}, ks)

        # geo score (tighter)
        lat = geo.get('lat', 0)
        lon = geo.get('lon', 0)
        dist = math.sqrt((user['latitude'] - lat)*2 + (user['longitude'] - lon)*2)
        if dist < 0.01:
            geoscore = 100
        elif dist < 0.03:
            geoscore = 60
        else:
            geoscore = 0

        # face
        fscore = face_score_from_value(face_score_override)
        # if actual face data was sent and stored, you could compute a better fscore

        # Weighted total (tune these weights as needed)
        total = round((kscore * 0.55) + (fscore * 0.25) + (geoscore * 0.20), 2)

        # stricter thresholds
        if total >= 75:
            result = 'allow'
        elif total >= 55:
            result = 'mfa'
        else:
            result = 'block'

        # debug print
        print(f"[VERIFY] {username} | stored_dwell={user['avgDwell']}, stored_flight={user['avgFlight']}")
        print(f"         current_dwell={ks.get('avgDwell')}, current_flight={ks.get('avgFlight')}")
        print(f"         k:{kscore} f:{fscore} g:{geoscore} -> total:{total} -> {result}")

        return jsonify({
            'username': username,
            'keystroke_score': kscore,
            'face_score': fscore,
            'geo_score': geoscore,
            'total_score': total,
            'result': result
        }), 200

    except Exception as e:
        print("Verify error:", e)
        return jsonify({'error': 'Verification failed', 'details': str(e)}), 500


if _name_ == '_main_':
    # open browser only on the first run
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        webbrowser.open("http://127.0.0.1:5000/")
    app.run(host='127.0.0.1', port=5000, debug=True)