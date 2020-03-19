import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd
app.add_template_global(name=lookup, f=lookup)


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
# API key command-line code: export API_KEY=pk_9e55c9e43555430388ce0e6481ad6bc3
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    symbols = db.execute("SELECT symbol FROM History WHERE id = :id GROUP BY symbol", id=session['user_id'])
    companies = db.execute("SELECT company FROM History WHERE id = :id GROUP BY symbol", id=session['user_id'])
    get_shares = db.execute("SELECT SUM(shares) FROM History WHERE id = :id GROUP BY symbol", id=session['user_id'])
    shares = [share['SUM(shares)'] for share in get_shares]
    cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])

    return render_template("index.html", symbols_companies_shares=zip(symbols, companies, shares), lookup=lookup, cash=cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    elif request.method == "POST":
        shares = request.form.get("shares")
        symbol = request.form.get("symbol")
        try:
            float(shares)
        except ValueError:
            return apology("please input a valid number of shares")
        try:
            int(shares)
        except ValueError:
            return apology("please input a valid number of shares")
        shares = int(shares)

        if not shares or not float(shares) or not float(shares).is_integer() or float(shares) <= 0:
            return apology("input a valid number of shares to buy")

        elif not symbol or not lookup(symbol):
            return apology("input a valid symbol")

        elif type(shares) != int:
            return apology("How did you even get this error?!")

        else:
            quote = lookup(symbol)
            current_price = float(quote["price"])
            company = quote["name"]
            shares_num = int(request.form.get("shares"))
            shares_tcost = float(shares_num * current_price)
            balance = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])

            # balance[0] b/c the returned value of balance is a dict of multiple lists
            flbal = [float(i) for i in list(balance[0].values())]
            for bal in flbal:
                if bal - shares_tcost < 0:
                    return apology("Sorry, you don't have enough money")
                else:
                    newshares = bal - shares_tcost
                    newbalance = db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=newshares, id=session['user_id'])
                    newpurchase = db.execute("INSERT INTO History ('symbol', 'company', 'shares', 'price', 'totalprice', 'id', 'transaction_type') VALUES (:symbol, :company, :shares, :price, :totalprice, :id, :transaction_type)",
                                             symbol=symbol, company=company, shares=shares_num, price=current_price, totalprice=shares_tcost, id=session['user_id'], transaction_type="BUY")

    return redirect('/')


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    username = request.args.get("username")
    names = db.execute("SELECT * FROM users WHERE username = :username", username=username)
    if names and username:
        return jsonify(False)
    elif not names and username:
        return jsonify(True)
    else:
        return jsonify(False)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    get_trans_codes = db.execute("SELECT transaction_code FROM History WHERE id = :id", id=session['user_id'])
    get_symbols = db.execute("SELECT symbol FROM History WHERE id = :id", id=session['user_id'])
    get_companies = db.execute("SELECT company FROM History WHERE id = :id", id=session['user_id'])
    get_trans_types = db.execute("SELECT transaction_type FROM History WHERE id = :id", id=session['user_id'])
    get_shares = db.execute("SELECT shares FROM History WHERE id = :id", id=session['user_id'])
    get_prices = db.execute("SELECT price FROM History WHERE id = :id", id=session['user_id'])
    get_timestamps = db.execute("SELECT timestamp FROM History WHERE id = :id", id=session['user_id'])

    trans_codes = [code['transaction_code'] for code in get_trans_codes]
    symbols = [symbol['symbol'] for symbol in get_symbols]
    companies = [company['company'] for company in get_companies]
    trans_types = [types['transaction_type'] for types in get_trans_types]
    shares = [share['shares'] for share in get_shares]
    prices = [price['price'] for price in get_prices]
    timestamps = [timestamp['timestamp'] for timestamp in get_timestamps]

    return render_template("history.html", values=zip(trans_codes, symbols, companies, trans_types, shares, prices, timestamps))


@app.route("/login", methods=["GET", "POST"])
def login():

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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session['user_id'] = rows[0]["id"]

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
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")

    elif request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("please enter a symbol")
        quote = lookup(symbol)
        if not quote:
            return apology("please enter a valid symbol")
        price = float(quote['price'])
        if not price:
            return apology("sorry, we're having trouble fetching the data; try again later")
        return render_template("quoted.html", quote=quote, price=price)
    else:
        return apology("sorry, that page doesn't exist")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Require user to input a username as a text field whose name is username
        if not request.form.get("username"):
            return apology("you must provide a username", 400)

        # Ensure password and confirmation was submitted
        elif not request.form.get("password"):
            return apology("you must provide a password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        if len(rows) == 1:
            return apology("sorry, that username is already taken", 400)
        else:
            username = request.form.get('username')
            password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256', salt_length=8)
            newuser = db.execute("INSERT INTO users ('username', 'hash') VALUES (:username, :hash)",
                                 username=username, hash=password)
            return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get('symbol')
        shares = request.form.get('shares')

        if not symbol or not shares or symbol == "Select Stock":
            return apology("Please input a valid symbol and number of shares")
        elif int(shares) <= 0:
            return apology("Please input a positive number for shares")
        else:
            symbol = symbol.lower()
            shares = int(shares)
            get_cur_shares = db.execute(
                "SELECT SUM(shares) FROM History WHERE id = :id AND symbol = :symbol GROUP BY symbol", id=session['user_id'], symbol=symbol)
            try:
                cur_shares = [share['SUM(shares)'] for share in get_cur_shares][0]
            except IndexError:
                return apology("Please input a valid number of shares")
            if shares > cur_shares:
                return apology("Sorry, you don't have enough shares to sell")
            else:
                cur_price = float(lookup(symbol)['price'])
                sell_val = cur_price * float(shares)
                sell_val = float(sell_val)
                get_bal = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])
                balance = [bal['cash'] for bal in get_bal][0]
                balance = float(balance)
                new_balance = balance + sell_val
                company = lookup(symbol)['name']
                new_database_balance = db.execute("UPDATE users SET cash = :cash WHERE id = :id",
                                                  cash=new_balance, id=session['user_id'])
                new_database_transaction = db.execute("INSERT INTO History ('symbol', 'company', 'shares', 'price', 'totalprice', 'id', 'transaction_type') VALUES (:symbol, :company, :shares, :price, :totalprice, :id, :transaction_type)",
                                                      symbol=symbol, company=company, shares=-shares, price=cur_price,
                                                      totalprice=sell_val, id=session['user_id'], transaction_type="SELL")
        return redirect("/")
    else:
        get_symbols = db.execute(
            "SELECT symbol FROM History WHERE id = :id GROUP BY symbol HAVING SUM(shares) > 0", id=session['user_id'])
        if not get_symbols:
            return apology("Sorry, could not find valid symbol")
        else:
            symbols = [symbol['symbol'] for symbol in get_symbols]
            return render_template("sell.html", symbols=symbols)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
