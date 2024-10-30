# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class RegisterDisinsectorForm(FlaskForm):
    name = StringField('Имя дезинсектора', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email дезинсектора', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    token = StringField('Токен бота', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Зарегистрировать дезинсектора')
