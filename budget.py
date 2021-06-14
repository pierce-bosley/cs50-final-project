'''Flask app and session initialization, webapp routes, HTTP error handling'''

import locale
import datetime

from tempfile import mkdtemp
from cs50 import SQL
from flask import Flask, flash, session, redirect, url_for, render_template, request
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, usd, parse_pattern, calculate_funds, get_pattern_day
from helpers import last_day, next_occurance, str_to_date, get_farthest, seed_required

app = Flask(__name__)

# The following is borrowed from the cs50 web track Finances source code

app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.after_request
def after_request(response):
    '''Ensure requests are not cached'''
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = 0
    response.headers['Pragma'] = 'no-cache'
    return response

app.jinja_env.filters['usd'] = usd

app.config['SESSION_FILE_DIR'] = mkdtemp()
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

bdb = SQL('sqlite:///database/budget.db')

# End of what was borrowed from the cs50 web track Finances source code

locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

app.secret_key = b'\xc4R\x94Oi\x8d\xf5*\xd1\x02\xafu\x14\xfaH\xdd'

@app.route("/")
@app.route("/home")
@app.route("/index")
@login_required
@seed_required
def index():
    '''Home page'''
    today = datetime.date.today()
    funds = bdb.execute('SELECT "spending", "savings", "last_update" ' \
                        'FROM "funds" ' \
                        'WHERE "user_username" = ' \
                        '(SELECT "username" FROM "users" WHERE "id" = :session_id)',
                        session_id=session.get('user_id'))
    transactions = bdb.execute('SELECT "id", "value", "type", "destination", "pattern", "day" ' \
                               'FROM "schedule" ' \
                               'WHERE "user_username" = ' \
                               '(SELECT "username" FROM "users" WHERE "id" = :session_id)',
                               session_id=session.get('user_id'))
    last_update = str_to_date(funds[0].get('last_update'))
    next_date = last_update
    cur_spending, cur_savings = funds[0].get('spending'), funds[0].get('savings')
    if last_update < today:
        cur_spending, cur_savings = calculate_funds(last_update,
                                                    cur_spending,
                                                    cur_savings,
                                                    transactions,
                                                    today)
        to_delete = []
        for transaction in transactions:
            next_date = next_occurance(last_update,
                                       transaction.get('pattern'),
                                       transaction.get('day'))
            while next_date <= today:
                if 'single' in transaction.get('pattern'):
                    bdb.execute('DELETE FROM "schedule" WHERE "id" = :trans_id',
                                trans_id=transaction.get('id'))
                    to_delete.append(transaction.get('id'))
                    break
                transaction['day'] = get_pattern_day(next_date, transaction.get('pattern'))
                next_date = next_occurance(next_date,
                                           transaction.get('pattern'),
                                           transaction.get('day'))
            bdb.execute('UPDATE "schedule" SET "day" = :day WHERE "id" = :trans_id',
                        day=transaction['day'],
                        trans_id=transaction.get('id'))
        transactions[:] = [trans for trans in transactions if trans.get('id') not in to_delete]
        bdb.execute('UPDATE "funds" ' \
                    'SET "spending" = :spending, ' \
                        '"savings" = :savings, ' \
                        '"last_update" = :last_update ' \
                    'WHERE "user_username" = ' \
                    '(SELECT "username" FROM "users" WHERE "id" = :session_id)',
                    spending=cur_spending,
                    savings=cur_savings,
                    last_update=today,
                    session_id=session.get('user_id'))
    cur_proj_date = today + datetime.timedelta(days=1)
    last_proj_date = cur_proj_date - datetime.timedelta(days=1)
    proj_savings = cur_savings
    next_cur_spending, next_proj_savings = cur_spending, proj_savings
    target_date = get_farthest(transactions)
    to_delete = []
    while cur_proj_date <= target_date:
        next_cur_spending, next_proj_savings = calculate_funds(last_proj_date,
                                                               next_cur_spending,
                                                               next_proj_savings,
                                                               transactions,
                                                               cur_proj_date)
        for transaction in transactions:
            if 'single' in transaction.get('pattern'):
                if cur_proj_date == next_occurance(last_proj_date,
                                                   transaction.get('pattern'),
                                                   transaction.get('day')):
                    to_delete.append(transaction.get('id'))
        transactions[:] = [trans for trans in transactions if trans.get('id') not in to_delete]
        if cur_spending > next_cur_spending:
            cur_spending = next_cur_spending
            proj_savings = next_proj_savings
            if cur_spending <= 0:
                cur_spending = 0
        cur_proj_date += datetime.timedelta(days=1)
        last_proj_date += datetime.timedelta(days=1)
    return render_template('index.html',
                           proj_spending=usd(cur_spending),
                           proj_savings=usd(proj_savings),
                           cur_savings=usd(cur_savings))

