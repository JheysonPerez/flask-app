#Realiza dos funciones al mismo lanzando multiples hilos simultaneos para ejecutar tareas concurrentes
#en este caso (5 usuarios iniciando sesión al mismo tiempo y 5 usuarios registrándose al mismo tiempo)
import os
import sys
import pytest
from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask_jwt_extended import JWTManager

from app.extensions import db
from app.models.usuario import Usuario
from app.routes.auth import auth_bp  # Asegúrate de que esté bien importado

# Añadir ruta base del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

TEMPLATES_PATH = os.path.abspath("app/templates")

@pytest.fixture
def app():
    app = Flask(__name__, template_folder=TEMPLATES_PATH)
    app.config['SECRET_KEY'] = 'clave-test'
    app.config['JWT_SECRET_KEY'] = 'jwt-prueba'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True

    db.init_app(app)
    JWTManager(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    app.register_blueprint(auth_bp, url_prefix="/auth")

    with app.app_context():
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

@pytest.fixture
def client(app):
    return app.test_client()

# Simula login tradicional
def login_user(client, email, password):
    return client.post("/auth/login", json={
        "email": email,
        "password": password
    })

# Simula registro de usuario
def register_user(client, nombre, email, password):
    return client.post("/auth/register", json={
        "nombre": nombre,
        "email": email,
        "password": password
    })

# Simula acceso a perfil con token
def get_perfil(client, token):
    return client.get("/auth/profile", headers={
        "Authorization": f"Bearer {token}"
    })


# Prueba de login concurrente
def test_login_concurrente(client, app):
    emails = [f"daniel{i}@gmail.com" for i in range(5)]
    password = "Pass1234!"

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(login_user, client, email, password)
            for email in emails
        ]
        resultados = [f.result() for f in as_completed(futures)]

    for res in resultados:
        assert res.status_code == 200
        assert b"access_token" in res.data


# Prueba de registro concurrente
def test_registro_concurrente(client, app):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(register_user, client,
                            f"nyels{i}", f"nyels{i}@gmail.com", "ClaveSegura")
            for i in range(5)
        ]
        resultados = [f.result() for f in as_completed(futures)]

    for res in resultados:
        assert res.status_code == 201
        assert b"Usuario registrado exitosamente" in res.data


# Prueba de acceso a perfiles concurrentes
def test_perfiles_concurrentes(client, app):
    tokens = []
    for i in range(5):
        login = login_user(client, f"daniel{i}@gmail.com", "Pass1234!")
        assert login.status_code == 200
        tokens.append(login.get_json()["access_token"])

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(get_perfil, client, token)
            for token in tokens
        ]
        resultados = [f.result() for f in as_completed(futures)]

    for res in resultados:
        assert res.status_code == 200
        assert b"email" in res.data
        assert b"rol" in res.data
