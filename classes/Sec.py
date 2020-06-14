from flask import flash
from flask_security.forms import RegisterForm, StringField, Required,ConfirmRegisterForm,ForgotPasswordForm, LoginForm, validators
from flask_security import UserMixin, RoleMixin
from .shared import db
from classes import Sec
from uuid import uuid4

class ExtendedRegisterForm(RegisterForm):
    username = StringField('username', [validators.Regexp("[^' ']+"), Required()])
    email = StringField('email', [Required()])

    def validate(self):
        success = True
        if not super(ExtendedRegisterForm, self).validate():
            success = False
        if db.session.query(User).filter(User.username == self.username.data.strip()).first():
            self.username.errors.append("Username already taken")
            success = False
        if db.session.query(User).filter(User.email == self.email.data.strip()).first():
            self.email.errors.append("Email address already taken")
            success = False
        return success

class ExtendedConfirmRegisterForm(ConfirmRegisterForm):
    username = StringField('username', [Required()])

class OSPLoginForm(LoginForm):

    def validate(self):

        isvalid = False
        userQuery = Sec.User.query.filter_by(username=self.email.data.strip(), authType=0).first()
        if userQuery is not None:
            isvalid = True
        userQuery = Sec.User.query.filter_by(email=self.email.data.strip(), authType=0).first()
        if userQuery is not None:
            isvalid = True
        if isvalid is True:
            response = super(OSPLoginForm, self).validate()
            return response
        flash("Invalid Username or Password","error")
        return False

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(255))
    username = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255), unique=True)
    fs_uniquifier = db.Column(db.String(255))
    password = db.Column(db.String(255))
    biography = db.Column(db.String(2048))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    pictureLocation = db.Column(db.String(255))
    authType = db.Column(db.Integer)
    oAuthID = db.Column(db.String(2048))
    oAuthProvider = db.Column(db.String(40))
    xmppToken = db.Column(db.String(64))
    oAuthToken = db.relationship('OAuth2Token', backref='userObj', lazy='joined')
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    invites = db.relationship('invitedViewer', backref='user', lazy="dynamic")
    channels = db.relationship('Channel', backref='owner', lazy="dynamic")
    notifications = db.relationship('userNotification', backref='user', lazy="dynamic")
    subscriptions = db.relationship('channelSubs', backref='user', cascade="all, delete-orphan", lazy="dynamic")

    def serialize(self):
        return {
            'id': str(self.id),
            'uuid': self.uuid,
            'username': self.username,
            'biography': self.biography,
            'pictureLocation': "/images/" + str(self.pictureLocation),
            'channels': [obj.id for obj in self.channels],
            'page': '/streamer/' + str(self.id) + '/'
        }

class OAuth2Token(db.Model):
    __tablename__ = "OAuth2Token"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))
    token_type = db.Column(db.String(40))
    access_token = db.Column(db.String(200))
    refresh_token = db.Column(db.String(200))
    expires_at = db.Column(db.Integer)
    user = db.Column(db.ForeignKey(User.id))

    def __init__(self, name, token_type, access_token, refresh_token, expires_at, user):
        self.name = name
        self.token_type = token_type
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.user = user

    def to_token(self):
        return dict(
            access_token=self.access_token,
            token_type=self.token_type,
            refresh_token=self.refresh_token,
            expires_at=self.expires_at,
        )