# This file contains all the logic.
import datetime
import os
import secrets
from operator import attrgetter

from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import extract

from budgetmanager import app, db, bcrypt
from budgetmanager.forms import RegistrationForm, LoginForm, UpdateAccountForm, TransactionForm, LimitsForm
from budgetmanager.models import User, Transaction, Category, UserExpenseLimit

APPNAME = "Budget Manager"


def first_database_init():
    categoryList = [
        "Food & Beverage", "Transportation", "Rentals", "Water Bill", "Phone Bill", "Electricity Bill", "Gas Bill",
        "Television Bill", "Internet Bill", "Other Utility Bills", "Home Maintenance", "Vehicle Maintenance",
        "Medical Check Up", "Insurances", "Education", "Housewares", "Personal Items", "Pets", "Home Services",
        "Other Expense", "Fitness", "Makeup", "Gifts & Donations", "Streaming Service", "Fun Money", "Investment",
        "Pay Interest", "Outgoing Transfer", "Debt Collection", "Debt", "Loan", "Repayment", "Salary", "Other Income",
        "Incoming Transfer"
    ]
    inflow_categories = ["Salary", "Other Income", "Incoming Transfer"]
    if not db.engine.has_table('user'):
        db.create_all()
        admin_password = bcrypt.generate_password_hash('admin').decode('utf-8')
        user = User(username='admin', password=admin_password)
        db.session.add(user)
        for cat in categoryList:
            if cat in inflow_categories:
                category = Category(name=cat, type="Income")
            else:
                category = Category(name=cat, type="Expense")
            db.session.add(category)
        db.session.commit()


def get_categories_tuple():
    categories = Category.query.all()
    value_name_list = []
    for category in categories:
        valueNameTuple = (category.name, category.name)
        value_name_list.append(valueNameTuple)
    return value_name_list


def get_money_amount_by_category(categorized_transactions):
    money_amount_by_category = []
    for ct in categorized_transactions:
        # First we make dictionary with category -> total amount of money
        category_and_amount_dics = {}
        for transaction in ct:
            if transaction.category_name not in category_and_amount_dics.keys():
                category_and_amount_dics[transaction.category_name] = float(transaction.amount)
            else:
                category_and_amount_dics[transaction.category_name] += float(transaction.amount)
        # Second we change dictionary into list to view it in html
        money_amount_by_category.append(change_dictionary_to_list(category_and_amount_dics))

    return money_amount_by_category


def change_dictionary_to_list(category_and_amount_dics):
    category_and_amount_list = []
    for caa in category_and_amount_dics.keys():
        category_and_amount_list = [caa, category_and_amount_dics.get(caa)]
    return category_and_amount_list


def get_categorized_transactions(month, year):
    categorized_transactions = []
    categories = Category.query.all()
    for category in categories:
        category_name = category.name
        transactions_by_category = Transaction.query.filter(
            extract('year', Transaction.transaction_date) == year).filter(
            extract('month', Transaction.transaction_date) == month).filter_by(user_id=current_user.id,
                                                                               category_name=category_name).all()
        if len(transactions_by_category) != 0:
            categorized_transactions.append(
                sorted(transactions_by_category, key=attrgetter('transaction_date'), reverse=True))
    return categorized_transactions


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    file_name, file_ext = os.path.splitext(form_picture.filename)
    picture_filename = random_hex + file_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_filename)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_filename


def get_income_categories():
    income_categories = []
    income_categories_objects = Category.query.filter_by(type="Income").all()
    for ic in income_categories_objects:
        income_categories.append(ic.name)
    return income_categories


def get_inflow_and_outflow_sum(category_and_total):
    inflow_sum = 0
    outflow_sum = 0
    for cat in category_and_total:
        income_categories = get_income_categories()
        if cat[0] in income_categories:
            inflow_sum += cat[1]
        else:
            outflow_sum -= cat[1]
    return inflow_sum, outflow_sum - (outflow_sum * 2)


