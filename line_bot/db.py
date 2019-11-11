from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
db = SQLAlchemy()
DB_ENV = 'HEROKU_POSTGRESQL_BROWN_URL'

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    step = db.Column(db.Integer, unique=False)
    line_id = db.Column(db.String(1024), unique=True)
    candidate = db.Column(db.String(120), unique=False)
    age_group = db.Column(db.String(120), unique=False)
    pts_show = db.Column(db.String(120), unique=False)
    phone_number = db.Column(db.String(1024), unique=False)
    add_friend_url = db.Column(db.String(1024), unique=False)
    paired_user_id = db.Column(db.String(120), unique=False)
    following = db.Column(db.Boolean, unique=False)
    last_message_sent = db.Column(db.DateTime)
    created = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow)
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow)


    def __init__(self, line_id):
        self.line_id = line_id
        self.step = 0


def init_app(app):
    db.init_app(app)
    app.config['SQLALCHEMY_DATABASE_URI'] =  os.environ[DB_ENV] if DB_ENV in os.environ else "postgresql://localhost/civid_dialogue"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


def add_user(line_id):
    user = db.session.query(User).filter(User.line_id == line_id).first()
    if not user:
        user = User(line_id)
        db.session.add(user)
        db.session.commit()
    return user

def edit_user(line_id, attrs, increment_step=False):
    user = User.query.filter_by(line_id=line_id).first()
    for k, v in attrs.items():
        setattr(user, k, v)
    if increment_step:
        user.step = user.step+1
    db.session.commit()
    return user

def get_step(line_id):
    user = User.query.filter_by(line_id=line_id).first()
    return user.step if user else None
