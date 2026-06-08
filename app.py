from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
from flask_login import current_user
import pickle
import numpy as np
import sqlite3
from datetime import datetime
import csv
import io

# ✅ LOGIN IMPORTS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

# ✅ EMAIL IMPORTS
import smtplib
from email.mime.text import MIMEText

# ✅ REAL-TIME IMPORT
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = "secret123"

socketio = SocketIO(app)

# ---------- LOGIN SETUP ----------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

users = {
    "laxmi": {"password": "12345"}
}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# ---------- LOAD MODEL ----------
model = pickle.load(open("model.pkl", "rb"))

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("fraud.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            result TEXT,
            time TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # ✅ ADMIN AUTO INSERT
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("laxmi", "12345"))
    except:
        pass

    conn.commit()
    conn.close()
init_db()
# ---------- EMAIL ----------
def send_email(amount):
    sender = "gudiya@gmail.com"
    password = "agpe abcd abcd rrjc"
    receiver = "yourgmail@gmail.com"

    try:
        msg = MIMEText(f"🚨 Fraud detected!\nAmount: ₹{amount}")
        msg["Subject"] = "Fraud Alert"
        msg["From"] = sender
        msg["To"] = receiver

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()

    except Exception as e:
        print("Email Error:", e)
    
# ---------- AI INSIGHTS ----------
def generate_insights(history, safe_count, fraud_count):
    total = safe_count + fraud_count
    insights = []

    fraud_percent = (fraud_count / total * 100) if total > 0 else 0

    if fraud_percent > 50:
        insights.append("🚨 Critical fraud activity detected")
    elif fraud_percent > 30:
        insights.append("⚠️ High fraud activity detected")
    else:
        insights.append("✅ Transactions are mostly safe")

    if history:
        max_amt = max(h[0] for h in history)
        insights.append(f"💰 Highest Transaction: ₹{int(max_amt):,}")

    insights.append(f"📊 Fraud Rate: {round(fraud_percent,2)}%")

    return insights

# ---------- SMART AI ASSISTANT ----------
@app.route("/ask_ai", methods=["POST"])
@login_required
def ask_ai():
    data = request.get_json()
    question = data.get("question", "").lower()

    if not question:
        return jsonify({"answer": "❗ Please ask something meaningful."})

    # -------- FETCH DATA FROM DB --------
    conn = sqlite3.connect("fraud.db")
    cur = conn.cursor()
    cur.execute("SELECT amount, result, time FROM transactions")
    history = cur.fetchall()
    conn.close()

    total = len(history)
    fraud_count = sum(1 for h in history if "Fraud" in h[1])
    safe_count = sum(1 for h in history if "Safe" in h[1])
    fraud_percent = (fraud_count / total * 100) if total > 0 else 0

    amounts = [h[0] for h in history] if history else [0]
    max_amt = max(amounts)
    avg_amt = sum(amounts) / len(amounts) if history else 0

    # -------- BASIC DEFINITIONS --------
    if "what is fraud" in question or ("fraud" in question and "what" in question):
        answer = "🚨 Fraud is an unauthorized or suspicious transaction where money is used without permission."

    elif "what is safe" in question or "safe transaction" in question:
        answer = "✅ Safe transactions are normal, low-risk payments made by the genuine user."

    elif "what is risk" in question:
        answer = "⚠️ Risk means the probability of a transaction being fraudulent based on behavior, amount, and pattern."

    # -------- SMART ANALYTICS --------
    elif "summary" in question or "report" in question:
        answer = f"""
📊 Total Transactions: {total}
✅ Safe: {safe_count}
🚨 Fraud: {fraud_count}
📉 Fraud Rate: {round(fraud_percent,2)}%
💰 Avg Amount: ₹{int(avg_amt):,}
"""

    elif "fraud rate" in question:
        answer = f"📉 Current fraud rate is {round(fraud_percent,2)}%"

    elif "highest" in question or "max" in question:
        answer = f"💰 Highest transaction recorded is ₹{int(max_amt):,}"

    elif "average" in question:
        answer = f"📊 Average transaction amount is ₹{int(avg_amt):,}"

    elif "risk" in question:
        if fraud_percent > 50:
            answer = "🚨 System is at HIGH RISK due to many fraud transactions."
        elif fraud_percent > 30:
            answer = "⚠️ Moderate risk detected. Be cautious."
        else:
            answer = "✅ System is mostly safe."

    elif "recent" in question:
        recent = history[-5:]
        formatted = "\n".join([f"₹{int(h[0])} → {h[1]}" for h in recent])
        answer = f"🕒 Last Transactions:\n{formatted}"

    elif "prevent" in question or "avoid fraud" in question:
        answer = """
🔐 Fraud Prevention Tips:
• Enable OTP verification
• Avoid public Wi-Fi
• Monitor bank alerts
• Use secure payment apps
"""

    # -------- DEFAULT --------
    else:
        answer = """
🤖 I can help you with:
• What is fraud / safe / risk
• Fraud report & summary
• Fraud rate
• Highest / average transaction
• Recent activity
• Prevention tips

Try: "What is fraud?" or "Show summary"
"""

    return jsonify({"answer": answer})
