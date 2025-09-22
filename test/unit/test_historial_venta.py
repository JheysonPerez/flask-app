import pytest
from flask import Flask
from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.tipo_comprobante import TipoComprobante
from app.models.historial_ventas import HistorialVenta

# Prepara la app Flask y DB en memoria
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app

# Crea registros de prueba: usuario, producto, tipo_comprobante y venta
@pytest.fixture
def datos_de_historial(app):
    with app.app_context():
        usuario = Usuario(nombre="Ana", email="ana@gmail.com", rol="cliente")
        usuario.set_password("123")
        categoria = Categoria(nombre="Tecnología")
        producto = Producto(
            nombre="Monitor",
            marca="LG",
            descripcion="24 pulgadas",
            precio=500.0,
            stock=5,
            imagen_url="http://img.com/monitor.jpg",
            cliente=usuario,
            categoria=categoria
        )
        tipo = TipoComprobante(nombre="Boleta")
        db.session.add_all([usuario, categoria, producto, tipo])
        db.session.commit()

        historial = HistorialVenta(
            cliente_id=usuario.id,
            producto_id=producto.id,
            cantidad=2,
            total_venta=1000.0,
            tipo_comprobante_id=tipo.id
        )
        db.session.add(historial)
        db.session.commit()

        yield historial

# ✅ Verifica que los datos básicos del historial se asignen correctamente
def test_datos_basicos_de_historial(app, datos_de_historial):
    with app.app_context():
        historial = HistorialVenta.query.first()
        assert historial.cantidad == 2
        assert historial.total_venta == 1000.0
        assert historial.cliente.nombre == "Ana"
        assert historial.producto.nombre == "Monitor"

# ✅ Verifica que la fecha de venta se asigne automáticamente
def test_fecha_venta_automatica(app, datos_de_historial):
    with app.app_context():
        historial = HistorialVenta.query.first()
        assert historial.fecha_venta is not None

# ✅ Verifica que el método to_dict incluya datos coherentes
def test_convertir_historial_a_diccionario(app, datos_de_historial):
    with app.app_context():
        historial = HistorialVenta.query.first()
        datos = historial.to_dict()
        assert datos["cantidad"] == 2
        assert datos["total_venta"] == 1000.0
        assert datos["producto_id"] == historial.producto.id
        assert datos["cliente_id"] == historial.cliente.id
        assert datos["tipo_comprobante_id"] == historial.tipo_comprobante_id

# ✅ Verifica que el __repr__ muestra el total de la venta
def test_representacion_legible_historial(app, datos_de_historial):
    with app.app_context():
        historial = HistorialVenta.query.first()
        assert f"{historial.total_venta}" in repr(historial)
