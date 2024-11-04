# app/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange

class RegisterDisinsectorForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    token = StringField('Токен', validators=[DataRequired(), Length(max=128)])
    telegram_user_id = IntegerField('Telegram User ID', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Зарегистрировать')
