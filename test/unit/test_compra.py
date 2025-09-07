import pytest
from flask import Flask
from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.tipo_comprobante import TipoComprobante
from app.models.compra import Compra
from app.models.compra_producto import CompraProducto

# Configura la app y la base de datos en memoria
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app

# Carga datos de prueba: usuario, producto, compra, relación compra-producto
@pytest.fixture
def datos_de_prueba(app):
    with app.app_context():
        usuario = Usuario(nombre="Juan", email="juan@gmail.com", rol="cliente")
        usuario.set_password("123")
        categoria = Categoria(nombre="Electrónica")
        producto = Producto(
            nombre="Mouse",
            marca="Logitech",
            descripcion="Mouse óptico",
            precio=100.0,
            stock=10,
            imagen_url="http://img.com/mouse.jpg",
            cliente=usuario,
            categoria=categoria
        )
        tipo_comprobante = TipoComprobante(id=1, nombre="Boleta")

        db.session.add_all([usuario, categoria, producto, tipo_comprobante])
        db.session.commit()

        compra = Compra(
            cliente_id=usuario.id,
            tipo_comprobante_id=1,
            dni="12345678",
            total=200.0,
            email_destino="cliente@gmail.com"
        )
        db.session.add(compra)
        db.session.commit()

        relacion = CompraProducto(
            compra_id=compra.id,
            producto_id=producto.id,
            cantidad=2
        )
        db.session.add(relacion)
        db.session.commit()

        yield {
            "usuario": usuario,
            "producto": producto,
            "compra": compra,
            "relacion": relacion
        }

# Verifica que la fecha se asigne automáticamente
def test_fecha_asignada_automaticamente(app, datos_de_prueba):
    with app.app_context():
        compra = datos_de_prueba["compra"]
        assert compra.fecha is not None

# Verifica que el total sea el esperado 
def test_total_compra_correcto(app, datos_de_prueba):
    with app.app_context():
        compra = datos_de_prueba["compra"]
        assert compra.total == 200.0

# Verifica que los productos están relacionados con la compra
def test_productos_relacionados_con_compra(app, datos_de_prueba):
    with app.app_context():
        compra = datos_de_prueba["compra"]
        assert len(compra.productos) == 1
        assert compra.productos[0].producto.nombre == "Mouse"

# Verifica que se lance error si el RUC es inválido en factura
def test_ruc_invalido_lanza_error(app):
    with app.app_context():
        usuario = Usuario(nombre="Carlos", email="carlos@gmail.com", rol="cliente")
        db.session.add(usuario)
        tipo_comprobante = TipoComprobante(id=2, nombre="Factura")
        db.session.add(tipo_comprobante)
        db.session.commit()

        compra = Compra(
            cliente_id=usuario.id,
            tipo_comprobante_id=2,
            ruc="123",  # RUC inválido
            total=100.0,
            email_destino="archie@gmail.com"
        )

        db.session.add(compra)
        with pytest.raises(ValueError, match="RUC debe tener 11 caracteres"):
            db.session.flush()
