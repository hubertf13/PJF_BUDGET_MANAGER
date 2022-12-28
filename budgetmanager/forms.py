from datetime import datetime

from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, DateField, DecimalField, \
    SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, NumberRange

from budgetmanager.models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField('Update')
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')


class TransactionForm(FlaskForm):
    category = SelectField("Category", validators=[DataRequired()], choices=[])
    amount = DecimalField("Amount", validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    description = TextAreaField('Description', validators=[Length(min=0, max=100)])
    date = DateField('Date', default=datetime.utcnow, validators=[DataRequired()])
    submit = SubmitField("Save")

class LimitsForm(FlaskForm):
    category = SelectField("Category", validators=[DataRequired()], choices=[])
    limit = DecimalField("Limit", validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    submit = SubmitField('Save')
