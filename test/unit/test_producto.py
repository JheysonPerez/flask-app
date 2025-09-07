import pytest
from flask import Flask
from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.tipo_comprobante import TipoComprobante
from app.models.compra import Compra
from app.models.compra_producto import CompraProducto

# Configura una aplicación Flask y base de datos SQLite en memoria para pruebas
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app

# Crea datos de prueba en la base de datos: usuario, categoría y producto
@pytest.fixture
def db_session(app):
    with app.app_context():
        usuario = Usuario(nombre="Cliente Prueba", email="cliente@prueba.com", rol="cliente")
        usuario.set_password("123")
        categoria = Categoria(nombre="Electrónica")
        db.session.add_all([usuario, categoria])
        db.session.commit()

        producto = Producto(
            nombre="Laptop",
            marca="Lenovo",
            descripcion="Laptop potente para desarrollo",
            precio=3500.0,
            stock=8,
            imagen_url="http://ejemplo.com/laptop.jpg",
            cliente_id=usuario.id,
            categoria_id=categoria.id
        )
        db.session.add(producto)
        db.session.commit()
        yield db.session

# Verifica que el método to_dict del modelo Producto devuelve los datos esperados
def test_producto_a_diccionario(app, db_session):
    with app.app_context():
        producto = Producto.query.first()
        prod_dict = producto.to_dict()
        assert prod_dict["nombre"] == "Laptop"
        assert prod_dict["marca"] == "Lenovo"
        assert prod_dict["categoria_nombre"] == "Electrónica"

# Verifica que el precio y el stock se asignaron correctamente
def test_precio_y_stock_producto(app, db_session):
    with app.app_context():
        producto = Producto.query.first()
        assert producto.precio == 3500.0
        assert producto.stock == 8

# Verifica que el usuario tiene productos relacionados correctamente
def test_usuario_con_productos(app, db_session):
    with app.app_context():
        usuario = Usuario.query.first()
        assert usuario.productos.count() == 1
        assert usuario.productos.first().nombre == "Laptop"
