from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
import re

def gmail_only(form, field):
    if not field.data.endswith('@gmail.com'):
        raise ValidationError('Email must be a Gmail address (e.g., example@gmail.com).')

def phone_number_only(form, field):
    if not re.match(r'^\d+$', field.data):
        raise ValidationError('Contact info must contain only numbers.')

def email_not_registered(form, field):
    from models import User
    user = User.query.filter_by(email=field.data).first()
    if user:
        raise ValidationError('This email is already registered. Please use a different email.')

def strong_password(form, field):
    password = field.data
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), gmail_only, email_not_registered])
    contact_info = StringField('Contact Info', validators=[DataRequired(), Length(min=1, max=50), phone_number_only])
    password = PasswordField('Password', validators=[DataRequired(), strong_password])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RoomForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    description = TextAreaField('Description')
    image = StringField('Image URL')
    available = BooleanField('Available')
    submit = SubmitField('Save')

class ReservationForm(FlaskForm):
    check_in = StringField('Check-in Date', validators=[DataRequired()])
    check_out = StringField('Check-out Date', validators=[DataRequired()])
    submit = SubmitField('Reserve')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')
