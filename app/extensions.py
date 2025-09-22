from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_login import LoginManager

db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
login_manager = LoginManager() 
