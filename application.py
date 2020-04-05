import os
import decimal
import re
import redis

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from collections import Counter
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text


from helpers import apology, login_required, lookup, usd, get_portfolio, get_cash, update_cash

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached (commented out for production)
# @app.after_request
# def after_request(response):
#     response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     response.headers["Expires"] = 0
#     response.headers["Pragma"] = "no-cache"
#     return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies) (commented out for production)

# app.config["SESSION_FILE_DIR"] = 'redis'
# app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "<redis></redis>"

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
Session(app)

# Configure database

app.config['SQLALCHEMY_DATABASE_URI'] = "postgres://dxdszuptkkorhs:257f2b303f0a01e884ec6f3021c13e2a4408ef11612f1774c0023d915c2a0c5c@ec2-52-200-119-0.compute-1.amazonaws.com:5432/de4liqu1p4k75j"
db = SQLAlchemy(app)


# db.execute("CREATE TABLE IF NOT EXISTS 'users' ('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 'username' TEXT NOT NULL, 'hash' TEXT NOT NULL, 'cash' NUMERIC NOT NULL DEFAULT 10000.00 );")
# db.execute("CREATE TABLE IF NOT EXISTS 'transactions' ('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 'symbol' TEXT NOT NULL, 'shares' INTEGER NOT NULL, 'price' REAL NOT NULL, 'created_at' TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, 'user_id' INTEGER, CONSTRAINT fk_users FOREIGN KEY (user_id) REFERENCES users(id));")



# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():


    cash = get_cash(db, session["user_id"])

    portfolio = get_portfolio(db, session["user_id"])

    if len(portfolio) > 0:
        # cash = round(portfolio[0]["cash"], 2)
        stocks_value = 0
        for stock in portfolio:
            updated_stock = lookup(stock["symbol"])
            stock["name"] = updated_stock["name"]
            stock["price"] = round(decimal.Decimal(updated_stock["price"]), 2)
            stocks_value += (stock["price"] * stock["sum"])
        empty = False
    else:
        stocks_value = 0
        empty = True

    return render_template("index.html", portfolio=portfolio, cash=round(cash, 2), empty=empty, stocks_value=stocks_value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        stock = lookup(symbol)
        shares = request.form.get("shares")

        if stock is None:
            return(apology("No such stock."))
        elif shares == "":
            return apology("Must specify quantity")
        elif int(shares) < 0:
            return apology("Quantity must be positive")
        elif int(shares) == 0:
            return apology("Quantity must be at least 1")

        cash = get_cash(db, session["user_id"])

        total_price = int(shares) * stock["price"]
        if cash >= total_price:

            update_cash(db, cash, (0 - total_price), session["user_id"])


            insert_transaction_cmd = """INSERT INTO transactions (user_id, symbol, shares, price, id)
                                        VALUES (:user_id, :symbol, :shares,
                                        :price, nextval('id_transactions'))"""



            db.engine.execute(text(insert_transaction_cmd),
            user_id=session["user_id"], symbol=symbol.lower(), shares=shares, price=stock["price"])
            return redirect("/")
        else:
            return(apology("you don't have enough money."))


@app.route("/history")
@login_required
def history():
    cmd = "SELECT * from transactions WHERE user_id = :id"
    transactions = db.engine.execute(text(cmd), id=session["user_id"])
    transactions = [{column: value for column, value in rowproxy.items()} for rowproxy in transactions]
    for transaction in transactions:
        transaction["created_at"] = re.sub(r"\.\w*", "", str(transaction["created_at"]))


    empty = True if len(transactions) == 0 else False
    return render_template("history.html", transactions=transactions, empty=empty)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        cmd = "SELECT * FROM users WHERE username = :username"
        username = request.form.get("username")
        rows = db.engine.execute(text(cmd), username = username)

        rows = list(rows)
        print(rows[0])
        print(rows[0]["hash"])

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == "GET":
        return render_template("quote.html")
    else:
        stock = lookup(request.form.get("symbol"))

        if stock is None:
            return(apology("No such stock."))
        else:
            return render_template("quote.html", stock=stock)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        cmd = "SELECT * FROM users WHERE username = :username"
        username = request.form.get("username")
        rows = db.engine.execute(text(cmd), username = username)

        rows = list(rows)

        print(rows)

        # rows = db.engine.execute("SELECT * FROM users WHERE username = :username",
        #                   username=request.form.get("username"))



        # Ensure username exists and password is correct
        if len((rows)) == 1:
            return apology("Username taken")
        else:

            cmd = "INSERT INTO users (username, hash, id) VALUES (:username, :hash, nextval('id_users'))"
            rows = db.engine.execute(text(cmd), username = username, hash = generate_password_hash(request.form.get("password")))

            return render_template("login.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    portfolio = get_portfolio(db, session["user_id"])

    if len(portfolio) == 0:
        return apology("You don't have stocks to sell")
    else:
        symbols = list(map(lambda stock: stock["symbol"].upper(), portfolio))
        print(request.form.get("symbol"))
        if request.method == "GET":
            return render_template("sell.html", symbols=symbols)
        else:
            symbol = request.form.get("symbol")
            shares = request.form.get("shares")
            if symbol == "":
                return apology("You have to select a stock")
            elif shares == "":
                return apology("Must specify number of shares")
            elif symbol not in symbols:
                return apology("You do not own that stock")
            elif int(shares) < 0:
                return apology("Input must be positive")
            elif int(shares) == 0:
                return apology("You need to  sell at least 1")
            elif int(shares) > list(filter(lambda y: y['symbol'].upper() == symbol, portfolio))[0]['sum']:
                return apology(f"You don't have enough { symbol } shares")

            stock = lookup(symbol)
            total_price = int(shares) * stock["price"]

            cash = get_cash(db, session["user_id"])


            update_cash(db, cash, total_price, session["user_id"])


            insert_transaction_cmd = """INSERT INTO transactions (user_id, symbol, shares, price, id)
                                        VALUES (:user_id, :symbol, :shares,
                                        :price, nextval('id_transactions'))"""


            db.engine.execute(text(insert_transaction_cmd),
            user_id=session["user_id"], symbol=symbol.lower(), shares=(0 - int(shares)), price=stock["price"])

            return redirect("/")


@app.route("/top_up", methods=["GET", "POST"])
@login_required
def top_up():
    if request.method == "GET":
        return render_template("top_up.html")
    else:
        amount = request.form.get("amount")
        if amount == "":
            return apology("Amount must be specified")
        elif int(amount) < 0:
            return apology("Amount must be positive")
        elif int(amount) == 0:
            return apology("Amount must be bigger than 0")



        cash = get_cash(db, session["user_id"])

        update_cash(db, cash, amount, session["user_id"])



    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)




# TO REFACTOR:
#  def create_transaction(amount, symbol):
#  def to_dict(result_proxy):
