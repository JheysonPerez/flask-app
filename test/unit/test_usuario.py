import pytest
from flask import Flask
from app.extensions import db
from app.models.usuario import Usuario

# Configura la app Flask para pruebas
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app

# Provee una sesión de base de datos limpia para cada test
@pytest.fixture
def db_session(app):
    with app.app_context():
        yield db.session

# Verifica que se crea un usuario correctamente
def test_creacion_basica_usuario(app, db_session):
    with app.app_context():
        usuario = Usuario(nombre="Ana", email="ana@gmail.com", rol="cliente")
        usuario.set_password("123456")
        db.session.add(usuario)
        db.session.commit()

        assert usuario.id is not None
        assert usuario.nombre == "Ana"
        assert usuario.email == "ana@gmail.com"

# Verifica el funcionamiento del hash y validación de contraseña
def test_validacion_contrasena_usuario(app, db_session):
    with app.app_context():
        usuario = Usuario(nombre="Luis", email="luis@gmail.com", rol="cliente")
        usuario.set_password("secreto")
        db.session.add(usuario)
        db.session.commit()

        assert usuario.check_password("secreto") is True
        assert usuario.check_password("incorrecto") is False

# Verifica que el método to_dict devuelve los datos esperados
def test_convertir_usuario_a_diccionario(app, db_session):
    with app.app_context():
        usuario = Usuario(nombre="Luz", email="luz@gmail.com", rol="administrador")
        usuario.set_password("clave")
        db.session.add(usuario)
        db.session.commit()

        user_dict = usuario.to_dict()
        assert user_dict["nombre"] == "Luz"
        assert user_dict["email"] == "luz@gmail.com"
        assert user_dict["rol"] == "administrador"
        assert "password_hash" not in user_dict

# Verifica que se pueda crear un usuario desde un diccionario
def test_creacion_usuario_desde_diccionario(app, db_session):
    with app.app_context():
        data = {
            "nombre": "Carlos",
            "email": "carlos@gmail.com",
            "password": "clave123",
            "rol": "cliente"
        }
        usuario = Usuario.create_from_dict(data)
        assert usuario is not None
        assert usuario.nombre == "Carlos"
        assert usuario.check_password("clave123") is True

# Verifica que no se permita duplicar el email de usuario
def test_usuario_email_duplicado_no_permitido(app, db_session):
    with app.app_context():
        data = {
            "nombre": "Pedro",
            "email": "pedro@gmail.com",
            "password": "abc123",
            "rol": "cliente"
        }
        u1 = Usuario.create_from_dict(data)
        u2 = Usuario.create_from_dict(data)

        assert u1 is not None
        assert u2 is None  # Fallará por email duplicado
