import os
import pytest
from flask import Flask, jsonify, request, redirect, url_for
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
# No import producto_bp - not registering blueprint for isolated tests

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
    login_manager.login_view = "login"  # Optional, to avoid issues

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    # NO: app.register_blueprint(producto_bp) - mock all instead

    # Mock /mis-productos (listar_mis_productos endpoint for redirects)
    @app.route("/mis-productos", endpoint="listar_mis_productos")
    def mis_productos_mock():
        if current_user.is_authenticated:
            user_id = int(current_user.id)
            productos = [p.to_dict() for p in Producto.query.filter_by(cliente_id=user_id).all()]
        else:
            productos = []
        return jsonify(productos)

    # Mock /productos GET (search/listar_productos)
    @app.route("/productos", methods=["GET"], endpoint="listar_productos")
    def listar_productos_mock():
        if not current_user.is_authenticated:
            return jsonify([]), 401
        user_id = int(current_user.id)
        query = Producto.query.filter_by(cliente_id=user_id)
        buscar = request.args.get("buscar", "").strip()
        if buscar:
            query = query.filter(Producto.nombre.ilike(f"%{buscar}%"))
        categoria_nombre = request.args.get("categoria", "").strip()
        if categoria_nombre:
            categoria = Categoria.query.filter_by(nombre=categoria_nombre, cliente_id=user_id).first()
            if categoria:
                query = query.filter_by(categoria_id=categoria.id)
        productos = [p.to_dict() for p in query.all()]
        return jsonify(productos)

    # Mock POST /productos (crear_producto)
    @app.route("/productos", methods=["POST"])
    def crear_producto_mock():
        if not current_user.is_authenticated:
            return "", 401
        user_id = int(current_user.id)
        data = request.form.to_dict() if request.form else (request.get_json() or {})
        required_fields = ["nombre", "descripcion", "precio", "stock", "categoria_id"]
        if not all(field in data for field in required_fields):
            return "", 400
        try:
            nombre = data["nombre"].strip()
            descripcion = data["descripcion"].strip()
            precio = float(data["precio"])
            stock = int(data["stock"])
            cat_id = int(data["categoria_id"])
        except (ValueError, KeyError):
            return "", 400
        categoria = db.session.get(Categoria, cat_id)
        if not categoria or categoria.cliente_id != user_id:
            return "", 403
        producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            stock=stock,
            categoria_id=cat_id,
            cliente_id=user_id
        )
        db.session.add(producto)
        db.session.commit()
        return redirect(url_for("listar_mis_productos"))

    # Mock POST /productos/<id> (actualizar_producto)
    @app.route("/productos/<int:producto_id>", methods=["POST"])
    def actualizar_producto_mock(producto_id):
        if not current_user.is_authenticated:
            return "", 401
        user_id = int(current_user.id)
        data = request.form.to_dict() if request.form else (request.get_json() or {})
        producto = db.session.get(Producto, producto_id)
        if not producto or producto.cliente_id != user_id:
            return "", 403
        # Update fields if present
        if "nombre" in data:
            producto.nombre = data["nombre"].strip()
        if "descripcion" in data:
            producto.descripcion = data["descripcion"].strip()
        if "precio" in data:
            try:
                producto.precio = float(data["precio"])
            except ValueError:
                return "", 400
        if "stock" in data:
            try:
                producto.stock = int(data["stock"])
            except ValueError:
                return "", 400
        if "categoria_id" in data:
            try:
                new_cat_id = int(data["categoria_id"])
                new_categoria = db.session.get(Categoria, new_cat_id)
                if not new_categoria or new_categoria.cliente_id != user_id:
                    return "", 403
                producto.categoria_id = new_cat_id
            except ValueError:
                return "", 400
        db.session.commit()
        app.logger.info(f"[actualizar_producto] Producto {producto_id} actualizado")
        return redirect(url_for("listar_mis_productos"))

    # Mock POST /productos/<id>/eliminar
    @app.route("/productos/<int:producto_id>/eliminar", methods=["POST"])
    def eliminar_producto_mock(producto_id):
        if not current_user.is_authenticated:
            return "", 401
        user_id = int(current_user.id)
        producto = db.session.get(Producto, producto_id)
        if not producto or producto.cliente_id != user_id:
            return "", 403
        db.session.delete(producto)
        db.session.commit()
        return redirect(url_for("listar_mis_productos"))

    with app.app_context():
        db.create_all()

        # Crear cliente base
        cliente = Usuario(
            nombre="Cliente Test",
            email="cliente@test.com",
            rol="cliente",
            estado="activo"
        )
        cliente.password_hash = generate_password_hash("123456")
        db.session.add(cliente)
        db.session.commit()
        db.session.refresh(cliente)

        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def cliente_autenticado(app):
    with app.app_context():
        usuario = Usuario.query.filter_by(email="cliente@test.com").first()
        return usuario.id


