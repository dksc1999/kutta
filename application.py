import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    row = db.execute("SELECT * FROM users WHERE id=:id", id=session['user_id'])
    username = row[0]['username']
    cash = row[0]['cash']
    rows = db.execute("SELECT * FROM stocks WHERE username=:username", username=username)
        
    if rows:
        symbols = []
        names = []
        prices = []
        shares = []
        totals = []
        t = 0
        for row in rows:
            symbols.append(row['symbol'])
            shares.append(row['shares'])
            quote = lookup(row['symbol'])
            name = quote['name']
            price = quote['price']
            totals.append(usd(price * row['shares']))
            names.append(name)
            prices.append(usd(price))
            t = t + (price * row['shares'])
        t = t + cash
        length = len(rows)
        return render_template("index.html",length=length,symbols=symbols,names=names,prices=prices,shares=shares,totals=totals,cash=usd(cash),t=usd(t))
    else:
        return render_template("index.html",length=0,symbols=[],names=[],prices=[],shares=[],totals=[],cash=usd(cash),t=usd(cash))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = (request.form.get("symbol")).upper()
        shares = int(request.form.get('shares'))
        if not symbol:
            return apology("no symbol")
        if not shares:
            return apology("no shares")
        quote = lookup(symbol)
        if not quote:
            return apology("not valid symbol")
        price = quote['price']
        total = price * shares
        
        row = db.execute("SELECT * FROM users WHERE id=:id", id=session['user_id'])
        cash = row[0]['cash']
        username = row[0]['username']
        if cash < total:
            return apology('too many shares')
        cash = cash - total
        db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=cash, id=session['user_id'])
        
        row = db.execute("SELECT * FROM stocks WHERE symbol=:symbol AND username=:username", symbol=symbol,username=username)
        if row:
            old_shares = row[0]['shares']
            new_shares = shares + old_shares
            db.execute("UPDATE stocks SET shares=:shares WHERE symbol=:symbol AND username=:username",shares=new_shares,symbol=symbol,username=username)
        else:
            db.execute("INSERT INTO stocks (username,symbol,shares) VALUES (:username,:symbol,:shares)", username=username,symbol=symbol,shares=shares)
        return redirect(url_for("index"))
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    rows = db.execute("SELECT * FROM buy_sell_records WHERE userid=:userid", userid=session["user_id"])
    return render_template("history.html",t=rows)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":

        # ensure symbol was submitted
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Must provide Symbol")
        if not lookup(symbol):
            return apology("No such symbol!")
        
        symbol=request.form.get("symbol")
        
        quote = lookup(symbol)
        if not quote:
            return apology("not valid symbol")
        
        name = quote['name']
        price = quote['price']
        symbol = quote['symbol']
        price = usd(price)
        return render_template("quoted.html",name=name,price=price,symbol=symbol)
        
    else:
        return render_template("quote.html")

    
    return apology("Invalid Symbol")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        
        #ensure whether password and re-password match     
        elif not request.form.get("re-password")==request.form.get("password"):
            return apology("Password and Password(again) fields do not match")
        
        else :
            username	=	request.form["username"]	
            password	=	request.form["password"]
            rows = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",username=username,hash=pwd_context.hash(password))   
            return redirect(url_for("index"))
    
    else:
        return render_template("register.html")
    

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
        symbol = (request.form.get("symbol")).upper()
        shares = int(request.form.get('shares'))
        if not symbol:
            return apology("no symbol")
        if not shares:
            return apology("no shares")
        quote = lookup(symbol)
        if not quote:
            return apology("not valid symbol")
        price = quote['price']
        total = price * shares
        
        row = db.execute("SELECT * FROM users WHERE id=:id", id=session['user_id'])
        cash = row[0]['cash']
        username = row[0]['username']
        
        row = db.execute("SELECT * FROM stocks WHERE symbol=:symbol AND username=:username", symbol=symbol,username=username)
        if not row:
            return apology('stock not available')
        old_shares = row[0]['shares']
        if old_shares<shares:
            return apology('not enough shares')
        cash = cash + total
        db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=cash, id=session['user_id'])
        db.execute("INSERT INTO buy_sell_records (userid,Symbol,Name,Shares) VALUES (:userid, :symbol,:names,:shares)",userid=session['user_id'],symbol=symbol,names=lookup(symbol)['name'],shares=0-shares)
        
        new_shares = old_shares - shares
        if new_shares != 0:
            db.execute("UPDATE stocks SET shares=:shares WHERE symbol=:symbol AND username=:username",shares=new_shares,symbol=symbol,username=username)
        else:
            db.execute("DELETE FROM stocks WHERE username=:username AND symbol=:symbol", username=username,symbol=symbol)
        return redirect(url_for("index"))
    else:
        return render_template("sell.html")
if __name__=="__main__":
    port = int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)