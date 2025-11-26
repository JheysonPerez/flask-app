import pytest
from flask import Flask
from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.tipo_comprobante import TipoComprobante
from app.models.historial_ventas import HistorialVenta
from datetime import datetime

# ---------------------------
# Configuración de la app y DB
# ---------------------------
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app
        db.drop_all()

# ---------------------------
# Datos de prueba
# ---------------------------
@pytest.fixture
def datos_de_historial(app):
    with app.app_context():
        # Usuario
        usuario = Usuario(nombre="Ana", email="ana@gmail.com", rol="cliente", estado="activo")
        usuario.set_password("123")
        db.session.add(usuario)
        db.session.commit()

        # Categoría vinculada al usuario
        categoria = Categoria(nombre="Tecnología", cliente=usuario)
        db.session.add(categoria)
        db.session.commit()

        # Producto vinculado a usuario y categoría
        producto = Producto(
            nombre="Monitor",
            descripcion="24 pulgadas",
            precio=500.0,
            stock=5,
            imagen_url="http://img.com/monitor.jpg",
            cliente=usuario,       # instancia de Usuario
            categoria=categoria    # instancia de Categoria
        )

        # Tipo de comprobante
        tipo = TipoComprobante(nombre="Boleta")

        db.session.add_all([producto, tipo])
        db.session.commit()

        # Historial de venta
        historial = HistorialVenta(
            cliente_id=usuario.id,
            producto_id=producto.id,
            cantidad=2,
            total_venta=1000.0,
            tipo_comprobante_id=tipo.id,
            fecha_venta=datetime.utcnow()
        )
        db.session.add(historial)
        db.session.commit()

        yield {
            "usuario": usuario,
            "categoria": categoria,
            "producto": producto,
            "tipo": tipo,
            "historial": historial
        }

# ---------------------------
# Tests
# ---------------------------
def test_datos_basicos_de_historial(app, datos_de_historial):
    with app.app_context():
        historial = datos_de_historial["historial"]
        assert historial.cantidad == 2
        assert historial.total_venta == 1000.0
        assert historial.cliente.nombre == "Ana"
        assert historial.producto.nombre == "Monitor"

def test_fecha_venta_automatica(app, datos_de_historial):
    with app.app_context():
        historial = datos_de_historial["historial"]
        assert historial.fecha_venta is not None

def test_convertir_historial_a_diccionario(app, datos_de_historial):
    with app.app_context():
        historial = datos_de_historial["historial"]
        datos = historial.to_dict()
        assert datos["cantidad"] == 2
        assert datos["total_venta"] == 1000.0
        assert datos["producto_id"] == historial.producto.id
        assert datos["cliente_id"] == historial.cliente.id
        assert datos["tipo_comprobante_id"] == historial.tipo_comprobante_id

def test_representacion_legible_historial(app, datos_de_historial):
    with app.app_context():
        historial = datos_de_historial["historial"]
        assert str(historial.total_venta) in repr(historial)