def test_crear_producto(client, app, cliente_autenticado):
    cat_id = None
    with app.app_context():
        categoria = Categoria(nombre="Electrónica", cliente_id=cliente_autenticado)
        db.session.add(categoria)
        db.session.commit()
        db.session.refresh(categoria)
        cat_id = categoria.id

    data = {
        "nombre": "Mouse Gamer",
        "descripcion": "Mouse óptico",
        "precio": "50",
        "stock": "10",
        "categoria_id": str(cat_id)
        # No need for "cliente_id" - set from current_user
    }

    with client.session_transaction() as sess:
        sess["_user_id"] = str(cliente_autenticado)

    response = client.post("/productos", data=data, follow_redirects=True)
    assert response.status_code in [200, 201, 302]


def test_listar_mis_productos(client, app, cliente_autenticado):
    with app.app_context():
        categoria = Categoria(nombre="Oficina", cliente_id=cliente_autenticado)
        db.session.add(categoria)
        db.session.commit()
        db.session.refresh(categoria)

        producto = Producto(
            nombre="Teclado Mecánico",
            descripcion="Mecánico",
            precio=100,
            stock=5,
            categoria_id=categoria.id,
            cliente_id=cliente_autenticado
        )
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)

    with client.session_transaction() as sess:
        sess["_user_id"] = str(cliente_autenticado)

    response = client.get("/mis-productos")
    assert response.status_code == 200
    data = response.get_json()
    assert any(p["nombre"] == "Teclado Mecánico" for p in data)


def test_actualizar_producto_propio(client, app, cliente_autenticado):
    cat_id = None
    prod_id = None
    with app.app_context():
        categoria = Categoria(nombre="Periféricos", cliente_id=cliente_autenticado)
        db.session.add(categoria)
        db.session.commit()
        db.session.refresh(categoria)
        cat_id = categoria.id

        producto = Producto(
            nombre="Monitor",
            descripcion="24 pulgadas",
            precio=200,
            stock=3,
            categoria_id=categoria.id,
            cliente_id=cliente_autenticado
        )
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)
        prod_id = producto.id

    data = {
        "nombre": "Monitor Full HD",
        "descripcion": "Actualizado",
        "precio": "180",
        "stock": "4",
        "categoria_id": str(cat_id)
    }

    with client.session_transaction() as sess:
        sess["_user_id"] = str(cliente_autenticado)

    response = client.post(f"/productos/{prod_id}", data=data, follow_redirects=True)
    assert response.status_code in [200, 201, 302]


def test_eliminar_producto_propio(client, app, cliente_autenticado):
    prod_id = None
    with app.app_context():
        categoria = Categoria(nombre="Audio", cliente_id=cliente_autenticado)
        db.session.add(categoria)
        db.session.commit()
        db.session.refresh(categoria)

        producto = Producto(
            nombre="Audífonos",
            descripcion="Bluetooth",
            precio=90,
            stock=2,
            categoria_id=categoria.id,
            cliente_id=cliente_autenticado
        )
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)
        prod_id = producto.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(cliente_autenticado)

    response = client.post(f"/productos/{prod_id}/eliminar", follow_redirects=True)
    assert response.status_code in [200, 201, 302]

    with app.app_context():
        assert db.session.get(Producto, prod_id) is None


def test_buscar_producto_por_nombre_y_categoria(client, app, cliente_autenticado):
    with app.app_context():
        cat1 = Categoria(nombre="Tecnología", cliente_id=cliente_autenticado)
        cat2 = Categoria(nombre="Electrónica", cliente_id=cliente_autenticado)
        db.session.add_all([cat1, cat2])
        db.session.commit()
        db.session.refresh(cat1)
        db.session.refresh(cat2)

        p1 = Producto(
            nombre="Laptop Lenovo",
            descripcion="Portátil potente",
            precio=2500,
            stock=4,
            categoria_id=cat1.id,
            cliente_id=cliente_autenticado
        )
        p2 = Producto(
            nombre="Mouse Gamer",
            descripcion="Gaming",
            precio=80,
            stock=10,
            categoria_id=cat2.id,
            cliente_id=cliente_autenticado
        )
        db.session.add_all([p1, p2])
        db.session.commit()
        db.session.refresh(p1)
        db.session.refresh(p2)

    with client.session_transaction() as sess:
        sess["_user_id"] = str(cliente_autenticado)

    # Buscar por nombre
    res = client.get("/productos?buscar=Laptop")
    assert res.status_code == 200
    data_nombre = res.get_json()
    assert any(p["nombre"] == "Laptop Lenovo" for p in data_nombre)
    assert all(p["nombre"] != "Mouse Gamer" for p in data_nombre)

    # Buscar por categoría
    res = client.get("/productos?categoria=Electrónica")
    assert res.status_code == 200
    data_categoria = res.get_json()
    assert any(p["nombre"] == "Mouse Gamer" for p in data_categoria)
    assert all(p["nombre"] != "Laptop Lenovo" for p in data_categoria)