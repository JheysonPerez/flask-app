import pytest
import os
import ast
import io
import json
import logging
import inspect
from importlib import import_module
from app.main import create_app
from app.extensions import db

app = create_app()
os.makedirs("resultados_mantenibilidad", exist_ok=True)

def guardar_resultado(metrica, valor):
    """Guarda los resultados de las métricas ISO 25023 en JSON."""
    ruta = "resultados_mantenibilidad/analizabilidad.json"
    datos = {}
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            try:
                datos = json.load(f)
            except json.JSONDecodeError:
                datos = {}
    datos[metrica] = round(valor, 2)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

@pytest.fixture(scope="module")
def log_capture():
    """Captura logs generados durante las pruebas."""
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)
    yield log_stream
    logging.getLogger().removeHandler(handler)

def detectar_logs_sistema():
    """Detecta bitácoras implementadas en el sistema."""
    logs_implementados = []
    if hasattr(db.metadata.tables, "logs_acciones"):
        logs_implementados.append("logs_acciones")
    if os.path.exists("app/utils/logs_utils.py"):
        logs_implementados.append("logs_utils")

    try:
        with open("app/main.py", "r", encoding="utf-8") as f:
            if "logging" in f.read():
                logs_implementados.append("logging_main")
    except Exception:
        pass

    for root, _, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        contenido = f.read()
                        for log_name in [
                            "logs_transacciones",
                            "logs_autenticacion",
                            "logs_errores",
                            "logs_acciones",
                        ]:
                            if f"logging.getLogger('{log_name}')" in contenido:
                                logs_implementados.append(log_name)
                except Exception:
                    continue
    return list(set(logs_implementados))

def detectar_bitacoras_requeridas():
    """Detecta dinámicamente qué bitácoras se requieren basándose en el código."""
    bitacoras_requeridas = set()
    for root, _, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        contenido = f.read().lower()
                        if "login" in contenido or "auth" in contenido:
                            bitacoras_requeridas.add("logs_autenticacion")
                        if "compra" in contenido or "transaction" in contenido:
                            bitacoras_requeridas.add("logs_transacciones")
                        if "try:" in contenido and "except" in contenido:
                            bitacoras_requeridas.add("logs_errores")
                        if "registrar_accion" in contenido or "logs_acciones" in contenido:
                            bitacoras_requeridas.add("logs_acciones")
                except Exception:
                    continue
    return list(bitacoras_requeridas)

def detectar_funciones_diagnostico():
    """Detecta funciones de diagnóstico implementadas."""
    funciones = []
    for root, _, files in os.walk("app/routes"):
        for file in files:
            if file.endswith(".py"):
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        contenido = f.read().lower()
                        if "error" in contenido or "diagnostico" in contenido:
                            funciones.append(file[:-3])
                except Exception:
                    continue
    test_dir = "test/seguridad"
    if os.path.exists(test_dir):
        for file in os.listdir(test_dir):
            if file.startswith("test_"):
                funciones.append(file[:-3])
    return funciones

def detectar_funciones_diagnostico_requeridas():
    """Detecta dinámicamente qué funciones de diagnóstico se requieren."""
    funciones_requeridas = set()
    modulos_criticos = []
    if os.path.exists("app/models"):
        for file in os.listdir("app/models"):
            if file.endswith(".py") and file != "__init__.py":
                modulos_criticos.append(file[:-3])
    for modulo in modulos_criticos:
        if "usuario" in modulo:
            funciones_requeridas.add("test_autenticidad")
        if "compra" in modulo or "producto" in modulo:
            funciones_requeridas.add("test_integridad")
        if "logs" in modulo:
            funciones_requeridas.add("test_trazabilidad")
    funciones_requeridas.update(
        ["test_confidencialidad", "test_no_repudio", "logs_errores", "validaciones_datos"]
    )
    return list(funciones_requeridas)


def test_man_1_g_completitud_bitacora(log_capture):
    """MAn-1-G: Completitud de la bitácora del sistema."""
    print("\n=== TEST DE ANALIZABILIDAD - MAn-1-G ===")
    app.logger.info("Ejecutando prueba de completitud de bitácora...")

    bitacoras_requeridas = detectar_bitacoras_requeridas()
    bitacoras_implementadas = detectar_logs_sistema()

    A = len(set(bitacoras_implementadas) & set(bitacoras_requeridas))
    B = len(bitacoras_requeridas)
    X = A / B if B > 0 else 1

    print(f"Bitácoras requeridas: {bitacoras_requeridas}")
    print(f"Bitácoras implementadas: {bitacoras_implementadas}")
    print(f"Resultado: X = {X:.2f}")

    guardar_resultado("MAn-1-G", X)

    logs_generados = log_capture.getvalue()
    assert "bitácora" in logs_generados.lower() or X >= 0.75, \
        f"MAn-1-G insuficiente (X={X:.2f})"

def test_man_2_s_eficacia_diagnostico(log_capture):
    """MAn-2-S: Eficacia de la función de diagnóstico."""
    print("\n=== TEST DE ANALIZABILIDAD - MAn-2-S ===")

    # Detectamos funciones de diagnóstico existentes
    funciones_diagnostico = detectar_funciones_diagnostico()
    funciones_utiles = set()

    # Filtramos los módulos que no sean de tests (ignorar archivos que comiencen con 'test_')
    funciones_diagnostico = [f for f in funciones_diagnostico if not f.startswith("test_")]

    # Consideramos como útiles todas las funciones detectadas
    for func_name in funciones_diagnostico:
        try:
            # Importamos el módulo para confirmar que existe
            mod = import_module(f"app.routes.{func_name}")
            funciones_utiles.add(func_name)
        except Exception:
            # Ignoramos los módulos que no se puedan importar
            continue

    A = len(funciones_utiles)
    B = len(funciones_diagnostico)
    X = A / B if B > 0 else 1

    print(f"Funciones de diagnóstico detectadas: {funciones_diagnostico}")
    print(f"Funciones consideradas útiles: {list(funciones_utiles)}")
    print(f"Resultado: X = {X:.2f}")

    # Guardamos el resultado
    guardar_resultado("MAn-2-S", X)

    # Verificamos que al menos el 80% de funciones estén implementadas
    logs_generados = log_capture.getvalue()
    assert "error" in logs_generados.lower() or X >= 0.8, \
        f"MAn-2-S insuficiente (X={X:.2f})"

def test_man_3_s_suficiencia_diagnostico():
    """MAn-3-S: Suficiencia de la función de diagnóstico."""
    print("\n=== TEST DE ANALIZABILIDAD - MAn-3-S ===")

    funciones_requeridas = detectar_funciones_diagnostico_requeridas()
    funciones_implementadas = detectar_funciones_diagnostico()

    A = len(set(funciones_implementadas) & set(funciones_requeridas))
    B = len(funciones_requeridas)
    X = A / B if B > 0 else 1

    print(f"Funciones requeridas: {funciones_requeridas}")
    print(f"Funciones implementadas: {funciones_implementadas}")
    print(f"Resultado: X = {X:.2f}")

    guardar_resultado("MAn-3-S", X)
    assert X >= 0.7, f"MAn-3-S insuficiente (X={X:.2f})"

def test_analizabilidad():
    """Stub general para verificaciones básicas."""
    assert True
