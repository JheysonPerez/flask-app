import pytest
import os
import re  
from app.main import create_app

app = create_app()

def detectar_funciones_prueba():
    """Detecta funciones de prueba implementadas (file names + defs internos)."""
    funciones_prueba = set()  # Set para unicidad

    # NUEVO: Por nombres de archivos test_xxx.py
    test_dir = 'test'
    if os.path.exists(test_dir):
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    file_name = file[5:-3]  # Strip 'test_' y '.py' → 'analizabilidad'
                    funciones_prueba.add(file_name.lower())

    # + Defs internos con regex
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            contenido = f.read()
                            # Extraer full names post 'test_'
                            matches = re.findall(r'def test_(\w+(?:_\w+)*)', contenido)
                            for match in matches:
                                funciones_prueba.add(match.lower())
                    except:
                        continue

    return list(funciones_prueba)

def detectar_pruebas_autonomas():
    """Detecta pruebas que pueden ejecutarse de forma autónoma (dinámico: escanea todo test/)."""
    pruebas_autonomas = set()

    # Buscar todos los test files y chequea por dependencias externas
    test_dir = 'test'
    if os.path.exists(test_dir):
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_file = os.path.join(root, file)
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            contenido = f.read().lower()
                            # Si NO usa dependencias externas (o usa mock)
                            if all(kw not in contenido for kw in ['requests.', 'http', 'db.session', 'external api']) or 'mock' in contenido:
                                pruebas_autonomas.add(file[5:-3])  # Nombre sin 'test_' y '.py'
                    except:
                        continue

    return list(pruebas_autonomas)

def detectar_capacidad_reinicio():
    """Detecta capacidad de reinicio de pruebas (dinámico: escanea todo test/)."""
    capacidad_reinicio = set()

    # Buscar fixtures o setups en todos los tests
    test_dir = 'test'
    if os.path.exists(test_dir):
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_file = os.path.join(root, file)
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            contenido = f.read().lower()
                            if '@pytest.fixture' in contenido or 'setup' in contenido or 'teardown' in contenido:
                                capacidad_reinicio.add(file[5:-3])
                    except:
                        continue

    return list(capacidad_reinicio)

def detectar_funciones_prueba_requeridas():
    """Detecta dinámicamente funciones de prueba requeridas basándose en módulos."""
    funciones_requeridas = set()

    # Basado en módulos críticos encontrados
    modulos_criticos = []

    # Buscar modelos
    modelos_dir = 'app/models'
    if os.path.exists(modelos_dir):
        for file in os.listdir(modelos_dir):
            if file.endswith('.py') and file != '__init__.py':
                modulos_criticos.append(file[:-3])

    # Para cada módulo crítico, agregar tests requeridos
    for modulo in modulos_criticos:
        if 'usuario' in modulo.lower():
            funciones_requeridas.add('test_autenticidad')
        if 'compra' in modulo.lower() or 'producto' in modulo.lower():
            funciones_requeridas.add('test_integridad')
        if 'logs' in modulo.lower():
            funciones_requeridas.add('test_trazabilidad')

    # Funciones básicas siempre requeridas
    funciones_requeridas.update([
        'test_confidencialidad',
        'test_no_repudio',
        'test_modularidad',
        'test_reutilizacion',
        'test_analizabilidad',
        'test_modificabilidad'
    ])

    return list(funciones_requeridas)

def detectar_pruebas_dependientes():
    """Detecta pruebas que dependen de otros sistemas (dinámico: escanea todo test/)."""
    pruebas_dependientes = set()

    # Tests que usan dependencias externas
    test_dir = 'test'
    if os.path.exists(test_dir):
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_file = os.path.join(root, file)
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            contenido = f.read().lower()
                            if any(kw in contenido for kw in ['requests.', 'http', 'db.session', 'external api']) and 'mock' not in contenido:
                                pruebas_dependientes.add(file[5:-3])
                    except:
                        continue

    return list(pruebas_dependientes)

def detectar_pruebas_pausables():
    """Detecta pruebas que pueden ser pausadas (dinámico: escanea todo test/)."""
    pruebas_pausables = set()

    # Todas las pruebas con fixtures pueden ser pausadas
    test_dir = 'test'
    if os.path.exists(test_dir):
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            contenido = f.read().lower()
                            if '@pytest.fixture' in contenido or 'yield' in contenido or 'scope' in contenido:
                                pruebas_pausables.add(file[5:-3])
                    except:
                        continue

    return list(pruebas_pausables)

