import json
import sqlite3
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session

# Initialize database
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)''')
    conn.commit()
    conn.close()

# Initialize Flask app
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'supersecretkey'
Session(app)

# Helper functions for expenses
def save_expenses(user_id, expenses):
    with open(f'expenses_{user_id}.json', 'w') as f:
        json.dump(expenses, f)

def load_expenses(user_id):
    try:
        with open(f'expenses_{user_id}.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid credentials, please try again."
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Index route
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    expenses = load_expenses(user_id)

    # Ensure expenses is not None
    if expenses is None:
        expenses = []

    # Calculate total expenses
    total_expenses = sum(float(expense['amount']) if expense['amount'] else 0.0 for expense in expenses)

    # Retrieve starting balance from session or set default
    starting_balance = session.get('starting_balance', 0.0)
    remaining_balance = starting_balance - total_expenses

    if request.method == 'POST':
        if 'set_balance' in request.form:
            # Handle setting the starting balance
            starting_balance = float(request.form.get('starting_balance', 0.0))
            session['starting_balance'] = starting_balance
            remaining_balance = starting_balance - total_expenses
        else:
            # Handle adding/updating expenses
            updating = request.form.get('updating')
            expense_id = int(request.form.get('expense_id')) if request.form.get('expense_id') else None
            amount = request.form.get('amount')
            expense = request.form.get('expense')
            date = request.form.get('date')

            new_expense = {
                'amount': amount,
                'category': expense,
                'date': date
            }

            if updating == 'true' and expense_id is not None:
                expenses[expense_id] = new_expense
            else:
                expenses.append(new_expense)

            save_expenses(user_id, expenses)

            # Update total expenses and remaining balance after POST
            total_expenses = sum(float(expense['amount']) if expense['amount'] else 0.0 for expense in expenses)
            remaining_balance = starting_balance - total_expenses

    return render_template('index.html', total_expenses=total_expenses, remaining_balance=remaining_balance, expenses=expenses)

# Delete expense API route
@app.route('/api/delete_expense/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = session['user_id']
    expenses = load_expenses(user_id)

    if 0 <= expense_id < len(expenses):
        del expenses[expense_id]
        save_expenses(user_id, expenses)

        total_expenses = sum(float(expense['amount']) if expense['amount'] else 0.0 for expense in expenses)
        remaining_balance = session.get('starting_balance', 0.0) - total_expenses

        return jsonify({
            'message': 'Deleted successfully',
            'total_expenses': total_expenses,
            'remaining_balance': remaining_balance
        }), 200
    else:
        return jsonify({'error': 'Invalid expense ID'}), 400

# Initialize the database and run the app
init_db()

if __name__ == '__main__':
    app.run(debug=True)
