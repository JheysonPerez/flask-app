import pytest
from flask import Flask
from app.extensions import db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.marca import Marca  # Importar el modelo Marca

# ==========================
# FIXTURE DE APLICACIÓN
# ==========================
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

# ==========================
# FIXTURE DE BASE DE DATOS
# ==========================
@pytest.fixture
def db_session(app):
    with app.app_context():
        # Crear usuario base
        usuario = Usuario(
            nombre="Cliente Prueba",
            email="cliente@prueba.com",
            rol="cliente",
            estado="activo"
        )
        usuario.set_password("123")
        db.session.add(usuario)
        db.session.commit()

        # Crear categoría asociada a la instancia del usuario
        categoria = Categoria(
            nombre="Electrónica",
            cliente=usuario  # ← PASAR LA INSTANCIA
        )
        db.session.add(categoria)
        db.session.commit()

        # Crear marca asociada al usuario
        marca = Marca(
            nombre="Lenovo",
            cliente=usuario  # ← PASAR LA INSTANCIA
        )
        db.session.add(marca)
        db.session.commit()

        # Crear producto asociado a instancias de usuario, categoría y marca
        producto = Producto(
            nombre="Laptop",
            descripcion="Laptop potente para desarrollo",
            precio=3500.0,
            stock=8,
            imagen_url="http://ejemplo.com/laptop.jpg",
            cliente=usuario,    # ← PASAR INSTANCIA
            categoria=categoria, # ← PASAR INSTANCIA
            marca=marca         # ← PASAR INSTANCIA, NO STRING
        )
        db.session.add(producto)
        db.session.commit()

        yield {
            "usuario": usuario,
            "categoria": categoria,
            "marca": marca,
            "producto": producto
        }

# ==========================
# TESTS DE PRODUCTO
# ==========================
def test_producto_a_diccionario(app, db_session):
    with app.app_context():
        producto = db_session["producto"]
        prod_dict = producto.to_dict()
        assert prod_dict["nombre"] == "Laptop"
        assert prod_dict["marca_nombre"] == "Lenovo"
        assert prod_dict["categoria_nombre"] == "Electrónica"

def test_precio_y_stock_producto(app, db_session):
    with app.app_context():
        producto = db_session["producto"]
        assert producto.precio == 3500.0
        assert producto.stock == 8

def test_usuario_con_productos(app, db_session):
    with app.app_context():
        usuario = db_session["usuario"]
        assert usuario.productos.count() == 1
        assert usuario.productos.first().nombre == "Laptop"
