import os
import pytest
from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.usuario import Usuario
from app.routes.admin import bp_admin  

TEMPLATES_PATH = os.path.abspath("app/templates")

@pytest.fixture
def app():
    app = Flask(__name__, template_folder=TEMPLATES_PATH)
    app.config['SECRET_KEY'] = 'clave-test'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True

    db.init_app(app)

    # Configura Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    app.register_blueprint(bp_admin)

    with app.app_context():
        db.create_all()
        # Crear usuarios para tests
        admin = Usuario(nombre="Juan Pérez", email="juan.perez@gmail.com", rol="administrador", estado="activo")
        admin.password_hash = generate_password_hash("AdminPass2025!")
        db.session.add(admin)

        cliente = Usuario(nombre="María López", email="maria.lopez@gmail.com", rol="cliente", estado="activo")
        cliente.password_hash = generate_password_hash("ClientePass2025!")
        db.session.add(cliente)

        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login_admin(client, app):
    with app.app_context():
        admin = Usuario.query.filter_by(email="juan.perez@gmail.com").first()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
    yield client


@pytest.fixture
def login_cliente(client, app):
    with app.app_context():
        cliente = Usuario.query.filter_by(email="maria.lopez@gmail.com").first()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(cliente.id)
    yield client


# Cliente no puede acceder a lista de clientes admin 
def test_acceso_restringido_para_no_admin(login_cliente):
    res = login_cliente.get("/admin/clientes")
    assert res.status_code == 403


# GET formulario para crear nuevo cliente 
def test_crear_cliente_get(login_admin):
    res = login_admin.get("/admin/clientes/nuevo")
    assert res.status_code == 200
    assert b"nombre" in res.data.lower()


# POST crea cliente nuevo con datos reales y confirma guardado
def test_crear_cliente_post(login_admin):
    data = {
        "nombre": "Carlos Mendoza",
        "email": "carlos.mendoza@hotmail.com",
        "estado": "activo",
        "password": "PassSegura2025!"
    }
    res = login_admin.post("/admin/clientes/nuevo", data=data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Cliente creado" in res.data
    nuevo = Usuario.query.filter_by(email="carlos.mendoza@hotmail.com").first()
    assert nuevo is not None
    assert nuevo.nombre == "Carlos Mendoza"
    assert nuevo.rol == "cliente"


# Ver detalle cliente existente
def test_ver_detalle_cliente(login_admin):
    cliente = Usuario.query.filter_by(rol="cliente").first()
    res = login_admin.get(f"/admin/clientes/{cliente.id}")
    assert res.status_code == 200
    assert bytes(cliente.nombre, "utf-8") in res.data


# Editar cliente vía GET y POST, confirmando cambios
def test_editar_cliente_get_post(login_admin):
    cliente = Usuario.query.filter_by(rol="cliente").first()
    res_get = login_admin.get(f"/admin/clientes/{cliente.id}/editar")
    assert res_get.status_code == 200
    assert bytes(cliente.nombre, "utf-8") in res_get.data

    data_edit = {
        "nombre": "María López Actualizada",
        "email": cliente.email,
        "estado": cliente.estado
    }
    res_post = login_admin.post(f"/admin/clientes/{cliente.id}/editar", data=data_edit, follow_redirects=True)
    assert res_post.status_code == 200
    assert b"Cliente actualizado" in res_post.data

    cliente_actualizado = Usuario.query.get(cliente.id)
    assert cliente_actualizado.nombre == "María López Actualizada"


# Borrar cliente y verificar que desaparece
def test_borrar_cliente(login_admin):
    nuevo = Usuario(nombre="Eliminar Cliente", email="eliminar.cliente@gmail.com", rol="cliente", estado="activo")
    nuevo.password_hash = generate_password_hash("EliminarPass2025!")
    db.session.add(nuevo)
    db.session.commit()

    res = login_admin.post(f"/admin/clientes/{nuevo.id}/borrar", follow_redirects=True)
    assert res.status_code == 200
    assert b"Cliente eliminado" in res.data

    eliminado = Usuario.query.get(nuevo.id)
    assert eliminado is None


# Cambiar estado cliente a "inactivo" y verificar persistencia
def test_cambiar_estado_cliente(login_admin):
    cliente = Usuario.query.filter_by(rol="cliente").first()
    res = login_admin.post(f"/admin/clientes/{cliente.id}/estado", data={"estado": "inactivo"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Estado actualizado" in res.data

    actualizado = Usuario.query.get(cliente.id)
    assert actualizado.estado == "inactivo"
