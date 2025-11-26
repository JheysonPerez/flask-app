import os
import sys
import pytest
from flask import Flask
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.extensions import db
from app.models.usuario import Usuario
from app.routes.auth import auth_bp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
TEMPLATES_PATH = os.path.abspath("app/templates")


@pytest.fixture
def app():
    app = Flask(__name__, template_folder=TEMPLATES_PATH)
    app.config['SECRET_KEY'] = 'clave-test'
    app.config['JWT_SECRET_KEY'] = 'jwt-prueba'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_login.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True

    db.init_app(app)
    JWTManager(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with app.app_context():
            return Usuario.query.get(int(user_id))

    app.register_blueprint(auth_bp, url_prefix="/auth")

    with app.app_context():
        db.drop_all()
        db.create_all()
        for i in range(5):
            user = Usuario(
                nombre=f"Daniel{i}",
                email=f"daniel{i}@gmail.com",
                rol="cliente",
                estado="activo"
            )
            user.set_password("Pass1234!")
            db.session.add(user)
        db.session.commit()

        yield app

    # Limpiar base de datos temporal
    try:
        os.remove("test_login.db")
    except FileNotFoundError:
        pass


@pytest.fixture
def client(app):
    return app.test_client()


# 🔹 Funciones de hilo para concurrencia
def login_user_thread(app, email, password):
    with app.app_context():
        client = app.test_client()
        return client.post("/auth/login", json={"email": email, "password": password})


def register_user_thread(app, nombre, email, password):
    with app.app_context():
        client = app.test_client()
        return client.post("/auth/register", json={"nombre": nombre, "email": email, "password": password})


def get_perfil_thread(app, token):
    with app.app_context():
        client = app.test_client()
        return client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})


# 🔹 Tests concurrentes
def test_login_concurrente(app):
    emails = [f"daniel{i}@gmail.com" for i in range(5)]
    password = "Pass1234!"

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(login_user_thread, app, email, password) for email in emails]
        resultados = [f.result() for f in as_completed(futures)]

    for res in resultados:
        assert res.status_code == 200
        assert b"access_token" in res.data


def test_registro_concurrente(app):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(register_user_thread, app, f"nyels{i}", f"nyels{i}@gmail.com", "ClaveSegura")
            for i in range(5)
        ]
        resultados = [f.result() for f in as_completed(futures)]

    for res in resultados:
        assert res.status_code == 201
        assert b"Usuario registrado exitosamente" in res.data


def test_perfiles_concurrentes(app):
    # Primero login para obtener tokens
    tokens = []
    with app.app_context():
        for i in range(5):
            client = app.test_client()
            login = client.post("/auth/login", json={"email": f"daniel{i}@gmail.com", "password": "Pass1234!"})
            assert login.status_code == 200
            tokens.append(login.get_json()["access_token"])

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_perfil_thread, app, token) for token in tokens]
        resultados = [f.result() for f in as_completed(futures)]

    for res in resultados:
        assert res.status_code == 200
        assert b"email" in res.data
        assert b"rol" in res.data
