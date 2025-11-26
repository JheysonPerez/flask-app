import os
import sys
import pytest
from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.extensions import db
from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.models.marca import Marca
from app.routes.cliente import bp_cliente

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))


# ⚙️ Función para crear una app por hilo
def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'clave-test'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_concurrente.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {"check_same_thread": False}
    }
    app.config['TESTING'] = True

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with app.app_context():
            return db.session.get(Usuario, int(user_id))

    app.register_blueprint(bp_cliente)
    return app


# 🔧 Configura la BD inicial con usuarios, categorías y marcas válidas
@pytest.fixture(scope="session", autouse=True)
def setup_db():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Crear usuarios y entidades relacionadas
        for i in range(5):
            email = f"cliente{i}@gmail.com"
            if not Usuario.query.filter_by(email=email).first():
                user = Usuario(
                    nombre=f"Cliente{i}",
                    email=email,
                    rol="cliente",
                    estado="activo"
                )
                user.password_hash = generate_password_hash("Pass1234!")
                db.session.add(user)
                db.session.flush()  # para obtener user.id antes de commit

                # Cada cliente tiene su categoría y marca
                categoria = Categoria(nombre=f"Accesorios{i}", cliente_id=user.id)
                marca = Marca(nombre=f"Logitech{i}", cliente_id=user.id)
                db.session.add_all([categoria, marca])

        db.session.commit()

    yield

    # Limpieza del archivo de prueba SQLite
    try:
        os.remove("test_concurrente.db")
    except FileNotFoundError:
        pass


# Login por sesión de cliente
def login_cliente_session(email):
    app = create_app()
    client = app.test_client()
    with app.app_context():
        user = Usuario.query.filter_by(email=email).first()
        if not user:
            raise ValueError(f"Usuario con email {email} no encontrado")
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
    return client


# Crear producto autenticado (agregando marca y categoría válidas)
def crear_producto_concurrente(email):
    app = create_app()
    with app.app_context():
        user = Usuario.query.filter_by(email=email).first()
        categoria = Categoria.query.filter_by(cliente_id=user.id).first()
        marca = Marca.query.filter_by(cliente_id=user.id).first()

    client = login_cliente_session(email)
    return client.post("/cliente/productos", json={
        "nombre": "Mouse Gamer",
        "descripcion": "RGB 7 botones",
        "precio": 120.5,
        "stock": 10,
        "imagen_url": "http://img.local/mouse.jpg",
        "categoria_id": categoria.id,
        "marca_id": marca.id
    })


# Listar productos autenticado
def obtener_productos_concurrente(email):
    client = login_cliente_session(email)
    return client.get("/cliente/productos")


# 🧪 Test concurrente: crear productos
def test_concurrencia_crear_productos():
    emails = [f"cliente{i}@gmail.com" for i in range(5)]
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(crear_producto_concurrente, email) for email in emails]
        resultados = [f.result() for f in as_completed(futures)]

    for res in resultados:
        assert res.status_code == 201
        assert b"Producto creado" in res.data


# 🧪 Test concurrente: listar productos
def test_concurrencia_listar_productos():
    emails = [f"cliente{i}@gmail.com" for i in range(5)]
    for email in emails:
        crear_producto_concurrente(email)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(obtener_productos_concurrente, email) for email in emails]
        resultados = [f.result() for f in as_completed(futures)]

    for res in resultados:
        assert res.status_code == 200
        assert b"Mouse Gamer" in res.data
