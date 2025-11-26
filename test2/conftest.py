import os
import pytest
from app import main
from app.extensions import db
from app.models import Usuario  # 👈 cambiamos Cliente → Usuario


@pytest.fixture(scope="session")
def app():
    """
    Crea una instancia especial de la app SOLO para los tests en test2/,
    usando SQLite en lugar de la BD real.
    """
    # ✅ Creamos una app normal SIN pasar argumentos
    app = main.create_app()

    # ⚙️ Cambiamos solo la base de datos a una temporal y activamos modo testing
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///test_temp.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # 🔄 Inicializamos las tablas y agregamos datos mínimos obligatorios
    with app.app_context():
        db.create_all()

        # 💡 Crea un usuario base para evitar errores de relaciones con usuario_id o cliente_id
        if not Usuario.query.first():
            usuario = Usuario(
                nombre="Usuario de prueba",
                email="test@demo.com",
                password="1234"
            )
            db.session.add(usuario)
            db.session.commit()

    yield app

    # 🧹 Limpieza al finalizar los tests
    with app.app_context():
        db.drop_all()
    if os.path.exists("test_temp.db"):
        os.remove("test_temp.db")


@pytest.fixture()
def client(app):
    """Cliente de pruebas Flask."""
    return app.test_client()
