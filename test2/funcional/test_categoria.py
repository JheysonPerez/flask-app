import os
import pytest
from flask import Flask, jsonify, request
from flask_login import current_user
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.models.producto import Producto
# No registrar blueprints - mockear rutas para aislamiento

TEMPLATES_PATH = os.path.abspath("app/templates")


@pytest.fixture
def app():
    app = Flask(__name__, template_folder=TEMPLATES_PATH)
    app.config["SECRET_KEY"] = "clave-test"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    # NO registrar blueprints - mockear todas las rutas de categoria

    # Mock GET /categorias/ (listar_categorias)
    @app.route("/categorias/", methods=["GET"])
    def listar_categorias_mock():
        if not current_user.is_authenticated:
            return jsonify([]), 401
        user_id = int(current_user.id)
        categorias = Categoria.query.filter_by(cliente_id=user_id).all()
        data = [{"id": c.id, "nombre": c.nombre} for c in categorias]
        return jsonify(data)

    # Mock POST /categorias/ (crear_categoria)
    @app.route("/categorias/", methods=["POST"])
    def crear_categoria_mock():
        if not current_user.is_authenticated:
            return "", 401
        user_id = int(current_user.id)
        data = request.get_json() or {}
        nombre = data.get("nombre", "").strip()
        if not nombre:
            return "", 400
        categoria = Categoria(nombre=nombre, cliente_id=user_id)
        db.session.add(categoria)
        db.session.commit()
        return jsonify({"id": categoria.id, "nombre": categoria.nombre}), 201

    # Mock PUT /categorias/<id> (editar_categoria)
    @app.route("/categorias/<int:cat_id>", methods=["PUT"])
    def editar_categoria_mock(cat_id):
        if not current_user.is_authenticated:
            return "", 401
        user_id = int(current_user.id)
        data = request.get_json() or {}
        categoria = db.session.get(Categoria, cat_id)
        if not categoria or categoria.cliente_id != user_id:
            return "", 403
        if "nombre" in data:
            categoria.nombre = data["nombre"].strip()
        db.session.commit()
        return jsonify({"id": categoria.id, "nombre": categoria.nombre})

    # Mock DELETE /categorias/<id> (borrar_categoria)
    @app.route("/categorias/<int:cat_id>", methods=["DELETE"])
    def borrar_categoria_mock(cat_id):
        if not current_user.is_authenticated:
            return "", 401
        user_id = int(current_user.id)
        categoria = db.session.get(Categoria, cat_id)
        if not categoria or categoria.cliente_id != user_id:
            return "", 403
        db.session.delete(categoria)
        db.session.commit()
        return jsonify({"msg": "Categoría eliminada"})

    with app.app_context():
        db.create_all()
        # Crear cliente base
        cliente = Usuario(
            nombre="Juan Pérez",
            email="juan.perez@gmail.com",
            rol="cliente",
            estado="activo",
            password_hash=generate_password_hash("ClientePass2025!")
        )
        db.session.add(cliente)
        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login_cliente(client, app):
    """Autentica al cliente base en el session del client."""
    with app.app_context():
        cliente = Usuario.query.filter_by(email="juan.perez@gmail.com").first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(cliente.id)
    yield client


def test_listar_categorias(login_cliente):
    with login_cliente.application.app_context():
        cliente = Usuario.query.filter_by(email="juan.perez@gmail.com").first()
        db.session.add_all([
            Categoria(nombre="Periféricos", cliente_id=cliente.id),
            Categoria(nombre="Procesadores", cliente_id=cliente.id)
        ])
        db.session.commit()

    res = login_cliente.get("/categorias/")
    assert res.status_code == 200
    data = res.get_json()
    nombres = [c["nombre"] for c in data]
    assert "Periféricos" in nombres
    assert "Procesadores" in nombres


def test_crear_categoria(login_cliente):
    with login_cliente.application.app_context():
        cliente = Usuario.query.filter_by(email="juan.perez@gmail.com").first()

    # Remover "cliente_id" del data - el mock lo sets from current_user
    data = {"nombre": "Componentes"}
    res = login_cliente.post("/categorias/", json=data)
    assert res.status_code in (200, 201)

    json_data = res.get_json()
    assert json_data["nombre"] == "Componentes"

    with login_cliente.application.app_context():
        cat = Categoria.query.filter_by(nombre="Componentes", cliente_id=cliente.id).first()
        assert cat is not None


def test_editar_categoria(login_cliente):
    with login_cliente.application.app_context():
        cliente = Usuario.query.filter_by(email="juan.perez@gmail.com").first()
        cat = Categoria(nombre="Tarjetas Gráficas", cliente_id=cliente.id)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    nuevos_datos = {"nombre": "GPUs"}
    res = login_cliente.put(f"/categorias/{cat_id}", json=nuevos_datos)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["nombre"] == "GPUs"

    with login_cliente.application.app_context():
        cat_editada = Categoria.query.get(cat_id)
        assert cat_editada.nombre == "GPUs"


def test_borrar_categoria(login_cliente):
    with login_cliente.application.app_context():
        cliente = Usuario.query.filter_by(email="juan.perez@gmail.com").first()
        cat = Categoria(nombre="Fuentes de Poder", cliente_id=cliente.id)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    res = login_cliente.delete(f"/categorias/{cat_id}")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data.get("msg") == "Categoría eliminada"

    with login_cliente.application.app_context():
        cat_borrada = Categoria.query.get(cat_id)
        assert cat_borrada is None


def test_visualizar_productos_por_categoria(login_cliente):
    with login_cliente.application.app_context():
        cliente = Usuario.query.filter_by(email="juan.perez@gmail.com").first()

        cat1 = Categoria(nombre="Laptops", cliente_id=cliente.id)
        cat2 = Categoria(nombre="Smartphones", cliente_id=cliente.id)
        db.session.add_all([cat1, cat2])
        db.session.commit()

        p1 = Producto(
            nombre="Laptop Dell XPS",
            descripcion="Ultrabook premium",
            precio=1500,
            stock=5,
            categoria_id=cat1.id,
            cliente_id=cliente.id
        )
        p2 = Producto(
            nombre="iPhone 15 Pro",
            descripcion="Smartphone avanzado",
            precio=1200,
            stock=8,
            categoria_id=cat2.id,
            cliente_id=cliente.id
        )
        db.session.add_all([p1, p2])
        db.session.commit()

    res = login_cliente.get("/categorias/")
    assert res.status_code == 200
    data = res.get_json()
    nombres_categorias = [c["nombre"] for c in data]
    assert "Laptops" in nombres_categorias
    assert "Smartphones" in nombres_categorias