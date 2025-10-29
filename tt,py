from flask import Flask, request, jsonify, render_template
import os
import webbrowser
import threading

app = Flask(_name_)

# In-memory data
# users structure:
# users[username] = {
#   "password": "...",
#   "geolocation": "lat,lon" or "Unknown",
#   "typing_speed": float(ms_per_char) or None
# }
users = {}
attempts = {}

# Configuration for typing-speed validation/comparison
MIN_MS_PER_CHAR = 5        # minimum plausible ms/char (very fast)
MAX_MS_PER_CHAR = 2000     # maximum plausible ms/char for a real typing event
TYPING_TOLERANCE = 0.30    # 30% tolerance: verify_speed must be within ±30% of baseline

# === Serve Frontend ===
@app.route('/')
def home():
    return render_template('index.html')


# === Enrollment ===
@app.route('/enroll', methods=['POST'])
def enroll():
    data = request.get_json()
    username = (data.get('username') or "").strip()
    password = data.get('password') or ""
    geolocation = data.get('geolocation', 'Unknown')
    # Accept typingSpeed optionally during enrollment (ms per char expected)
    raw_typing = data.get('typingSpeed', None)

    if not username or not password or not geolocation:
        return jsonify({"message": "All fields required including location"}), 400

    # Attempt to parse typing speed if provided
    typing_speed = None
    if raw_typing is not None:
        try:
            typing_speed = float(raw_typing)
        except Exception:
            typing_speed = None

    # Validate typing speed if present; otherwise allow enroll but mark baseline as None
    if typing_speed is not None:
        if typing_speed < MIN_MS_PER_CHAR or typing_speed > MAX_MS_PER_CHAR:
            # Unreasonable typing speed reported — ignore and tell user to type properly
            typing_speed = None
            msg = ("Enrollment saved, but typing-speed value looked invalid. "
                   "Please type your password naturally when enrolling next time so keystroke profile can be recorded.")
        else:
            msg = f"✅ {username} enrolled successfully at {geolocation} with typing baseline {typing_speed} ms/char."
    else:
        msg = f"✅ {username} enrolled successfully at {geolocation}. (typing baseline not recorded)"

    users[username] = {
        "password": password,
        "geolocation": geolocation,
        "typing_speed": typing_speed
    }
    attempts[username] = 0
    return jsonify({"message": msg})