@app.route('/new-instant', methods=['GET', 'POST'])
@login_required
@seed_required
def new_instant():
    '''Add a one-time new-instant'''
    if request.method == 'GET':
        return redirect(url_for('index'))
    amount = round(float(request.form.get('trans-value')), 2)
    trans_type = request.form.get('trans-type')
    destination = request.form.get('destination')
    if destination == 'spending':
        if trans_type == 'debit':
            amount *= -1
        bdb.execute('UPDATE "funds" ' \
                    'SET "spending" = "spending" + :amount ' \
                    'WHERE "user_username" = ' \
                    '(SELECT "username" FROM "users" WHERE "id" = :session_id)',
                    amount=amount, session_id=session.get('user_id'))
    elif destination == 'savings':
        if trans_type == 'credit':
            amount *= -1
        bdb.execute('UPDATE "funds" ' \
                    'SET "spending" = "spending" + :amount, ' \
                        '"savings" = "savings" - :amount ' \
                    'WHERE "user_username" = ' \
                    '(SELECT "username" FROM "users" WHERE "id" = :session_id)',
                    amount=amount, session_id=session.get('user_id'))
    return redirect(url_for('index'))

@app.route('/schedule', methods=['GET', 'POST'])
@login_required
@seed_required
def schedule():
    '''View schedule of recurring transactions'''
    if request.method == 'POST':
        to_delete = request.form.getlist('delete')
        for trans_id in to_delete:
            bdb.execute('DELETE FROM "schedule" WHERE "id" = :trans_id', trans_id=trans_id)
        return redirect(url_for('schedule'))
    transactions = bdb.execute('SELECT "id", "value", "type", "destination", "pattern", "day" ' \
                               'FROM "schedule" ' \
                               'WHERE "user_username" = ' \
                               '(SELECT "username" FROM "users" WHERE "id" = :session_id)',
                               session_id=session.get('user_id'))
    scheduled_credits = []
    scheduled_debits = []
    for transaction in transactions:
        transaction['amount'] = usd(transaction.pop('value'))
        transaction['next'] = str(next_occurance(datetime.date.today(),
                                                 transaction.get('pattern'),
                                                 transaction.pop('day')))
        transaction['frequency'] = parse_pattern(transaction.pop('pattern'),
                                                 transaction.get('next'))
        transaction['next'] = (transaction['next'][8:] + '-' +
                               transaction['next'][5:7] + '-' +
                               transaction['next'][0:4])
        if transaction.get('type') == 'credit':
            if transaction.get('destination') == 'spending':
                transaction['source'] = 'income'
                transaction.pop('destination')
                transaction.pop('type')
                scheduled_credits.append(transaction)
            elif transaction.get('destination') == 'savings':
                transaction['destination'] = 'savings'
                transaction.pop('type')
                scheduled_debits.append(transaction)
        elif transaction.get('type') == 'debit':
            if transaction.get('destination') == 'spending':
                transaction['destination'] = 'payment'
                transaction.pop('type')
                scheduled_debits.append(transaction)
            elif transaction.get('destination') == 'savings':
                transaction['source'] = 'savings'
                transaction.pop('destination')
                transaction.pop('type')
                scheduled_credits.append(transaction)
    return render_template('schedule.html', credits=scheduled_credits, debits=scheduled_debits)

@app.route('/new-scheduled', methods=['GET', 'POST'])
@login_required
@seed_required
def new_scheduled():
    '''Add scheduled charges, income, and savings deposits and withdrawls'''
    if request.method == 'POST':
        frequency = request.form.get('frequency')
        start_date = request.form.get('start-date')
        if frequency == 'recurring':
            pattern = request.form.get('selected-pattern')
            if pattern == 'yearly':
                if '-02-29' in start_date:
                    pattern = 'yearly' + request.form.get('non-leap-year')
                else:
                    pattern = 'yearly1'
                start_date = str_to_date(start_date).timetuple().tm_yday
            elif pattern == 'monthly':
                pattern = 'monthly' + request.form.get('monthly-pattern')
                if pattern[-1:] == '1':
                    start_date = 1
                elif pattern[-1:] == '2':
                    start_date = last_day(int(start_date[0:4]), int(start_date[5:7]))
                else:
                    start_date = str_to_date(start_date).day
            elif pattern == 'weekly':
                pattern = 'weekly' + request.form.get('weekly-pattern')
                start_date = str_to_date(start_date).toordinal()
            else:
                start_date = str_to_date(start_date).toordinal()
        else:
            pattern = 'single'
            start_date = str_to_date(start_date).toordinal()
        bdb.execute('INSERT INTO "schedule" ' \
                    '("user_username", "value", "type", "destination", "pattern", "day") ' \
                    'VALUES ((SELECT "username" FROM "users" WHERE "id" = :session_id), ' \
                    ':trans_value, :trans_type, :destination, :pattern, :start_date)',
                    session_id=session.get('user_id'),
                    trans_value=round(float(request.form.get('trans-value')), 2),
                    trans_type=request.form.get('trans-type'),
                    destination=request.form.get('destination'),
                    pattern=pattern,
                    start_date=start_date)
        return redirect(url_for('schedule'))
    return render_template('new-scheduled.html', today=datetime.date.today())

