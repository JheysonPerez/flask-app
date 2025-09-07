# Mide el rendimiento al generar un test de creacion de pdf (boleta y factura) 
import os
import time
import pytest
from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from concurrent.futures import ThreadPoolExecutor

from app.extensions import db
from app.models.usuario import Usuario
from app.models.tipo_comprobante import TipoComprobante
from app.models.compra import Compra
from app.routes.compra import compra_bp


def create_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../app"))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static")
    )
    app.config["SECRET_KEY"] = "clave-test"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test_pdf_rendimiento.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}
    app.config["TESTING"] = True

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with app.app_context():
            return db.session.get(Usuario, int(user_id))

    app.register_blueprint(compra_bp)
    return app


@pytest.fixture(scope="session", autouse=True)
def setup_pdf_test_data():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        boleta = TipoComprobante(nombre="boleta")
        factura = TipoComprobante(nombre="factura")
        db.session.add_all([boleta, factura])
        db.session.flush()

        user = Usuario(
            nombre="Denilson",
            email="denilson0@gmail.com",
            rol="cliente",
            estado="activo"
        )
        user.password_hash = generate_password_hash("Pass1234!")
        db.session.add(user)
        db.session.flush()

        compra_boleta = Compra(
            cliente_id=user.id,
            tipo_comprobante_id=boleta.id,
            ruc="",
            dni="72257140",
            total=150.75,
            email_destino=user.email
        )

        compra_factura = Compra(
            cliente_id=user.id,
            tipo_comprobante_id=factura.id,
            ruc="10722571402",
            dni="",
            total=240.00,
            email_destino=user.email
        )

        db.session.add_all([compra_boleta, compra_factura])
        db.session.commit()
    yield
    try:
        os.remove("test_pdf_rendimiento.db")
    except FileNotFoundError:
        pass


# Función para PDF de boleta
def generar_pdf_boleta():
    app = create_app()
    client = app.test_client()

    with app.app_context():
        user = Usuario.query.filter_by(email="denilson0@gmail.com").first()
        compra = Compra.query.filter_by(cliente_id=user.id).filter(Compra.dni != "").first()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    response = client.get(f"/compra/{compra.id}/pdf")
    return response.status_code == 200


# Función para PDF de factura
def generar_pdf_factura():
    app = create_app()
    client = app.test_client()

    with app.app_context():
        user = Usuario.query.filter_by(email="denilson0@gmail.com").first()
        compra = Compra.query.filter_by(cliente_id=user.id).filter(Compra.ruc != "").first()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    response = client.get(f"/compra/{compra.id}/pdf")
    return response.status_code == 200


# Función base para test
def ejecutar_prueba(nombre, funcion, cantidad, workers):
    print(f"\n🚀 {nombre} - {cantidad} PDF")
    inicio = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        resultados = list(executor.map(lambda _: funcion(), range(cantidad)))

    fin = time.time()
    exitosas = sum(resultados)
    duracion = fin - inicio
    promedio = duracion / cantidad
    tps = exitosas / duracion if duracion > 0 else 0

    print(f"✅ Éxito: {exitosas}/{cantidad}")
    print(f"⏱️ Tiempo total: {duracion:.2f} s")
    print(f"📄 Promedio por PDF: {promedio:.4f} s")
    print(f"⚡ TPS (transacciones/segundo): {tps:.2f}\n")


# -------------------- TESTS ---------------------

@pytest.mark.parametrize("cantidad,workers", [(10, 5), (100, 10), (1000, 20)])
def test_pdf_boleta_concurrente(cantidad, workers):
    ejecutar_prueba("Boleta PDF", generar_pdf_boleta, cantidad, workers)


@pytest.mark.parametrize("cantidad,workers", [(10, 5), (100, 10), (1000, 20)])
def test_pdf_factura_concurrente(cantidad, workers):
    ejecutar_prueba("Factura PDF", generar_pdf_factura, cantidad, workers)
