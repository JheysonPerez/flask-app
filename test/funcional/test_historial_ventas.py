import os
import pytest
from flask import Flask
from flask_login import LoginManager
from app.extensions import db
from app.models.usuario import Usuario
from app.models.historial_ventas import HistorialVenta
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.tipo_comprobante import TipoComprobante
from app.routes.historial_ventas import historial_ventas_bp, dashboard_ventas_bp
from datetime import datetime

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

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    app.register_blueprint(historial_ventas_bp, url_prefix='/api')
    app.register_blueprint(dashboard_ventas_bp, url_prefix='/api')

    @app.route("/cliente/dashboard")
    def cliente_dashboard():
        return "Dashboard de prueba"

    with app.app_context():
        db.create_all()
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def cliente_autenticado(app):
    with app.app_context():
        usuario = Usuario(nombre="Comprador", email="compra@prueba.com", rol="cliente", estado="activo")
        usuario.set_password("123456")
        db.session.add(usuario)

        categoria = Categoria(nombre="Tecnología")
        db.session.add(categoria)
        db.session.flush()

        producto = Producto(
            nombre="Laptop",
            descripcion="Potente",
            precio=3000,
            stock=2,
            categoria_id=categoria.id,
            cliente_id=usuario.id
        )
        db.session.add(producto)

        tipo = TipoComprobante(nombre="Boleta")
        db.session.add(tipo)
        db.session.commit()

        venta = HistorialVenta(
            cliente_id=usuario.id,
            producto_id=producto.id,
            tipo_comprobante_id=tipo.id,
            total_venta=3000,
            cantidad=1,
            fecha_venta=datetime.utcnow()
        )
        db.session.add(venta)
        db.session.commit()

        return usuario.id

# Test para agrupación por día 
def test_dashboard_ventas_por_dia(client, app, cliente_autenticado):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.get("/api/dashboard_ventas?agrupacion=dia&filtro=tipo_comprobante")
    assert response.status_code == 200
    assert b"00:00" in response.data or b"Boleta" in response.data or b"Laptop" in response.data

# Test para agrupación por semana
def test_dashboard_ventas_por_semana(client, app, cliente_autenticado):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.get("/api/dashboard_ventas?agrupacion=semana&filtro=tipo_comprobante")
    assert response.status_code == 200
    assert b"Semana" in response.data or b"Boleta" in response.data or b"Laptop" in response.data

# Test para agrupación por mes
def test_dashboard_ventas_por_mes(client, app, cliente_autenticado):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.get("/api/dashboard_ventas?agrupacion=mes&filtro=tipo_comprobante")
    assert response.status_code == 200
    assert b"Enero" in response.data or b"Febrero" in response.data or b"Boleta" in response.data or b"Laptop" in response.data
