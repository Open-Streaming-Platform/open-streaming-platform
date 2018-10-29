from flask_security.forms import RegisterForm, StringField, Required,ConfirmRegisterForm,ForgotPasswordForm
from flask_security import UserMixin, RoleMixin
import os

basedir = os.path.abspath(os.path.dirname(__file__))
from app import db

class ExtendedRegisterForm(RegisterForm):
    username = StringField('username', [Required()])

class ExtendedConfirmRegisterForm(ConfirmRegisterForm):
    username = StringField('username', [Required()])

class ExtendedForgotPasswordForm(ForgotPasswordForm):
    username = StringField('username', [Required()])

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    pictureLocation = db.Column(db.String(255))
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))