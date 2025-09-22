import os
import pytest
from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.routes.categoria import bp_categoria

TEMPLATES_PATH = os.path.abspath("app/templates")

@pytest.fixture
def app():
    app = Flask(__name__, template_folder=TEMPLATES_PATH)
    app.config['SECRET_KEY'] = 'clave-test'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    app.login_manager = login_manager  # importante para evitar error de login_user()

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))  # SQLAlchemy 2.x compatible

    app.register_blueprint(bp_categoria)

    with app.app_context():
        db.create_all()
        cliente = Usuario(nombre="Juan Pérez", email="juan.perez@gmail.com", rol="cliente", estado="activo")
        cliente.password_hash = generate_password_hash("ClientePass2025!")
        db.session.add(cliente)
        db.session.commit()
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def login_admin(client, app):
    with app.app_context():
        cliente = Usuario.query.filter_by(email="juan.perez@gmail.com").first()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente.id)
    yield client

# Listar categorías electrónicas (sin login)
def test_listar_categorias(login_admin):
    with login_admin.application.app_context():
        db.session.add(Categoria(nombre="Periféricos"))
        db.session.add(Categoria(nombre="Procesadores"))
        db.session.commit()

    res = login_admin.get("/categorias/")
    assert res.status_code == 200
    data = res.get_json()
    nombres = [c["nombre"] for c in data]
    assert "Periféricos" in nombres
    assert "Procesadores" in nombres

# Crear categoría nueva (requiere login_cliente)
def test_crear_categoria(login_admin):
    data = {"nombre": "Componentes"}
    res = login_admin.post("/categorias/", json=data)
    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["nombre"] == "Componentes"

    with login_admin.application.app_context():
        cat = Categoria.query.filter_by(nombre="Componentes").first()
        assert cat is not None

# Editar categoría existente
def test_editar_categoria(login_admin):
    with login_admin.application.app_context():
        cat = Categoria(nombre="Tarjetas Gráficas")
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    nuevos_datos = {"nombre": "GPUs"}
    res = login_admin.put(f"/categorias/{cat_id}", json=nuevos_datos)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["nombre"] == "GPUs"

    with login_admin.application.app_context():
        cat_editada = Categoria.query.get(cat_id)
        assert cat_editada.nombre == "GPUs"

# Eliminar categoría existente
def test_borrar_categoria(login_admin):
    with login_admin.application.app_context():
        cat = Categoria(nombre="Fuentes de Poder")
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    res = login_admin.delete(f"/categorias/{cat_id}")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data.get("msg") == "Categoría eliminada"

    with login_admin.application.app_context():
        cat_borrada = Categoria.query.get(cat_id)
        assert cat_borrada is None
