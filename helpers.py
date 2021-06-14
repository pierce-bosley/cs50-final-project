'''Helper functions'''

import datetime
from functools import wraps
from flask import redirect, session, url_for

# The following is borrowed from the cs50 web track Finances source code

def login_required(func):
    '''
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    '''
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated_function

def usd(value):
    '''Format value as USD'''
    return f'${value:,.2f}'

# End of what was borrowed from the cs50 web track Finances source code

def seed_required(func):
    '''Decorate routes to require user to have entered a starting amount of money.'''
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not session.get('seeded') or not int(session.get('seeded')):
            return redirect(url_for('starting_funds'))
        return func(*args, **kwargs)
    return decorated_function

def parse_pattern(pattern, date):
    '''Make pattern string more user frendly'''
    frequency = None
    if pattern == 'yearly1':
        frequency = 'Annually on ' + date[5:]
    if pattern == 'yearly2':
        frequency = 'Annually on ' + date[5:] + ' (02-28)'
    if pattern == 'yearly3':
        frequency = 'Annually on ' + date[5:] + ' (03-01)'
    if pattern == 'monthly1':
        frequency = 'First of every month'
    if pattern == 'monthly2':
        frequency = 'Last of every month'
    if pattern == 'monthly3':
        frequency = make_ordinal(int(date[8:])) + ' of every month'
    if pattern == 'weekly1':
        frequency = 'Every ' + get_weekday(date)
    if pattern == 'weekly2':
        frequency = 'Every other ' + get_weekday(date)
    if pattern == 'weekly3':
        frequency = 'Every third ' + get_weekday(date)
    if pattern == 'weekly4':
        frequency = 'Every forth ' + get_weekday(date)
    if pattern == 'daily':
        frequency = 'Every day'
    if pattern == 'single':
        frequency = 'Non-recurring'
    return frequency

# The following is borrowed from StackOverflow user Florian Brucker

def make_ordinal(day):
    '''
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    '''
    day = int(day)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(day % 10, 4)]
    if 11 <= (day % 100) <= 13:
        suffix = 'th'
    return str(day) + suffix

# End of what was borrowed from StackOverflow user Florian Brucker

def calculate_funds(last_update, spending, savings, transactions, target_date):
    '''Calculate spending and savings based on all transactions up to target_date'''
    next_date = last_update
    for transaction in transactions:
        next_date = next_occurance(last_update,
                                   transaction.get('pattern'),
                                   transaction.get('day'))
        while next_date <= target_date:
            spending, savings = apply_transaction(transaction, spending, savings)
            next_date = next_occurance(next_date,
                                       transaction.get('pattern'),
                                       transaction.get('day'))
            if 'single' in transaction.get('pattern'):
                break
    return round(float(spending), 2), round(float(savings), 2)

def get_weekday(date):
    '''Get day of week string for date object or 'YYYY-MM-DD' string'''
    switcher = {
        0: 'Monday',
        1: 'Tuesdy',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday'
    }
    if isinstance(date, str):
        date = str_to_date(date)
    return switcher.get(date.weekday())

def last_day(year, month):
    '''Returns the number of days in the given month'''
    if month == 2:
        return 29 if is_leap_year(year) else 28
    if month % 2 == 0:
        return 30 if month <= 7 else 31
    return 31 if month <= 7 else 30

def is_leap_year(year):
    '''Returns true if year is leap year, else false'''
    return False if year % 4 != 0 else year % 400 == 0 if year % 100 == 0 else True

def next_occurance(working_date, pattern, pattern_day):
    '''Returns the date of the next occurrance'''
    next_date = working_date
    if 'yearly' in pattern:
        next_date = yearly_next(working_date, int(pattern[-1:]), pattern_day)
    elif 'monthly' in pattern:
        next_date = monthly_next(working_date, int(pattern[-1:]), pattern_day)
    elif 'weekly' in pattern:
        next_date = weekly_next(working_date, int(pattern[-1:]), pattern_day)
    elif 'daily' in pattern:
        next_date = working_date + datetime.timedelta(days=1)
    elif 'single' in pattern:
        next_date = datetime.date.fromordinal(pattern_day)
    return next_date

