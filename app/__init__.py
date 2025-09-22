from flask_login import LoginManager
from app.models.usuario import Usuario

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))
