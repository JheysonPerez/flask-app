import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_login import LoginManager
from app.extensions import db
from app.models.usuario import Usuario
from app.routes.auth import auth_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'clave-secreta-test'
    app.config['SECRET_KEY'] = 'clave-login-test'
    app.config['TESTING'] = True

    db.init_app(app)
    JWTManager(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    app.login_manager = login_manager  

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))  

    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


# Login con credenciales válidas
def test_login_credenciales_validas(client, app):
    with app.app_context():
        user = Usuario(nombre="Carlos Ramirez", email="carlos.ramirez@gmail.com", rol="cliente")
        user.set_password("clave123")
        db.session.add(user)
        db.session.commit()

    response = client.post("/login", json={
        "email": "carlos.ramirez@gmail.com",
        "password": "clave123"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data


# Login con credenciales inválidas
def test_login_credenciales_invalidas(client):
    response = client.post("/login", json={
        "email": "maria.lopez@gmail.com",
        "password": "incorrecta"
    })
    assert response.status_code == 401
    data = response.get_json()
    assert data["msg"] == "Credenciales inválidas"


# Logout con token válido
def test_logout_con_token(client, app):
    with app.app_context():
        user = Usuario(nombre="Laura Sánchez", email="laura.sanchez@gmail.com", rol="cliente")
        user.set_password("miClaveSecreta")
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=user.id)

    response = client.post("/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.get_json()
    assert "Sesión cerrada" in data["msg"]


# Logout sin token
def test_logout_sin_token(client):
    response = client.post("/logout")
    assert response.status_code == 401
    data = response.get_json()
    assert "Missing Authorization Header" in data["msg"]