# === Verification ===
@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json()
    username = (data.get('username') or "").strip()
    password = data.get('password') or ""
    raw_typing = data.get('typingSpeed', None)
    geolocation = data.get('geolocation', 'Unknown')

    if not username or not password:
        return jsonify({"message": "Please fill all fields"}), 400

    if username not in users:
        return jsonify({"message": "User not enrolled."}), 404

    # Block check
    if attempts.get(username, 0) >= 3:
        return jsonify({"message": "🚫 Account blocked after 3 failed attempts."})

    # Password check
    if users[username]["password"] != password:
        attempts[username] += 1
        remaining = max(0, 3 - attempts[username])
        return jsonify({"message": f"❌ Wrong password. {remaining} attempts left."}), 401

    # Location verification (basic tolerance)
    enrolled_loc = users[username].get("geolocation", "Unknown")
    if enrolled_loc == "Unknown" or geolocation == "Unknown":
        loc_match = True
    else:
        try:
            e_lat, e_lon = map(float, enrolled_loc.split(","))
            v_lat, v_lon = map(float, geolocation.split(","))
            # roughly within ~0.1 degrees (~11km) considered a match (adjust if needed)
            loc_match = abs(e_lat - v_lat) < 0.1 and abs(e_lon - v_lon) < 0.1
        except Exception:
            loc_match = False

    if not loc_match:
        attempts[username] += 1
        remaining = max(0, 3 - attempts[username])
        return jsonify({"message": f"⚠ Location mismatch detected. {remaining} attempts left."}), 403

    # Typing-speed handling
    typing_speed = None
    if raw_typing is not None:
        try:
            typing_speed = float(raw_typing)
        except Exception:
            typing_speed = None

    # If the client sent an obviously invalid typing speed (very large due to stale timer),
    # ask the user to retype so we get a fresh value instead of trusting the huge number.
    if typing_speed is None:
        # No typing info sent; accept login but notify baseline requirement
        attempts[username] = 0
        baseline = users[username].get("typing_speed")
        if baseline is None:
            return jsonify({"message": "✅ Access granted, but no typing profile available. Consider re-enrolling with typing data."})
        else:
            return jsonify({"message": "✅ Access granted."})

    if typing_speed < MIN_MS_PER_CHAR or typing_speed > (MAX_MS_PER_CHAR * 10):
        # If it's totally unrealistic (e.g. extremely big because user didn't retype),
        # require the user to type again to get valid typingSpeed; do not consume attempt.
        return jsonify({"message": "⚠ Typing speed reading looks invalid. Please focus and type the password now, then press VERIFY again."}), 400

    # If baseline exists, compare within tolerance
    baseline = users[username].get("typing_speed")
    if baseline is None:
        # No baseline to compare to: accept but suggest re-enrollment
        attempts[username] = 0
        # Save current typing speed as a baseline optionally to improve next time
        users[username]["typing_speed"] = typing_speed
        return jsonify({"message": ("✅ Access granted. No prior typing baseline existed — current typing "
                                    "speed recorded as baseline for future verifications.")})

    # Compare
    diff = abs(typing_speed - baseline)
    if baseline == 0:
        rel_diff = float('inf')
    else:
        rel_diff = diff / baseline

    if rel_diff <= TYPING_TOLERANCE:
        attempts[username] = 0
        return jsonify({"message": f"✅ Access granted for {username}. Typing speed: {typing_speed} ms/char (baseline {baseline})."})
    else:
        attempts[username] += 1
        remaining = max(0, 3 - attempts[username])
        return jsonify({"message": (f"❌ Keystroke pattern mismatch (baseline {baseline} ms/char vs {typing_speed} ms/char). "
                                    f"{remaining} attempts left.")}), 401


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if _name_ == '_main_':
    threading.Timer(1, open_browser).start()
    app.run(debug=False, use_reloader=False)
from flask import Flask, request, jsonify, render_template
import os
import webbrowser
import threading

app = Flask(_name_)

# In-memory data
# users structure:
# users[username] = {
#   "password": "...",
#   "geolocation": "lat,lon" or "Unknown",
#   "typing_speed": float(ms_per_char) or None
# }
users = {}
attempts = {}

# Configuration for typing-speed validation/comparison
MIN_MS_PER_CHAR = 5        # minimum plausible ms/char (very fast)
MAX_MS_PER_CHAR = 2000     # maximum plausible ms/char for a real typing event
TYPING_TOLERANCE = 0.30    # 30% tolerance: verify_speed must be within ±30% of baseline

# === Serve Frontend ===
@app.route('/')
def home():
    return render_template('index.html')


# === Enrollment ===
@app.route('/enroll', methods=['POST'])
def enroll():
    data = request.get_json()
    username = (data.get('username') or "").strip()
    password = data.get('password') or ""
    geolocation = data.get('geolocation', 'Unknown')
    # Accept typingSpeed optionally during enrollment (ms per char expected)
    raw_typing = data.get('typingSpeed', None)

    if not username or not password or not geolocation:
        return jsonify({"message": "All fields required including location"}), 400

    # Attempt to parse typing speed if provided
    typing_speed = None
    if raw_typing is not None:
        try:
            typing_speed = float(raw_typing)
        except Exception:
            typing_speed = None

    # Validate typing speed if present; otherwise allow enroll but mark baseline as None
    if typing_speed is not None:
        if typing_speed < MIN_MS_PER_CHAR or typing_speed > MAX_MS_PER_CHAR:
            # Unreasonable typing speed reported — ignore and tell user to type properly
            typing_speed = None
            msg = ("Enrollment saved, but typing-speed value looked invalid. "
                   "Please type your password naturally when enrolling next time so keystroke profile can be recorded.")
        else:
            msg = f"✅ {username} enrolled successfully at {geolocation} with typing baseline {typing_speed} ms/char."
    else:
        msg = f"✅ {username} enrolled successfully at {geolocation}. (typing baseline not recorded)"

    users[username] = {
        "password": password,
        "geolocation": geolocation,
        "typing_speed": typing_speed
    }
    attempts[username] = 0
    return jsonify({"message": msg})