@app.route('/login', methods=['GET', 'POST'])
def login():
    '''Login and begin a new user session'''
    if session.get('_flashes'):
        flashes = session.get('_flashes')
        session.clear()
        session['_flashes'] = flashes
    else:
        session.clear()
    if request.method == 'POST':
        username = request.form.get('username').lower()
        rows = bdb.execute('SELECT * FROM "users" WHERE "username" = :username',
                           username=username)
        if len(rows) != 1 or not check_password_hash(rows[0]['hash'], request.form.get('password')):
            flash('Incorrect username or password')
            return redirect(url_for('login'))
        session['user_id'] = rows[0]['id']
        session['seeded'] = rows[0]['seeded']
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    '''Log current session out'''
    if session.get('_flashes'):
        flashes = session.get('_flashes')
        session.clear()
        session['_flashes'] = flashes
    else:
        session.clear()
    flash('You have been logged out successfully')
    return redirect(url_for('login'))

@app.route('/changepass', methods=['GET', 'POST'])
@login_required
def changepass():
    '''Allow user to change their password'''
    if request.method == 'POST':
        old_pass = request.form.get('old-password')
        new_hash = generate_password_hash(request.form.get('new-password'))
        old_hash = bdb.execute('SELECT "hash" FROM "users" WHERE "id" = :session_id',
                              session_id=session.get('user_id'))
        if not check_password_hash(old_hash[0]['hash'], old_pass):
            flash('The provided current password was incorrect')
            return redirect(url_for('changepass'))
        bdb.execute('UPDATE "users" SET "hash" = :new_hash WHERE "id" = :session_id',
                   new_hash=new_hash, session_id=session.get('user_id'))
        flash('Password successfully changed')
        return redirect(url_for('index'))
    return render_template('changepass.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    '''Register new user'''
    if request.method == 'POST':
        username = request.form.get('username').lower()
        pwordhash = generate_password_hash(request.form.get('password'))
        if bdb.execute('SELECT * FROM "users" WHERE "username" = :username',
                       username=username):
            flash('Username already exists')
            return redirect(url_for('register'))
        if bdb.execute('INSERT INTO "users" ("username", "hash") VALUES (:username, :pwordhash)',
                       username=username,
                       pwordhash=pwordhash):
            bdb.execute('INSERT INTO "funds" ("user_username", "last_update") ' \
                        'VALUES (:username, :today)',
                        username=username,
                        today=str(datetime.date.today()))
            rows = bdb.execute('SELECT * FROM "users" WHERE "username" = :username',
                               username=username)
            session['user_id'] = rows[0]['id']
            return redirect(url_for('starting_funds'))
    return render_template('register.html')

@app.route('/starting-funds', methods=['GET', 'POST'])
@login_required
def starting_funds():
    '''Get starting funds from newly registered user'''
    if request.method == 'POST':
        seed = round(float(request.form.get('seed')), 2)
        bdb.execute('UPDATE "funds" ' \
                    'SET "spending" = "spending" + :seed ' \
                    'WHERE "user_username" = ' \
                    '(SELECT "username" FROM "users" WHERE "id" = :session_id)',
                    seed=seed, session_id=session.get('user_id'))
        bdb.execute('UPDATE "users" SET "seeded" = 1 WHERE "id" = :session_id',
                    session_id=session.get('user_id'))
        session['seeded'] = 1
        return redirect(url_for('index'))
    return render_template('starting-funds.html')

# The following is borrowed from the cs50 web track Finances source code

def errorhandler(error):
    '''Handle error'''
    if not isinstance(error, HTTPException):
        error = InternalServerError()
    return f'Error occurred: {error.name}, {error.code}'


for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

# End of what was borrowed from the cs50 web track Finances source code