def test_mte_1_g_completitud_pruebas():
    """MTe-1-G: Completitud de la función de prueba (match por file + substring)."""
    print("\n" + "="*80)
    print("                  TEST DE PROBABILIDAD")
    print("="*80)
    print("\nMétrica MTe-1-G: Completitud de la Función de Prueba")
    print("-"*65)
    print("Fórmula: X = A/B")
    print("A = Número de funciones de prueba implementadas")
    print("B = Número de funciones de prueba requeridas")

    funciones_requeridas = detectar_funciones_prueba_requeridas()
    funciones_implementadas = detectar_funciones_prueba()  # File names + defs

    # Exact or substring case-insensitive
    core_requeridas = [req.replace('test_', '').lower() for req in funciones_requeridas]
    print(f"Core requeridas para match: {core_requeridas}")  # Debug
    implementadas_coincidentes = []
    for func in funciones_implementadas:
        func_lower = func.lower()
        for core in core_requeridas:
            if core == func_lower or core in func_lower:  # Exact or substring
                implementadas_coincidentes.append(func)
                break

    A = len(set(implementadas_coincidentes))
    B = len(funciones_requeridas)
    X = min(A / B if B > 0 else 1, 1.0)  # Cap a 1.0

    print(f"Funciones requeridas: {funciones_requeridas}")
    print(f"Funciones implementadas: {funciones_implementadas}")
    print(f"Coincidencias: {implementadas_coincidentes}")
    print(f"A = {A} funciones implementadas")
    print(f"B = {B} funciones requeridas")
    print(f"Resultado: X = {X:.2f}")

    UMBRAL_MTE_1 = 0.7
    print(f"Umbral recomendado MTe-1-G: {UMBRAL_MTE_1}")
    assert X >= UMBRAL_MTE_1, f"MTe-1-G insuficiente: {A}/{B} funciones implementadas (X={X:.2f}) < umbral {UMBRAL_MTE_1}"

def test_mte_2_s_capacidad_autonoma():
    """MTe-2-S: Capacidad de ser probado en forma autónoma (cap X<=1.0)."""
    print("\nMétrica MTe-2-S: Capacidad de Ser Probado en Forma Autónoma")
    print("-"*65)
    print("Fórmula: X = A/B")
    print("A = Número de pruebas que pueden ser simuladas por stub")
    print("B = Número de pruebas que dependen de otros sistemas")

    pruebas_dependientes = detectar_pruebas_dependientes()
    pruebas_autonomas = detectar_pruebas_autonomas()

    A = len(pruebas_autonomas)
    B = len(pruebas_dependientes)
    X = min(A / B if B > 0 else 1, 1.0)  # Cap a 1.0

    print(f"Pruebas dependientes: {pruebas_dependientes}")
    print(f"Pruebas autónomas/simulables: {pruebas_autonomas}")
    print(f"A = {A} pruebas simulables")
    print(f"B = {B} pruebas dependientes")
    print(f"Resultado: X = {X:.2f}")

    UMBRAL_MTE_2 = 0.6
    print(f"Umbral recomendado MTe-2-S: {UMBRAL_MTE_2}")
    assert X >= UMBRAL_MTE_2, f"MTe-2-S insuficiente: {A}/{B} pruebas autónomas (X={X:.2f}) < umbral {UMBRAL_MTE_2}"

def test_mte_3_s_capacidad_reinicio():
    """MTe-3-S: Capacidad de reinicio de la prueba (cap X<=1.0)."""
    print("\nMétrica MTe-3-S: Capacidad de Reinicio de la Prueba")
    print("-"*65)
    print("Fórmula: X = A/B")
    print("A = Número de casos donde se puede pausar y reiniciar")
    print("B = Número de casos donde se puede pausar la ejecución")

    pruebas_con_reinicio = detectar_capacidad_reinicio()
    pruebas_pausables = detectar_pruebas_pausables()

    A = len(pruebas_con_reinicio)
    B = len(pruebas_pausables)
    X = min(A / B if B > 0 else 1, 1.0)  # Cap a 1.0

    print(f"Pruebas pausables: {pruebas_pausables}")
    print(f"Pruebas con reinicio: {pruebas_con_reinicio}")
    print(f"A = {A} pruebas con reinicio")
    print(f"B = {B} pruebas pausables")
    print(f"Resultado: X = {X:.2f}")

    UMBRAL_MTE_3 = 0.5
    print(f"Umbral recomendado MTe-3-S: {UMBRAL_MTE_3}")
    assert X >= UMBRAL_MTE_3, f"MTe-3-S insuficiente: {A}/{B} pruebas con reinicio (X={X:.2f}) < umbral {UMBRAL_MTE_3}"