def yearly_next(working_date, pattern, pattern_day):
    '''Returns the date of the next occurance for yearly patterns'''
    this_year = working_date.year
    next_year = working_date.year + 1
    if pattern == 2:
        if working_date >= datetime.date(this_year, 2, last_day(this_year, 2)):
            next_date = datetime.date(next_year, 2, last_day(next_year, 2))
        else:
            next_date = datetime.date(this_year, 2, last_day(this_year, 2))
    elif pattern == 3:
        if is_leap_year(this_year):
            if working_date >= datetime.date(this_year, 2, 29):
                next_date = datetime.date(next_year, 3, 1)
            else:
                next_date = datetime.date(this_year, 2, 29)
        elif working_date >= datetime.date(this_year, 3, 1):
            if is_leap_year(next_year):
                next_date = datetime.date(next_year, 2, 29)
            else:
                next_date = datetime.date(next_year, 3, 1)
        else:
            next_date = datetime.date(this_year, 3, 1)
    elif working_date.timetuple().tm_yday >= pattern_day:
        next_date = datetime.date(next_year, 1, 1) + datetime.timedelta(days=pattern_day - 1)
    else:
        next_date = datetime.date(this_year, 1, 1) + datetime.timedelta(days=pattern_day - 1)
    return next_date

def monthly_next(working_date, pattern, pattern_day):
    '''Returns the date of the next occurance for monthly patterns'''
    today = working_date.day
    this_month = working_date.month
    if this_month == 12:
        next_month = 1
        year = working_date.year + 1
    else:
        next_month = working_date.month + 1
        year = working_date.year
    if pattern == 2:
        if today == last_day(year, this_month):
            next_date = datetime.date(year, next_month, last_day(year, next_month))
        else:
            next_date = datetime.date(year,
                                      this_month,
                                      last_day(working_date.year, working_date.month))
    elif pattern == 3:
        if today >= pattern_day:
            next_date = datetime.date(year,
                                      next_month,
                                      min(last_day(year, next_month), pattern_day))
        else:
            next_date = datetime.date(year, this_month, pattern_day)
    else:
        next_date = datetime.date(year, next_month, 1)
    return next_date

def weekly_next(working_date, pattern, pattern_day):
    '''Returns the date of the next occurance for weekly patterns'''
    next_date = datetime.date.fromordinal(pattern_day)
    while working_date < next_date:
        next_date -= datetime.timedelta(days=7 * pattern)
    while working_date >= next_date:
        next_date += datetime.timedelta(days=7 * pattern)
    return next_date

def str_to_date(date):
    '''Convert 'YYYY-MM-DD' string to datetime.date object'''
    year = int(date[0:4])
    month = int(date[5:7])
    day = int(date[8:])
    return datetime.date(year, month, day)

def get_pattern_day(date, pattern):
    '''Convert the date into a pattenred int'''
    if pattern == 'yearly':
        day = date.timetuple().tm_yday
    elif pattern == 'monthly':
        day = date.day
    else:
        day= date.toordinal()
    return day

def apply_transaction(transaction, spending, savings):
    '''Apply the transaction to funds'''
    if transaction.get('destination') == 'spending':
        if transaction.get('type') == 'credit':
            spending += transaction.get('value')
        elif transaction.get('type') == 'debit':
            spending -= transaction.get('value')
    elif transaction.get('destination') == 'savings':
        if transaction.get('type') == 'credit':
            spending -= transaction.get('value')
            savings += transaction.get('value')
        elif transaction.get('type') == 'debit':
            spending += transaction.get('value')
            savings -= transaction.get('value')
    return round(float(spending), 2), round(float(savings), 2)

def get_farthest(transactions):
    '''Returns the date of the transaction with the furthest out next occurance'''
    today = datetime.date.today()
    next_trans_date = today
    furthest_trans_date = today
    for transaction in transactions:
        next_trans_date = next_occurance(today, transaction.get('pattern'), transaction.get('day'))
        if next_trans_date > furthest_trans_date:
            if transaction.get('destination') == 'spending':
                if transaction.get('type') == 'debit':
                    furthest_trans_date = next_trans_date
            elif transaction.get('destination') == 'savings':
                if transaction.get('type') == 'credit':
                    furthest_trans_date = next_trans_date
    return furthest_trans_date
