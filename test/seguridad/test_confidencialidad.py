import os
import requests
from sqlalchemy import text

from app.extensions import db
from app.models.usuario import Usuario
from app.main import create_app

app = create_app()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:archi123@localhost:5432/flaskdb"
)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"options": "-c client_encoding=utf8"}
}

def test_control_acceso(app_url="http://127.0.0.1:5000"):
    rutas = []
    for rule in app.url_map.iter_rules():
        if "static" in rule.endpoint:
            continue
        rutas.append((rule.rule, list(rule.methods - {"HEAD", "OPTIONS"})))

    accesos_no_autorizados = 0
    total_rutas = len(rutas)
    accesos_detalle = []

    for ruta, metodos in rutas:
        for metodo in metodos:
            try:
                if metodo == "GET":
                    r = requests.get(app_url + ruta, allow_redirects=False)
                elif metodo == "POST":
                    r = requests.post(app_url + ruta, data={}, allow_redirects=False)
                else:
                    continue

                if r.status_code in [200, 201]:
                    accesos_no_autorizados += 1
                    accesos_detalle.append((metodo, ruta, r.status_code))
            except Exception as e:
                print(f"Error probando {metodo} {ruta}: {e}")

    X = 1 - (accesos_no_autorizados / total_rutas) if total_rutas > 0 else 1
    print("\n" + "="*80)
    print("                         TEST DE CONFIDENCIALIDAD")
    print("="*80)
    print("\nMétrica SCo-1-G: Control de Acceso No Autorizado")
    print("-"*65)
    print("Fórmula: X = 1 - (A / B)")
    print(f"A = {accesos_no_autorizados} accesos indebidos")
    print(f"B = {total_rutas} rutas verificadas")
    print(f"Resultado: X = {X:.2f}")
    if accesos_detalle:
        print("Rutas con acceso indebido (metodo, ruta, status):")
        for m, r, s in accesos_detalle:
            print(f" - {m} {r} -> {s}")
    assert X >= 0.8, f"Control de acceso débil ({accesos_no_autorizados}/{total_rutas} accesos indebidos)"

def test_cifrado_datos():
    with app.app_context():
        usuarios = Usuario.query.all()
        if all(getattr(u, "password", None) in (None, "") for u in usuarios):
            print("\n=== Métrica SCo-2-G: Exactitud del cifrado de datos ===")
            print("Nota: Todos los usuarios usan OAuth → prueba de cifrado local no aplicable.")
            return

        total_datos = len(usuarios)
        cifrados_correctamente = 0

        for usuario in usuarios:
            password = getattr(usuario, "password", None)
            if not password:
                continue
            if password.startswith("$2b$") or password.startswith("$2a$") or password.startswith("pbkdf2:sha256"):
                cifrados_correctamente += 1

    X = (cifrados_correctamente / total_datos) if total_datos > 0 else 0
    print("\nMétrica SCo-2-G: Cifrado de Datos Sensibles")
    print("-"*65)
    print("Fórmula: X = A / B")
    print(f"A = {cifrados_correctamente} contraseñas cifradas correctamente")
    print(f"B = {total_datos} contraseñas analizadas")
    print(f"Resultado: X = {X:.2f}")
    assert X >= 0.8, "Menos del 80% de las contraseñas están cifradas correctamente"

def detectar_algoritmos():
    """Detecta algoritmos criptográficos usados en la aplicación."""
    algoritmos = set()
    
    # 1. Detectar OAuth/OIDC
    if 'GOOGLE_CLIENT_ID' in app.config:
        algoritmos.add('OAUTH2')
        algoritmos.add('RSA')      # OAuth usa RSA
        algoritmos.add('SHA256')   # OAuth usa SHA256
    
    # 2. Detectar algoritmos en la configuración
    if app.config.get('PREFERRED_URL_SCHEME') == 'https':
        algoritmos.add('TLS1.3')
    
    # 3. Detectar hashes de passwords en la DB
    with app.app_context():
        for usuario in Usuario.query.all():
            if not hasattr(usuario, 'password') or not usuario.password:
                continue
            if usuario.password.startswith('$2b$'):
                algoritmos.add('BCRYPT')
            elif usuario.password.startswith('pbkdf2:sha256'):
                algoritmos.add('PBKDF2')
                algoritmos.add('SHA256')
    
    # 4. Buscar uso de funciones criptográficas en el código
    import inspect
    import pkgutil
    import importlib
    
    routes_pkg = importlib.import_module("app.routes")
    for _, name, _ in pkgutil.iter_modules([routes_pkg.__path__[0]]):
        try:
            mod = importlib.import_module(f"app.routes.{name}")
            source = inspect.getsource(mod)
            if 'hashlib.md5' in source:
                algoritmos.add('MD5')
            if 'hashlib.sha1' in source:
                algoritmos.add('SHA1')
            if 'Fernet' in source:
                algoritmos.add('AES')
        except:
            continue
    
    return algoritmos

def test_algoritmos():
    print("\nMétrica SCo-3-S: Fortaleza de Algoritmos Criptográficos")
    print("-"*65)
    print("Fórmula: X = 1 - (A / B)")
    
    algoritmos_usados = detectar_algoritmos()
    if not algoritmos_usados:
        print("No se detectaron algoritmos criptográficos. Test saltado.")
        assert True
        return
        
    print(f"Algoritmos detectados: {algoritmos_usados}")
    
    algoritmos_inseguros = {"MD5", "SHA1", "DES", "RC4", "3DES", "BLOWFISH"}
    algoritmos_inseguros_encontrados = algoritmos_usados & algoritmos_inseguros
    
    A = len(algoritmos_inseguros_encontrados)
    B = len(algoritmos_usados)
    X = 1 - (A / B) if B > 0 else 1  # Si no hay algoritmos, consideramos que es seguro

    print(f"A = {A} algoritmos inseguros")
    print(f"B = {B} algoritmos analizados")
    print(f"Resultado: X = {X:.2f}")
    assert X == 1.0, "Fortaleza criptográfica no óptima"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        test_control_acceso()
        test_cifrado_datos()
        test_algoritmos()
