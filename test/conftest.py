import pytest
from app import main
from app.extensions import db
from app.models.usuario import Usuario

@pytest.fixture(scope="session", autouse=True)
def setup_app():
    app = main.create_app(testing=True)
    with app.app_context():
        db.drop_all()
        db.create_all()
        # Agrega un usuario de prueba
        usuario = Usuario(
            nombre="Denilson Aguirre",
            email="denilson0@gmail.com",
            rol="cliente"
        )
        db.session.add(usuario)
        db.session.commit()
    yield
