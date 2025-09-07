import os
import pytest
from flask import Flask
from flask_login import LoginManager
from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.routes.producto import producto_bp

TEMPLATES_PATH = os.path.abspath("app/templates")


# Configura la aplicación Flask para pruebas
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

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    app.register_blueprint(producto_bp)

    # Mock de la ruta cliente_dashboard para evitar BuildError en los tests
    @app.route("/cliente/dashboard")
    def cliente_dashboard():
        return "Dashboard de prueba"

    with app.app_context():
        db.create_all()
        yield app


# Crea un cliente de pruebas Flask
@pytest.fixture
def client(app):
    return app.test_client()


# Crea un usuario de prueba autenticado
@pytest.fixture
def cliente_autenticado(app):
    with app.app_context():
        usuario = Usuario(nombre="Cliente Test", email="cliente@test.com", rol="cliente", estado="activo")
        usuario.set_password("123456")
        db.session.add(usuario)
        db.session.commit()
        return usuario.id


# Crear producto desde el formulario
def test_crear_producto(client, app, cliente_autenticado):
    with app.app_context():
        categoria = Categoria(nombre="Electrónica")
        db.session.add(categoria)
        db.session.commit()

    data = {
        'nombre': 'Mouse',
        'descripcion': 'Mouse óptico',
        'precio': '50',
        'stock': '10',
        'categoria_nombre': 'Electrónica',
        'marca': 'Logitech'
    }

    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.post("/productos", data=data, follow_redirects=True)
    assert response.status_code in [200, 302]


# Test: Listar productos del cliente autenticado
def test_listar_mis_productos(client, app, cliente_autenticado):
    with app.app_context():
        categoria = Categoria(nombre="Oficina")
        db.session.add(categoria)
        db.session.commit()

        producto = Producto(
            nombre="Teclado",
            descripcion="Mecánico",
            precio=100,
            stock=5,
            categoria_id=categoria.id,
            cliente_id=cliente_autenticado
        )
        db.session.add(producto)
        db.session.commit()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.get("/mis-productos")
    assert response.status_code == 200
    assert b"Teclado" in response.data


# Test: Actualizar producto propio del cliente
def test_actualizar_producto_propio(client, app, cliente_autenticado):
    with app.app_context():
        categoria = Categoria(nombre="Periféricos")
        db.session.add(categoria)
        db.session.commit()
        categoria_id = categoria.id

        producto = Producto(
            nombre="Monitor",
            descripcion="24 pulgadas",
            precio=200,
            stock=3,
            categoria_id=categoria_id,
            cliente_id=cliente_autenticado
        )
        db.session.add(producto)
        db.session.commit()
        producto_id = producto.id

    data = {
        'nombre': 'Monitor Full HD',
        'descripcion': 'Actualizado',
        'precio': '180',
        'stock': '4',
        'categoria_id': str(categoria_id),
        'marca': 'Samsung'
    }

    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.post(f"/productos/{producto_id}", data=data, follow_redirects=True)
    assert response.status_code in [200, 302]


# Test: Eliminar producto propio del cliente
def test_eliminar_producto_propio(client, app, cliente_autenticado):
    with app.app_context():
        categoria = Categoria(nombre="Audio")
        db.session.add(categoria)
        db.session.commit()
        categoria_id = categoria.id

        producto = Producto(
            nombre="Audífonos",
            descripcion="Bluetooth",
            precio=90,
            stock=2,
            categoria_id=categoria_id,
            cliente_id=cliente_autenticado
        )
        db.session.add(producto)
        db.session.commit()
        producto_id = producto.id

    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.post(f"/productos/{producto_id}/eliminar", follow_redirects=True)
    assert response.status_code in [200, 302]


    # Verifica que el producto ya no exista
    with app.app_context():
        assert db.session.get(Producto, producto_id) is None
