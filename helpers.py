import os
import requests
import urllib.parse
import decimal

from flask import redirect, render_template, request, session
from functools import wraps
from sqlalchemy.sql import text



def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(session)
        if session.get("user_id") is None:
            print("was none")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def get_portfolio(db, user_id):
     cmd = """ SELECT symbol, SUM(shares) FROM transactions t
            JOIN users u ON u.id = t.user_id
            WHERE u.id = :user_id
            GROUP BY t.symbol
            HAVING SUM(shares) > 0 """
     portfolio = db.engine.execute(text(cmd), user_id=user_id)
     portfolio = [{column: value for column, value in rowproxy.items()} for rowproxy in portfolio]
     return portfolio


def get_cash(db, user_id):
    cash_cmd = "SELECT * FROM users u WHERE u.id = :id"
    result_cash = db.engine.execute(text(cash_cmd), id=user_id)
    list_cash = list(result_cash)
    cash = list_cash[0]['cash']
    return cash


def update_cash(db, old, amount, user_id):
     update_cash_cmd = "UPDATE users SET cash = :new_cash WHERE id = :id"
     db.engine.execute(text(update_cash_cmd),
                       new_cash=(old + decimal.Decimal(amount)), id=user_id)

