from datetime import datetime

from flask_login import UserMixin

from budgetmanager import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    categories = db.relationship('Category', secondary='user_expense_limit', back_populates="users")

    def __repr__(self):
        return f"User('{self.username}', '{self.image_file}')"


class Category(db.Model):
    name = db.Column(db.String(100), primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    transactions = db.relationship('Transaction', backref='category')
    users = db.relationship('User', secondary='user_expense_limit', back_populates="categories")

    def __repr__(self):
        return f"'{self.name}':'{self.type}'"


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), db.ForeignKey('category.name'), nullable=False)
    amount = db.Column(db.Numeric, nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Transaction('{self.category_name}', {self.transaction_date}', '{self.amount}', user:'{self.user_id}')"


class UserExpenseLimit(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    category_name = db.Column(db.String(100), db.ForeignKey('category.name'), primary_key=True)
    max_amount = db.Column(db.Numeric, default=0)

    def __repr__(self):
        return f"UserExpenseLimit('{self.user_id}', {self.category_name}', '{self.max_amount}')"