# === Verification ===
@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json()
    username = (data.get('username') or "").strip()
    password = data.get('password') or ""
    raw_typing = data.get('typingSpeed', None)
    geolocation = data.get('geolocation', 'Unknown')

    if not username or not password:
        return jsonify({"message": "Please fill all fields"}), 400

    if username not in users:
        return jsonify({"message": "User not enrolled."}), 404

    # Block check
    if attempts.get(username, 0) >= 3:
        return jsonify({"message": "🚫 Account blocked after 3 failed attempts."})

    # Password check
    if users[username]["password"] != password:
        attempts[username] += 1
        remaining = max(0, 3 - attempts[username])
        return jsonify({"message": f"❌ Wrong password. {remaining} attempts left."}), 401

    # Location verification (basic tolerance)
    enrolled_loc = users[username].get("geolocation", "Unknown")
    if enrolled_loc == "Unknown" or geolocation == "Unknown":
        loc_match = True
    else:
        try:
            e_lat, e_lon = map(float, enrolled_loc.split(","))
            v_lat, v_lon = map(float, geolocation.split(","))
            # roughly within ~0.1 degrees (~11km) considered a match (adjust if needed)
            loc_match = abs(e_lat - v_lat) < 0.1 and abs(e_lon - v_lon) < 0.1
        except Exception:
            loc_match = False

    if not loc_match:
        attempts[username] += 1
        remaining = max(0, 3 - attempts[username])
        return jsonify({"message": f"⚠ Location mismatch detected. {remaining} attempts left."}), 403

    # Typing-speed handling
    typing_speed = None
    if raw_typing is not None:
        try:
            typing_speed = float(raw_typing)
        except Exception:
            typing_speed = None

    # If the client sent an obviously invalid typing speed (very large due to stale timer),
    # ask the user to retype so we get a fresh value instead of trusting the huge number.
    if typing_speed is None:
        # No typing info sent; accept login but notify baseline requirement
        attempts[username] = 0
        baseline = users[username].get("typing_speed")
        if baseline is None:
            return jsonify({"message": "✅ Access granted, but no typing profile available. Consider re-enrolling with typing data."})
        else:
            return jsonify({"message": "✅ Access granted."})

    if typing_speed < MIN_MS_PER_CHAR or typing_speed > (MAX_MS_PER_CHAR * 10):
        # If it's totally unrealistic (e.g. extremely big because user didn't retype),
        # require the user to type again to get valid typingSpeed; do not consume attempt.
        return jsonify({"message": "⚠ Typing speed reading looks invalid. Please focus and type the password now, then press VERIFY again."}), 400

    # If baseline exists, compare within tolerance
    baseline = users[username].get("typing_speed")
    if baseline is None:
        # No baseline to compare to: accept but suggest re-enrollment
        attempts[username] = 0
        # Save current typing speed as a baseline optionally to improve next time
        users[username]["typing_speed"] = typing_speed
        return jsonify({"message": ("✅ Access granted. No prior typing baseline existed — current typing "
                                    "speed recorded as baseline for future verifications.")})

    # Compare
    diff = abs(typing_speed - baseline)
    if baseline == 0:
        rel_diff = float('inf')
    else:
        rel_diff = diff / baseline

    if rel_diff <= TYPING_TOLERANCE:
        attempts[username] = 0
        return jsonify({"message": f"✅ Access granted for {username}. Typing speed: {typing_speed} ms/char (baseline {baseline})."})
    else:
        attempts[username] += 1
        remaining = max(0, 3 - attempts[username])
        return jsonify({"message": (f"❌ Keystroke pattern mismatch (baseline {baseline} ms/char vs {typing_speed} ms/char). "
                                    f"{remaining} attempts left.")}), 401


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if _name_ == '_main_':
    threading.Timer(1, open_browser).start()
    app.run(debug=False, use_reloader=False)