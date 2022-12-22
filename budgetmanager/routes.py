# This file contains all the logic.
import os
import secrets
from operator import attrgetter

from PIL import Image
from flask import render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required

from budgetmanager import app, db, bcrypt
from budgetmanager.forms import RegistrationForm, LoginForm, UpdateAccountForm, TransactionForm
from budgetmanager.models import User, Transaction, Category

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


def get_categories_list():
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


def get_categorized_transactions():
    categorized_transactions = []
    categories = Category.query.all()
    for category in categories:
        category_name = category.name
        transactions_by_category = Transaction.query.filter_by(user_id=current_user.id,
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


@app.route("/")
@app.route("/home")
def home():
    first_database_init()
    if current_user.is_active:
        categorized_transactions = get_categorized_transactions()
        money_amount_by_category = get_money_amount_by_category(categorized_transactions)
        inflow_sum, outflow_sum = get_inflow_and_outflow_sum(money_amount_by_category)
        return render_template("home.html", transactions=categorized_transactions, appname=APPNAME,
                               money_amount_by_category=money_amount_by_category, inflow_sum=inflow_sum,
                               income_cateogires=get_income_categories(), outflow_sum=outflow_sum)
    else:
        return render_template("homeNotLogged.html", appname=APPNAME)


@app.route("/home/transaction", methods=['GET', 'POST'])
@login_required
def open_transaction_window():
    transaction_form = TransactionForm()
    transaction_form.category.choices = get_categories_list()
    categorized_transactions = get_categorized_transactions()
    money_amount_by_category = get_money_amount_by_category(categorized_transactions)
    inflow_sum, outflow_sum = get_inflow_and_outflow_sum(money_amount_by_category)
    return render_template("create_transaction.html", transactions=categorized_transactions, appname=APPNAME,
                           transactionForm=transaction_form, inflow_sum=inflow_sum, outflow_sum=outflow_sum,
                           money_amount_by_category=money_amount_by_category, income_cateogires=get_income_categories())


@app.route("/about")
def about():
    return render_template("about.html", title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
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
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            # if next_page is not None then redirect to next page else redirect to home
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form, appname=APPNAME)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


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


@app.route("/home/transaction/new", methods=['GET', 'POST'])
@login_required
def new_transaction():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    # if request.method == "POST":
    form = TransactionForm(request.form)
    if form.submit.data:
        income_categories = get_income_categories()
        if form.category.data not in income_categories:
            form.amount.data = form.amount.data - (form.amount.data * 2)
        transaction = Transaction(category_name=form.category.data, amount=form.amount.data,
                                  transaction_date=form.date.data, description=form.description.data,
                                  user=current_user)
        db.session.add(transaction)
        db.session.commit()
        flash('New transaction added!', 'success')
        return redirect(url_for('home'))
    return render_template("home.html", transactions=transactions, appname=APPNAME)
