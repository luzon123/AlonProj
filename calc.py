import sqlite3
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
from flask import Flask, render_template, request, redirect, url_for, session
import time 
import os

# יצירת חיבור למסד נתונים SQLite
conn = sqlite3.connect('investment.db', check_same_thread=False)
cursor = conn.cursor()

# יצירת טבלה במסד נתונים אם לא קיימת
cursor.execute('''CREATE TABLE IF NOT EXISTS investment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    initial_investment REAL,
                    initial_investment_2 REAL,
                    initial_investment_3 REAL,
                    initial_investment_4 REAL,
                    shares REAL,
                    shares_2 REAL,
                    shares_3 REAL,
                    shares_4 REAL,
                    sp500_price REAL)''')

# יצירת אפליקציה של Flask
app = Flask(__name__)
app.secret_key = "supersecretkey"  # שנה את זה לסיסמה חזקה משלך

PASSWORD = "Yossi1105"  # שנה את הסיסמה הרצויה כאן

# פונקציה לקבלת ערך המניה הנוכחי של S&P 500, ולהמיר אותו לשקלים
def get_sp500_price(retries=3, delay=5):
    for attempt in range(retries):
        try:
            sp500 = yf.Ticker('^GSPC')
            sp500_history = sp500.history(period='1d')
            if sp500_history.empty:
                print("[!] Yahoo Finance returned empty data for S&P 500.")
                time.sleep(delay)
                continue
            sp500_price_in_usd = sp500_history['Close'].iloc[-1]
            exchange_rate = 3.8
            return sp500_price_in_usd * exchange_rate
        except Exception as e:
            print(f"[!] Error fetching S&P 500 price: {e}")
            time.sleep(delay)
    return None

# פונקציה לשמירת השקעה ראשונית (אם עדיין לא קיימת)
def save_initial_investment(investment, investment_2=None, investment_3=None, investment_4=None):
    cursor.execute("SELECT COUNT(*) FROM investment")
    count = cursor.fetchone()[0]

    if count == 0:
        sp500_price = get_sp500_price()

        shares = investment / sp500_price
        shares_2 = shares_3 = shares_4 = 0

        if investment_2:
            shares_2 = investment_2 / sp500_price
        if investment_3:
            shares_3 = investment_3 / sp500_price
        if investment_4:
            shares_4 = investment_4 / sp500_price

        cursor.execute("INSERT INTO investment (initial_investment, initial_investment_2, initial_investment_3, initial_investment_4, shares, shares_2, shares_3, shares_4, sp500_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (investment, investment_2, investment_3, investment_4, shares, shares_2, shares_3, shares_4, sp500_price))
        conn.commit()
        print(f"Initial investment(s) saved. You bought shares at S&P 500 price of ₪{sp500_price}.")
    else:
        print("The initial investment has already been saved.")

# פונקציה לעדכון ההשקעה

def update_investment():
    sp500_price = get_sp500_price()
    cursor.execute("SELECT id, initial_investment, initial_investment_2, initial_investment_3, initial_investment_4, shares, shares_2, shares_3, shares_4, sp500_price FROM investment ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()

    if result:
        initial_investment = result[1]
        initial_investment_2 = result[2]
        initial_investment_3 = result[3]
        initial_investment_4 = result[4]
        shares = result[5]
        shares_2 = result[6]
        shares_3 = result[7]
        shares_4 = result[8]

        new_investment = shares * sp500_price
        new_investment_2 = shares_2 * sp500_price
        new_investment_3 = shares_3 * sp500_price
        new_investment_4 = shares_4 * sp500_price
        profit_loss = new_investment - initial_investment
        profit_loss_2 = new_investment_2 - initial_investment_2
        profit_loss_3 = new_investment_3 - initial_investment_3
        profit_loss_4 = new_investment_4 - initial_investment_4

        cursor.execute("UPDATE investment SET sp500_price = ?, shares = ?, shares_2 = ?, shares_3 = ?, shares_4 = ? WHERE id = ?",
                       (sp500_price, shares, shares_2, shares_3, shares_4, result[0]))
        conn.commit()
        return initial_investment, initial_investment_2, initial_investment_3, initial_investment_4, shares, shares_2, shares_3, shares_4, new_investment, new_investment_2, new_investment_3, new_investment_4, profit_loss, profit_loss_2, profit_loss_3, profit_loss_4, sp500_price
    else:
        print("No investment found in the database to update.")
        return None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None

# דף התחברות בסיסמה
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('home'))
        else:
            return "סיסמה שגויה. נסה שוב."
    return '''<form method="POST">
                סיסמה: <input type="password" name="password">
                <input type="submit" value="היכנס">
              </form>'''

# דף הבית - דרוש סיסמה
@app.route('/')
def home():
    if not session.get('authenticated'):
        return redirect(url_for('login'))

    initial_investment, initial_investment_2, initial_investment_3, initial_investment_4, shares, shares_2, shares_3, shares_4, new_investment, new_investment_2, new_investment_3, new_investment_4, profit_loss, profit_loss_2, profit_loss_3, profit_loss_4, sp500_price = update_investment()

    if initial_investment is not None:
        return render_template('index.html', 
                               initial_investment=initial_investment, 
                               initial_investment_2=initial_investment_2,
                               initial_investment_3=initial_investment_3,
                               initial_investment_4=initial_investment_4,
                               shares=shares, 
                               shares_2=shares_2,
                               shares_3=shares_3,
                               shares_4=shares_4,
                               new_investment=new_investment,
                               new_investment_2=new_investment_2,
                               new_investment_3=new_investment_3,
                               new_investment_4=new_investment_4,
                               profit_loss=profit_loss,
                               profit_loss_2=profit_loss_2,
                               profit_loss_3=profit_loss_3,
                               profit_loss_4=profit_loss_4,
                               sp500_price=sp500_price)
    else:
        return "No investment found. Please save your initial investment first."

save_initial_investment(1066981, 361300, 250000, 100000)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)

conn.close()