# ---------- LOGIN ----------
@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # ✅ ADMIN LOGIN (hardcoded)
        if username == "laxmi" and password == "12345":
            user = User(username)
            login_user(user)
            return redirect(url_for("main"))

        # ✅ DATABASE LOGIN (normal users)
        conn = sqlite3.connect("fraud.db")
        cur = conn.cursor()

        cur.execute("SELECT password FROM users WHERE username=?", (username,))
        data = cur.fetchone()

        conn.close()

        if data:
            if data[0] == password:
                user = User(username)
                login_user(user)
                return redirect(url_for("main"))
            else:
                return render_template("home.html", error="Wrong Password")
        else:
            return render_template("home.html", error="User Not Found")

    return render_template("home.html")
# ---------- SIGNUP ----------
@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("fraud.db")
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))

        except:
            conn.close()
            return render_template("signup.html", error="User already exists")

    return render_template("signup.html")

# ---------- DASHBOARD ----------
@app.route('/main')
@login_required
def main():
    conn = sqlite3.connect("fraud.db")
    cur = conn.cursor()
    cur.execute("SELECT amount, result, time FROM transactions")
    history = cur.fetchall()
    conn.close()
    # 📊 AI CHART DATA
    labels = [h[2] for h in history]   # time
    values = [h[0] for h in history]   # amount
    results = [1 if "Fraud" in h[1] else 0 for h in history]
    safe_count = sum(1 for h in history if "Safe" in h[1])
    fraud_count = sum(1 for h in history if "Fraud" in h[1])
    insights = generate_insights(history, safe_count, fraud_count)

    return render_template(
        'index.html',
        safe_count=safe_count,
        fraud_count=fraud_count,
        history=history,
        insights=insights,
        labels=labels,
        values=values,
        results=results,
        last_result=None,
        last_amount=None,
        last_description=None,
        risk_score=None
    )
# ---------- PREDICT ----------
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    val = float(request.form['f1'])
    data = np.array([[val] * 30])

    prediction = model.predict(data)[0]

    if val > 200000 or prediction == 1:
        result = "Fraud"
        description = "🚨 High risk! This transaction may be fraudulent."
        send_email(val)

    else: 
        result = "Safe"
        description = "✅ This transaction is low risk."

    # 🔥 AI RISK SCORING
    if val < 2000:
     risk_score = 10
    elif val < 10000:
     risk_score = 30
    elif val < 50000:
     risk_score = 50
    elif val < 100000:
     risk_score = 70
    elif val < 200000:
     risk_score = 80
    else:
     risk_score = 95
    # -------- INSERT INTO DB --------
    conn = sqlite3.connect("fraud.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (amount, result, time) VALUES (?, ?, ?)",
        (val, result, datetime.now().strftime("%H:%M:%S"))
    )
    conn.commit()
    conn.close()

    # -------- SOCKET.IO EMIT --------
    socketio.emit("new_transaction", {
        "amount": val,
        "result": result,
        "description": description,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    # -------- RETURN FOR DASHBOARD --------
    conn = sqlite3.connect("fraud.db")
    cur = conn.cursor()
    cur.execute("SELECT amount, result, time FROM transactions")
    history = cur.fetchall()
    conn.close()
# 📊 AI CHART DATA AGAIN
    labels = [h[2] for h in history]
    values = [h[0] for h in history]
    results = [1 if "Fraud" in h[1] else 0 for h in history]
    safe_count = sum(1 for h in history if "Safe" in h[1])
    fraud_count = sum(1 for h in history if "Fraud" in h[1])
    insights = generate_insights(history, safe_count, fraud_count)

    # Agar AJAX call (live update), return empty response
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return ""

    # Else render full template
    return render_template(
    'index.html',
    safe_count=safe_count,
    fraud_count=fraud_count,
    history=history,
    insights=insights,
    labels=labels,
    values=values,
    results=results,
    last_result=result,
    last_amount=val,
    last_description=description,
    risk_score=risk_score
)
# ---------- ADMIN PANEL ----------
@app.route("/admin")
@login_required
def admin():

    if current_user.id != "laxmi":
        return "❌ Access Denied"

    conn = sqlite3.connect("fraud.db")
    cur = conn.cursor()

    search = request.args.get("search")

    # 👤 Users
    if search:
        cur.execute("SELECT id, username FROM users WHERE username LIKE ?", ('%' + search + '%',))
    else:
        cur.execute("SELECT id, username FROM users")

    users = cur.fetchall()

    # 💳 Transactions
    cur.execute("SELECT amount, result, time FROM transactions ORDER BY id DESC")
    transactions = cur.fetchall()

    # 📊 Summary
    fraud_count = sum(1 for t in transactions if "Fraud" in t[1])
    safe_count = sum(1 for t in transactions if "Safe" in t[1])

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        transactions=transactions,
        fraud_count=fraud_count,
        safe_count=safe_count
    )
# ---------- DELETE USER ----------
@app.route("/delete_user", methods=["POST"])
@login_required
def delete_user():

    if current_user.id != "laxmi":
        return "❌ Unauthorized"

    user_id = request.form["id"]

    conn = sqlite3.connect("fraud.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))
# ---------- CSV ----------
@app.route("/download_csv")
@login_required
def download_csv():
    conn = sqlite3.connect("fraud.db")
    cur = conn.cursor()
    cur.execute("SELECT amount, result, time FROM transactions")
    data = cur.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Amount", "Result", "Time"])
    writer.writerows(data)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="transactions.csv"
    )

# ---------- LOGOUT ----------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ---------- RUN ----------
if __name__ == "__main__":
    socketio.run(app, debug=True)
