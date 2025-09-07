import pytest
from flask import Flask
from app.extensions import db
from app.models.tipo_comprobante import TipoComprobante

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.app_context():
        db.init_app(app)
        db.create_all()

        # Insertamos directamente en este contexto
        db.session.add_all([
            TipoComprobante(nombre="Boleta"),
            TipoComprobante(nombre="Factura")
        ])
        db.session.commit()
        yield app

# Verifica que se asignen correctamente los nombres a los tipos
def test_asignacion_correcta_de_tipos(app):
    with app.app_context():
        tipos = TipoComprobante.query.all()
        nombres = [tipo.nombre for tipo in tipos]
        assert "Boleta" in nombres
        assert "Factura" in nombres

# Verifica que el método to_dict funcione con ambos tipos
def test_convertir_ambos_tipos_a_diccionario(app):
    with app.app_context():
        boleta = TipoComprobante.query.filter_by(nombre="Boleta").first()
        factura = TipoComprobante.query.filter_by(nombre="Factura").first()

        assert boleta.to_dict()["nombre"] == "Boleta"
        assert factura.to_dict()["nombre"] == "Factura"

# Verifica que la representación __repr__ funcione para ambos
def test_representacion_legible_de_tipos(app):
    with app.app_context():
        boleta = TipoComprobante.query.filter_by(nombre="Boleta").first()
        factura = TipoComprobante.query.filter_by(nombre="Factura").first()

        assert "Boleta" in repr(boleta)
        assert "Factura" in repr(factura)