def get_request_values_if_present():
    if len(request.values.keys()) == 0:
        date = datetime.datetime.utcnow()
    else:
        date = datetime.datetime(int(request.values.get('year')), int(request.values.get('month')),
                                 datetime.datetime.utcnow().day)
    return date


def get_required_data():
    month = request.args.get('month', request.values.get('month'), type=int)
    year = request.args.get('year', request.values.get('year'), type=int)
    categorized_transactions = get_categorized_transactions(month, year)
    money_amount_by_category = get_money_amount_by_category(categorized_transactions)
    inflow_sum, outflow_sum = get_inflow_and_outflow_sum(money_amount_by_category)
    return categorized_transactions, inflow_sum, money_amount_by_category, month, outflow_sum, year


def get_limit_if_present(category):
    user_category_limit = UserExpenseLimit.query.filter_by(user_id=current_user.id, category_name=category).first()
    if user_category_limit is None:
        return -1
    else:
        return user_category_limit.max_amount


@app.route("/home/month")
def home_by_date():
    if len(request.values.keys()) != 0:
        month = int(request.values.get('month'))
        if request.values.get('button') == "prev":
            month = int(month) - 1
        elif request.values.get('button') == "next":
            month = int(month) + 1
        year = int(request.values.get('year'))
        if month < 1:
            year = year - 1
            month = 12
        elif month > 12:
            year = year + 1
            month = 1
        return redirect(url_for('home', month=month, year=year))
    return redirect(url_for('home'))


@app.route("/")
@app.route("/home")
def home():
    first_database_init()
    if current_user.is_active:
        date = get_request_values_if_present()
        month_name = date.strftime("%B")
        month = request.args.get('month', date.month, type=int)
        year = request.args.get('year', date.year, type=int)
        categorized_transactions = get_categorized_transactions(month, year)
        money_amount_by_category = get_money_amount_by_category(categorized_transactions)
        inflow_sum, outflow_sum = get_inflow_and_outflow_sum(money_amount_by_category)
        get_flash_if_limit_exceeded(money_amount_by_category)
        return render_template("home.html", transactions=categorized_transactions, appname=APPNAME,
                               money_amount_by_category=money_amount_by_category, inflow_sum=inflow_sum,
                               income_cateogires=get_income_categories(), outflow_sum=outflow_sum, month=month,
                               year=year, month_name=month_name)
    else:
        return render_template("homeNotLogged.html", appname=APPNAME)


@app.route("/home/transaction", methods=['GET', 'POST'])
@login_required
def new_transaction():
    form = TransactionForm()
    form.category.choices = get_categories_tuple()
    categorized_transactions, inflow_sum, money_amount_by_category, month, outflow_sum, year = get_required_data()
    date = datetime.datetime(int(year), int(month), datetime.datetime.utcnow().day)
    month_name = date.strftime("%B")
    form.date.data = date

    if form.validate_on_submit():
        income_categories = get_income_categories()
        if form.category.data not in income_categories:
            form.amount.data = form.amount.data - (form.amount.data * 2)
        transaction = Transaction(category_name=form.category.data, amount=form.amount.data,
                                  transaction_date=form.date.data, description=form.description.data,
                                  user=current_user)
        db.session.add(transaction)
        db.session.commit()
        flash('New transaction added!', 'success')
        return redirect(url_for('home_by_date', month=month, year=year))
    return render_template("create_transaction.html", transactions=categorized_transactions, appname=APPNAME,
                           transactionForm=form, inflow_sum=inflow_sum, outflow_sum=outflow_sum,
                           money_amount_by_category=money_amount_by_category, income_cateogires=get_income_categories(),
                           legend='Add Transaction', month=month, year=year, month_name=month_name)


