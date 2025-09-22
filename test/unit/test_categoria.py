import pytest
from flask import Flask
from app.extensions import db
from app.models.categoria import Categoria

# Configura la aplicación Flask y la base de datos SQLite en memoria
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app

# Sesión de base de datos con una categoría de prueba
@pytest.fixture
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db.session

# Verifica que se puede crear una categoría correctamente
def test_creacion_de_categoria(app, db_session):
    with app.app_context():
        categoria = Categoria(nombre="Ropa")
        db_session.add(categoria)
        db_session.commit()

        categoria_encontrada = Categoria.query.filter_by(nombre="Ropa").first()
        assert categoria_encontrada is not None
        assert categoria_encontrada.nombre == "Ropa"

# Verifica que el método to_dict de categoría devuelva los datos esperados
def test_conversion_categoria_a_diccionario(app, db_session):
    with app.app_context():
        categoria = Categoria(nombre="Juguetes")
        db_session.add(categoria)
        db_session.commit()

        categoria_dict = categoria.to_dict()
        assert categoria_dict["nombre"] == "Juguetes"
        assert "id" in categoria_dict

# Verifica que no se puedan registrar dos categorías con el mismo nombre
def test_nombre_categoria_unico(app, db_session):
    with app.app_context():
        categoria1 = Categoria(nombre="Videojuegos")
        db_session.add(categoria1)
        db_session.commit()

        categoria2 = Categoria(nombre="Videojuegos")
        db_session.add(categoria2)

        with pytest.raises(Exception):
            db_session.commit()
