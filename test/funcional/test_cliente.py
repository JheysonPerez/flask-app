import pytest
from flask import Flask
from flask_login import LoginManager, login_user, current_user
from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.routes.cliente import bp_cliente


# Configura la app con Flask-Login para que funcione current_user
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'clave-test'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True

    db.init_app(app)

    # Iniciar LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    app.register_blueprint(bp_cliente)

    with app.app_context():
        db.create_all()
        yield app


# Cliente de pruebas
@pytest.fixture
def client(app):
    return app.test_client()


# Crea un usuario autenticado como cliente
@pytest.fixture
def cliente_autenticado(app):
    with app.app_context():
        user = Usuario(nombre="Juan Chamba", email="juan@gmail.com", rol="cliente")
        user.set_password("123")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


# Test para crear un producto como cliente autenticado
def test_crear_producto(client, app, cliente_autenticado):
    with app.test_request_context():
        login_user(cliente_autenticado)
        response = client.post("/cliente/productos", json={
            "nombre": "Teclado",
            "descripcion": "Teclado mecánico RGB",
            "precio": 150.0,
            "stock": 10,
            "imagen_url": "http://img.test/teclado.jpg",
            "marca": "HyperX"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["msg"] == "Producto creado"


# Test para listar productos del cliente autenticado
def test_listar_productos_cliente(client, app, cliente_autenticado):
    with app.app_context():
        producto = Producto(nombre="Mouse", descripcion="Gamer", precio=80, stock=3, cliente_id=cliente_autenticado.id)
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)

    with app.test_request_context():
        login_user(cliente_autenticado)
        response = client.get("/cliente/productos")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert any(p["nombre"] == "Mouse" for p in data)


# Test para actualizar un producto propio
def test_actualizar_producto_cliente(client, app, cliente_autenticado):
    with app.app_context():
        producto = Producto(
            nombre="Monitor", descripcion="27 pulgadas", precio=300, stock=3,
            cliente_id=cliente_autenticado.id
        )
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)

    with app.test_request_context():
        login_user(cliente_autenticado)
        response = client.put(f"/cliente/productos/{producto.id}", json={
            "precio": 280.0,
            "stock": 4
        })
        assert response.status_code == 200
        assert response.get_json()["msg"] == "Producto actualizado"

    with app.app_context():
        actualizado = db.session.get(Producto, producto.id) 
        assert actualizado.precio == 280.0
        assert actualizado.stock == 4


# Test para eliminar un producto propio
def test_eliminar_producto_cliente(client, app, cliente_autenticado):
    with app.app_context():
        producto = Producto(
            nombre="Audífonos", descripcion="Bluetooth", precio=120, stock=2,
            cliente_id=cliente_autenticado.id
        )
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)

    with app.test_request_context():
        login_user(cliente_autenticado)
        response = client.delete(f"/cliente/productos/{producto.id}")
        assert response.status_code == 200
        assert response.get_json()["msg"] == "Producto eliminado"

    with app.app_context():
        eliminado = db.session.get(Producto, producto.id)  
        assert eliminado is None


# Test para impedir que el cliente actualice un producto ajeno
def test_actualizar_producto_ajeno(client, app, cliente_autenticado):
    with app.app_context():
        otro = Usuario(nombre="Jheyson Perez", email="jheyson@gmail.com", rol="cliente")
        otro.set_password("abc123")
        db.session.add(otro)
        db.session.commit()
        db.session.refresh(otro)

        producto = Producto(nombre="Tablet", precio=200, stock=1, cliente_id=otro.id)
        db.session.add(producto)
        db.session.commit()
        db.session.refresh(producto)

    with app.test_request_context():
        login_user(cliente_autenticado)
        response = client.put(f"/cliente/productos/{producto.id}", json={
            "precio": 180
        })
        assert response.status_code == 403  
