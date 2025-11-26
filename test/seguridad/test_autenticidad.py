import pytest
from app.main import app
from app.extensions import db
from app.models.usuario import Usuario


@pytest.fixture(scope="module")
def test_client():
    with app.app_context():
        yield app.test_client()


def rutas_app():
    rutas = []
    for rule in app.url_map.iter_rules():
        if "static" in rule.endpoint:
            continue
        rutas.append((rule.rule, list(rule.methods - {"HEAD", "OPTIONS"}), rule.endpoint))
    return rutas


def detectar_caracteristicas_autenticacion():
    """Devuelve un dict con banderas sobre mecanismos detectados en la app."""
    rutas = rutas_app()

    has_password_login = any(("/api/login" in ruta or ruta.endswith("/login")) and "POST" in metodos and "google" not in ruta for ruta, metodos, _ in rutas)
    has_google_bp = "google" in app.blueprints
    has_jwt = bool(app.config.get("JWT_SECRET_KEY"))
    has_2fa = any("2fa" in name.lower() or "two_factor" in name.lower() for name in app.blueprints)

    return {
        "password": has_password_login,
        "oauth_google": has_google_bp,
        "jwt": has_jwt,
        "2fa": has_2fa,
    }


def test_suficiencia_mecanismos_autenticacion(test_client):
    """SAu-1-G: Suficiencia del mecanismo de autenticación

    A = Mecanismos implementados
    B = Mecanismos especificados
    """
    print("\n" + "="*80)
    print("                         TEST DE AUTENTICIDAD")
    print("="*80)
    especificados = [
        "password",  # login con correo+password
        "jwt",  # emisión/uso de tokens JWT
        "oauth_google",  # login con Google OAuth
        "2fa",  # autenticación de dos factores 
    ]

    implementados = []

    features = detectar_caracteristicas_autenticacion()

    for mech in especificados:
        if features.get(mech):
            implementados.append(mech)

    A = len(implementados)
    B = len(especificados)
    X = A / B if B > 0 else 0

    print("\nMétrica SAu-1-G: Mecanismos de Autenticación Implementados")
    print("-"*65)
    print("Fórmula: X = A / B")
    print(f"A = {A} mecanismos implementados: {implementados}")
    print(f"B = {B} mecanismos especificados: {especificados}")
    print(f"Resultado: X = {X:.2f}")

    # Umbral recomendado: al menos 75% de los mecanismos especificados implementados
    UMBRAL_SAU_1 = 0.75
    print(f"Umbral recomendado SAu-1-G: {UMBRAL_SAU_1}")
    assert X >= UMBRAL_SAU_1, (
        f"SAu-1-G insuficiente: {A}/{B} mecanismos implementados (X={X:.2f}) < umbral {UMBRAL_SAU_1}"
    )


def test_conformidad_reglas_autenticacion_oauth(test_client):
    """SAu-2-S adaptado a OAuth: evalúa reglas relevantes cuando se usa Google OAuth."""

    features = detectar_caracteristicas_autenticacion()

    aplicables = []
    
    if features.get("password"):
        aplicables.extend([
            "password_policy",      # políticas de contraseña
            "account_lockout",      # bloqueo de cuenta por intentos fallidos
        ])
    
    if features.get("oauth_google") or features.get("jwt"):
        aplicables.extend([
            "token_validation",     # validación de token (aud, issuer, firma)
            "token_revocation",     # revocación de tokens al logout
            "session_security",     # expiración de sesión / cookies / JWT
        ])
    
    if not aplicables:
        aplicables = ["account_lockout"]  # mínimo requerido si no hay otros mecanismos

    implementadas = []

    from inspect import getsource
    try:
        import app.routes.auth as auth_module
        src_auth = getsource(auth_module)
    except Exception:
        src_auth = ""

    try:
        import app.main as main_module
        src_main = getsource(main_module)
    except Exception:
        src_main = ""

    # Detecciones para reglas de password
    if "len(data.get(\"password\")" in src_auth or ("password" in src_auth and "min" in src_auth):
        implementadas.append("password_policy")

    if "failed" in src_auth.lower() or "intentos" in src_auth.lower() or "attempt" in src_auth.lower():
        implementadas.append("account_lockout")

    if "id_token.verify_oauth2_token" in src_auth or "verify_oauth2_token" in src_auth:
        implementadas.append("token_validation")

    if "revoke" in src_main.lower() or "oauth2/revoke" in src_main.lower() or "google.post" in src_main.lower():
        implementadas.append("token_revocation")

    # Session security heurística: JWT config o cookies seguros
    if app.config.get("JWT_SECRET_KEY") or app.config.get("SESSION_COOKIE_SECURE"):
        implementadas.append("session_security")

    A = len(set(implementadas))
    B = len(aplicables)
    X = A / B if B > 0 else 0

    print("\nMétrica SAu-2-S: Conformidad con Reglas de Autenticación")
    print("-"*65)
    print("Fórmula: X = A / B")
    print(f"A = {A} reglas implementadas: {sorted(set(implementadas))}")
    print(f"B = {B} reglas especificadas: {aplicables}")
    print(f"Resultado: X = {X:.2f}")

    UMBRAL_SAU_2 = 0.80
    if B == 0:
        print("No hay reglas aplicables. Test saltado.")
        assert True
    else:
        print(f"Umbral recomendado SAu-2-S: {UMBRAL_SAU_2}")
        assert X >= UMBRAL_SAU_2, (
            f"SAu-2-S insuficiente: {A}/{B} reglas implementadas (X={X:.2f}) < umbral {UMBRAL_SAU_2}"
        )