def get_flash_if_limit_exceeded(money_amount_by_category):
    for mabc in money_amount_by_category:
        category = mabc[0]
        category_money_amount = mabc[1]
        category_money_amount = category_money_amount - (2 * category_money_amount)
        user_category_limit = UserExpenseLimit.query.filter_by(user_id=current_user.id, category_name=category).first()
        if user_category_limit is not None:
            if user_category_limit.max_amount < category_money_amount:
                flash('The limit for ' + category + ' has been exceeded', 'warning')


@app.route("/about")
def about():
    return render_template("about.html", title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home_by_date'))
    form = RegistrationForm()
    # if form was submitted (clicked button)
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        # url_for(THERE IS THE NAME OF FUNCTION)
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form, appname=APPNAME)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home_by_date'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            # if next_page is not None then redirect to next page else redirect to home
            return redirect(next_page) if next_page else redirect(url_for('home_by_date'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form, appname=APPNAME)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home_by_date'))


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        db.session.commit()
        flash('Your account has beed updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form, appname=APPNAME)


@app.route("/home/transaction/<int:transaction_id>/delete", methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        abort(403)
    month = request.args.get('month', request.values.get('month'), type=int)
    year = request.args.get('year', request.values.get('year'), type=int)
    db.session.delete(transaction)
    db.session.commit()
    flash('Your transaction has been deleted!', 'success')
    return redirect(url_for('home_by_date', month=month, year=year))


@app.route("/home/transaction/<int:transaction_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        abort(403)
    form = TransactionForm()
    form.category.choices = get_categories_tuple()
    categorized_transactions, inflow_sum, money_amount_by_category, month, outflow_sum, year = get_required_data()
    income_categories = get_income_categories()
    date = datetime.datetime(int(year), int(month), datetime.datetime.utcnow().day)
    month_name = date.strftime("%B")

    if form.validate_on_submit():
        transaction.category_name = form.category.data
        if form.category.data not in income_categories:
            form.amount.data = form.amount.data - (form.amount.data * 2)
        transaction.amount = form.amount.data
        transaction.description = form.description.data
        transaction.transaction_date = form.date.data
        db.session.commit()
        flash('Your transaction has been edited!', 'success')
        return redirect(url_for('home_by_date', month=month, year=year))

    form.category.data = transaction.category_name
    if transaction.amount < 0:
        form.amount.data = transaction.amount - (transaction.amount * 2)
    else:
        form.amount.data = transaction.amount
    form.description.data = transaction.description
    form.date.data = transaction.transaction_date
    return render_template("create_transaction.html", transactions=categorized_transactions, appname=APPNAME,
                           transactionForm=form, inflow_sum=inflow_sum, outflow_sum=outflow_sum,
                           money_amount_by_category=money_amount_by_category, income_cateogires=get_income_categories(),
                           legend='Edit Transaction', month=month, year=year, month_name=month_name)


@app.route("/settings", methods=['GET', 'POST'])
@login_required
def settings():
    form = LimitsForm()
    form.category.choices = delete_income_categories()

    if form.validate_on_submit():
        user_expense_limit = UserExpenseLimit(user_id=current_user.id, category_name=form.category.data,
                                              max_amount=form.limit.data)

        user_category_limit = UserExpenseLimit.query.filter_by(user_id=current_user.id,
                                                               category_name=form.category.data).first()
        if user_category_limit is not None:
            user_category_limit.max_amount = form.limit.data
        else:
            db.session.add(user_expense_limit)
        db.session.commit()
        flash('Your settings has been updated!', 'success')
        return redirect(url_for('settings'))
    all_limits = UserExpenseLimit.query.filter_by(user_id=current_user.id).all()
    return render_template("settings.html", appname=APPNAME, form=form, all_limits=all_limits)


def delete_income_categories():
    all_categories = get_categories_tuple()
    income_categories = get_income_categories()
    for ic in income_categories:
        for ac in all_categories:
            if ac[0] == ic:
                all_categories.remove(ac)
    return all_categories
