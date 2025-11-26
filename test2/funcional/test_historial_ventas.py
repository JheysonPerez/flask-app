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

    # Registro de Blueprints
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
    """Crea un cliente con una venta asociada para pruebas del dashboard."""
    with app.app_context():
        # Crear cliente
        usuario = Usuario(
            nombre="Comprador",
            email="compra@prueba.com",
            rol="cliente",
            estado="activo"
        )
        usuario.set_password("123456")
        db.session.add(usuario)
        db.session.flush()  # Obtener usuario.id antes del commit

        # Crear categoría vinculada al cliente
        categoria = Categoria(nombre="Tecnología", cliente=usuario)
        db.session.add(categoria)
        db.session.flush()

        # Crear producto vinculado al cliente y la categoría
        producto = Producto(
            nombre="Laptop",
            descripcion="Potente",
            precio=3000,
            stock=2,
            categoria=categoria,
            cliente=usuario
        )
        db.session.add(producto)
        db.session.flush()

        # Crear tipo de comprobante
        tipo = TipoComprobante(nombre="Boleta")
        db.session.add(tipo)
        db.session.flush()

        # Crear historial de venta
        venta = HistorialVenta(
            cliente=usuario,
            producto=producto,
            tipo_comprobante=tipo,
            total_venta=3000,
            cantidad=1,
            fecha_venta=datetime.utcnow()
        )
        db.session.add(venta)
        db.session.commit()

        return usuario.id


# ============================
# TESTS DEL DASHBOARD
# ============================

def test_dashboard_ventas_por_dia(client, cliente_autenticado):
    """Verifica que el dashboard muestre datos agrupados por día."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.get("/api/dashboard_ventas?agrupacion=dia&filtro=tipo_comprobante")
    assert response.status_code == 200
    assert any(
        term in response.data
        for term in [b"00:00", b"Boleta", b"Laptop"]
    ), "El dashboard diario no devolvió los datos esperados."


def test_dashboard_ventas_por_semana(client, cliente_autenticado):
    """Verifica que el dashboard muestre datos agrupados por semana."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.get("/api/dashboard_ventas?agrupacion=semana&filtro=tipo_comprobante")
    assert response.status_code == 200
    assert any(
        term in response.data
        for term in [b"Semana", b"Boleta", b"Laptop"]
    ), "El dashboard semanal no devolvió los datos esperados."


def test_dashboard_ventas_por_mes(client, cliente_autenticado):
    """Verifica que el dashboard muestre datos agrupados por mes."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente_autenticado)

    response = client.get("/api/dashboard_ventas?agrupacion=mes&filtro=tipo_comprobante")
    assert response.status_code == 200
    assert any(
        term in response.data
        for term in [b"Enero", b"Febrero", b"Boleta", b"Laptop"]
    ), "El dashboard mensual no devolvió los datos esperados."
