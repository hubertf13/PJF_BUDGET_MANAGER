from datetime import datetime
from budgetmanager import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    # user has relationship to Transaction model, backref is adding another column to the Transaction model,
    # lazy means that sqlalchemy will load the data in one go
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    # how object is printed
    def __repr__(self):
        return f"User('{self.username}', '{self.image_file}')"

class Category(db.Model):
    name = db.Column(db.String(100), primary_key=True)

    def __repr__(self):
        return f"{self.name}"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), db.ForeignKey('category.name'), nullable=False)
    amount = db.Column(db.Numeric, nullable=False)
    # passing function as argument (-> datetime.utcnow)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    # foreign key referencing to the table name and column name (that's why lowercase)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Transaction(''{self.category_name}', {self.transaction_date}', '{self.amount}', user:{self.user_id})"
