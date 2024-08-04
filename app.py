from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import json
import sqlite3
from flask_session import Session

# Initialize the database with a users table if it doesn't already exist
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

# Initialize the Flask app
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem for session storage
app.config['SECRET_KEY'] = 'supersecretkey'  # Secret key for session encryption
Session(app)  # Initialize session management

# Helper function to get the filename for the user's expenses
def get_expenses_file(user_id):
    return f'expenses_{user_id}.json'

# Helper function to get the filename for the user's starting balance
def get_balance_file(user_id):
    return f'starting_balance_{user_id}.json'

# Save expenses to a JSON file
def save_expenses(user_id, expenses):
    with open(get_expenses_file(user_id), 'w') as f:
        json.dump(expenses, f)

# Load expenses from a JSON file, return an empty list if file not found
def load_expenses(user_id):
    try:
        with open(get_expenses_file(user_id), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Save the starting balance to a JSON file
def save_starting_balance(user_id, balance):
    with open(get_balance_file(user_id), 'w') as f:
        json.dump({'starting_balance': balance}, f)

# Load the starting balance from a JSON file, return 0 if file not found
def load_starting_balance(user_id):
    try:
        with open(get_balance_file(user_id), 'r') as f:
            data = json.load(f)
            return data.get('starting_balance', 0)
    except FileNotFoundError:
        return 0

# Route to handle both displaying the main page and processing form submissions
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    user_id = session['user_id']
    expenses = load_expenses(user_id)  # Load the user's expenses

    if request.method == 'POST':
        if 'set_balance' in request.form:
            # Handle setting the starting balance
            starting_balance = request.form.get('starting_balance')
            if starting_balance:
                try:
                    starting_balance = float(starting_balance)
                    save_starting_balance(user_id, starting_balance)
                except ValueError:
                    return "Invalid starting balance."

        elif 'amount' in request.form and 'expense' in request.form and 'date' in request.form:
            # Handle adding a new expense
            amount = request.form.get('amount')
            expense = request.form.get('expense')
            date = request.form.get('date')
            if amount and expense and date:
                try:
                    amount = float(amount)
                    new_expense = {
                        'amount': amount,
                        'category': expense,
                        'date': date
                    }
                    # Check for duplicate entry
                    existing_expense = next((e for e in expenses if e['amount'] == amount and e['category'] == expense and e['date'] == date), None)
                    if existing_expense:
                        return "Duplicate expense detected."

                    expenses.append(new_expense)
                    save_expenses(user_id, expenses)
                except ValueError:
                    return "Invalid amount."

        return redirect(url_for('index'))

    # Calculate total expenses and remaining balance
    total_expenses = sum(float(expense['amount']) for expense in expenses)
    starting_balance = load_starting_balance(user_id)
    remaining_balance = starting_balance - total_expenses

    return render_template('index.html', expenses=expenses, total_expenses=total_expenses, remaining_balance=remaining_balance, starting_balance=starting_balance)

# API route to handle deleting an expense
@app.route('/api/delete_expense/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401  # Return error if not logged in

    user_id = session['user_id']
    expenses = load_expenses(user_id)

    if 0 <= expense_id < len(expenses):
        del expenses[expense_id]
        save_expenses(user_id, expenses)

        # Recalculate total expenses and remaining balance
        total_expenses = sum(float(expense['amount']) for expense in expenses)
        starting_balance = load_starting_balance(user_id)
        remaining_balance = starting_balance - total_expenses

        return jsonify({
            'message': 'Deleted successfully',
            'total_expenses': total_expenses,
            'remaining_balance': remaining_balance
        }), 200
    else:
        return jsonify({'error': 'Invalid expense ID'}), 400

# Route to handle user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid credentials"

    return render_template('login.html')

# Route to handle user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists"
        finally:
            conn.close()
    
    return render_template('register.html')

# Route to handle user logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user_id from session
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)  # Run the Flask app in debug mode
