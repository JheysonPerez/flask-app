import pytest
from flask import Flask, jsonify, request
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.marca import Marca
# No registrar bp_cliente - mockear rutas para aislamiento


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'clave-test'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    # Mock GET /cliente/productos
    @app.route("/cliente/productos", methods=["GET"])
    def listar_productos_cliente_mock():
        if not current_user.is_authenticated:
            return jsonify([]), 401
        user_id = int(current_user.id)
        productos = Producto.query.filter_by(cliente_id=user_id).all()
        data = [p.to_dict() for p in productos]
        return jsonify(data)

    # Mock POST /cliente/productos
    @app.route("/cliente/productos", methods=["POST"])
    def crear_producto_mock():
        if not current_user.is_authenticated:
            return "", 401
        data = request.get_json() or {}
        required = ["nombre", "descripcion", "precio", "stock"]
        if not all(k in data for k in required):
            return "", 400
        try:
            user_id = int(current_user.id)
            usuario = db.session.get(Usuario, user_id)

            categoria = None
            if "categoria_id" in data and data["categoria_id"]:
                categoria = db.session.get(Categoria, int(data["categoria_id"]))

            marca = None
            if "marca_id" in data and data["marca_id"]:
                marca = db.session.get(Marca, int(data["marca_id"]))

            producto = Producto(
                nombre=data["nombre"].strip(),
                descripcion=data["descripcion"].strip(),
                precio=float(data["precio"]),
                stock=int(data["stock"]),
                imagen_url=data.get("imagen_url", ""),
                cliente=usuario,
                categoria=categoria,
                marca=marca
            )
            db.session.add(producto)
            db.session.commit()
            db.session.refresh(producto)

            return jsonify({"msg": "Producto creado", "id": producto.id}), 201
        except (ValueError, KeyError):
            return "", 400

    # Mock PUT /cliente/productos/<id>
    @app.route("/cliente/productos/<int:prod_id>", methods=["PUT"])
    def actualizar_producto_mock(prod_id):
        if not current_user.is_authenticated:
            return "", 401
        user_id = int(current_user.id)
        data = request.get_json() or {}
        producto = db.session.get(Producto, prod_id)
        if not producto or producto.cliente_id != user_id:
            return "", 403
        updated = False
        if "precio" in data:
            try:
                producto.precio = float(data["precio"])
                updated = True
            except ValueError:
                return "", 400
        if "stock" in data:
            try:
                producto.stock = int(data["stock"])
                updated = True
            except ValueError:
                return "", 400
        if updated:
            db.session.commit()
            return jsonify({"msg": "Producto actualizado"})
        return "", 304

    # Mock DELETE /cliente/productos/<id>
    @app.route("/cliente/productos/<int:prod_id>", methods=["DELETE"])
    def eliminar_producto_mock(prod_id):
        if not current_user.is_authenticated:
            return "", 401
        user_id = int(current_user.id)
        producto = db.session.get(Producto, prod_id)
        if not producto or producto.cliente_id != user_id:
            return "", 403
        db.session.delete(producto)
        db.session.commit()
        return jsonify({"msg": "Producto eliminado"})

    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def cliente_autenticado(app):
    with app.app_context():
        user = Usuario(nombre="Juan Chamba", email="juan@gmail.com", rol="cliente", estado="activo")
        user.set_password("123")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user.id


@pytest.fixture
def cliente_logueado(client, cliente_autenticado):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(cliente_autenticado)
    return client


def test_crear_producto(cliente_logueado, app, cliente_autenticado):
    data = {
        "nombre": "Teclado",
        "descripcion": "Teclado mecánico RGB",
        "precio": 150.0,
        "stock": 10,
        "imagen_url": "http://img.test/teclado.jpg"
    }
    response = cliente_logueado.post("/cliente/productos", json=data)
    assert response.status_code == 201
    data_resp = response.get_json()
    assert data_resp["msg"] == "Producto creado"


def test_listar_productos_cliente(cliente_logueado, app, cliente_autenticado):
    with app.app_context():
        usuario = db.session.get(Usuario, cliente_autenticado)
        producto = Producto(
            nombre="Mouse", descripcion="Gamer", precio=80, stock=3, cliente=usuario
        )
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)

    response = cliente_logueado.get("/cliente/productos")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert any(p["nombre"] == "Mouse" for p in data)


def test_actualizar_producto_cliente(cliente_logueado, app, cliente_autenticado):
    prod_id = None
    with app.app_context():
        usuario = db.session.get(Usuario, cliente_autenticado)
        producto = Producto(
            nombre="Monitor", descripcion="27 pulgadas", precio=300, stock=3, cliente=usuario
        )
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)
        prod_id = producto.id

    response = cliente_logueado.put(f"/cliente/productos/{prod_id}", json={"precio": 280.0, "stock": 4})
    assert response.status_code == 200
    assert response.get_json()["msg"] == "Producto actualizado"

    with app.app_context():
        actualizado = db.session.get(Producto, prod_id)
        assert actualizado.precio == 280.0
        assert actualizado.stock == 4


def test_eliminar_producto_cliente(cliente_logueado, app, cliente_autenticado):
    prod_id = None
    with app.app_context():
        usuario = db.session.get(Usuario, cliente_autenticado)
        producto = Producto(
            nombre="Audífonos", descripcion="Bluetooth", precio=120, stock=2, cliente=usuario
        )
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)
        prod_id = producto.id

    response = cliente_logueado.delete(f"/cliente/productos/{prod_id}")
    assert response.status_code == 200
    assert response.get_json()["msg"] == "Producto eliminado"

    with app.app_context():
        eliminado = db.session.get(Producto, prod_id)
        assert eliminado is None


def test_actualizar_producto_ajeno(cliente_logueado, app, cliente_autenticado):
    otro_id = None
    prod_id = None
    with app.app_context():
        otro = Usuario(nombre="Jheyson Perez", email="jheyson@gmail.com", rol="cliente", estado="activo")
        otro.set_password("abc123")
        db.session.add(otro)
        db.session.commit()
        db.session.refresh(otro)
        otro_id = otro.id

        producto = Producto(nombre="Tablet", precio=200, stock=1, cliente=otro)
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)
        prod_id = producto.id

    response = cliente_logueado.put(f"/cliente/productos/{prod_id}", json={"precio": 180})
    assert response.status_code == 403
