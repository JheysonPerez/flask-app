#Mide el tiempo promedio de carga al insertar datos en gran escala
import os
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor

from app import main
from app.extensions import db
from app.models.usuario import Usuario
from app.models.compra import Compra

# Elimina la base de datos anterior de pruebas si existe
if os.path.exists("test.db"):
    os.remove("test.db")


def create_app():
    app = main.create_app(testing=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db?check_same_thread=False"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        if not Usuario.query.filter_by(email="denilson0@gmail.com").first():
            user = Usuario(nombre="Test", email="denilson0@gmail.com", rol="cliente")
            db.session.add(user)
            db.session.commit()
    return app


app = create_app()


# ---------------------- FUNCIONES DE SIMULACIÓN ----------------------

def simular_compra(email):
    with app.app_context():
        user = Usuario.query.filter_by(email=email).first()
        if not user:
            return False
        compra = Compra(
            cliente_id=user.id,
            tipo_comprobante_id=1,
            ruc=''.join(random.choices(string.digits, k=11)),
            dni=''.join(random.choices(string.digits, k=8)),
            total=random.uniform(10.0, 200.0),
            email_destino=user.email
        )
        try:
            db.session.add(compra)
            db.session.commit()
            return True
        except:
            db.session.rollback()
            return False

def simular_login(email):
    with app.app_context():
        return Usuario.query.filter_by(email=email).first() is not None

def simular_generacion_pdf(compra_id):
    time.sleep(0.01)  # Simula carga de procesamiento
    return True

def ejecutar_prueba_con_metrica(entradas, max_workers, funcion, titulo):
    print(f"\n🚀 Ejecutando prueba: {titulo}")
    inicio = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        resultados = list(executor.map(funcion, entradas))

    fin = time.time()
    duracion_total = fin - inicio
    exitosas = sum(resultados)
    tps = exitosas / duracion_total if duracion_total > 0 else 0
    promedio = duracion_total / len(entradas)

    print(f"🔄 Solicitudes totales: {len(entradas)}")
    print(f"✅ Solicitudes exitosas: {exitosas}")
    print(f"⏱️ Duración total: {duracion_total:.2f} s")
    print(f"📈 Tiempo promedio por solicitud: {promedio:.4f} s")
    print(f"⚡ TPS (transacciones/segundo): {tps:.2f}\n")


# ---------------------- COMPRAS SIMULTANEAS ----------------------

def test_compras_10():
    emails = ["denilson0@gmail.com"] * 10
    ejecutar_prueba_con_metrica(emails, 5, simular_compra, "Compras Concurrentes - 10")

def test_compras_100():
    emails = ["denilson0@gmail.com"] * 100
    ejecutar_prueba_con_metrica(emails, 10, simular_compra, "Compras Concurrentes - 100")

def test_compras_1000():
    emails = ["denilson0@gmail.com"] * 1000
    ejecutar_prueba_con_metrica(emails, 20, simular_compra, "Compras Concurrentes - 1000")


# ---------------------- LOGINS SIMULTANEAS ----------------------

def test_logins_10():
    emails = ["denilson0@gmail.com"] * 10
    ejecutar_prueba_con_metrica(emails, 5, simular_login, "Logins Concurrentes - 10")

def test_logins_100():
    emails = ["denilson0@gmail.com"] * 100
    ejecutar_prueba_con_metrica(emails, 10, simular_login, "Logins Concurrentes - 100")

def test_logins_1000():
    emails = ["denilson0@gmail.com"] * 1000
    ejecutar_prueba_con_metrica(emails, 20, simular_login, "Logins Concurrentes - 1000")


# ---------------------- GENERACIÓN DE PDFS ----------------------

def test_pdfs_10():
    compra_ids = [1] * 10
    ejecutar_prueba_con_metrica(compra_ids, 5, simular_generacion_pdf, "PDFs Concurrentes - 10")

def test_pdfs_100():
    compra_ids = [1] * 100
    ejecutar_prueba_con_metrica(compra_ids, 10, simular_generacion_pdf, "PDFs Concurrentes - 100")

def test_pdfs_1000():
    compra_ids = [1] * 1000
    ejecutar_prueba_con_metrica(compra_ids, 20, simular_generacion_pdf, "PDFs Concurrentes - 1000")
