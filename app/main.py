import os
import logging
from flask import Flask, redirect, url_for, render_template, session, flash, make_response
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from sqlalchemy.sql import text
from sqlalchemy.exc import OperationalError
from flask_dance.consumer import oauth_authorized
from sqlalchemy import create_engine
import urllib.parse

from app.extensions import db, jwt, mail
from app.models.usuario import Usuario
from app.routes.categoria import bp_categoria

# ----------------------------------------------------
# LOGGING
# ----------------------------------------------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = "index"


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(Usuario, int(user_id))
    if user:
        logger.debug(f"Usuario cargado: id={user_id}, email={user.email}, rol={user.rol}")
    else:
        logger.error(f"No se pudo cargar usuario con id={user_id}")
    return user


# ----------------------------------------------------
# APP FACTORY
# ----------------------------------------------------
def create_app(testing=False):
    app = Flask(__name__)
    app.logger.setLevel(logging.DEBUG)

    # Permitir HTTP en desarrollo
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # ----------------------------------------------------
    # CONFIGURACIÓN BASE DE DATOS
    # ----------------------------------------------------
    if testing:
        app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///test.db?check_same_thread=False",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=True,
            SECRET_KEY="clave_test",
        )
    else:
        odbc_conn = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=JHEYSON\\SQLEXPRESS;"
            "DATABASE=flaskdb;"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )
        odbc_encoded = urllib.parse.quote_plus(odbc_conn)
        database_url = f"mssql+pyodbc:///?odbc_connect={odbc_encoded}"

        app.config.update(
            SQLALCHEMY_DATABASE_URI=database_url,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "supersecretkey"),
            MAIL_SERVER="smtp.gmail.com",
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
            MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
            SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "clave_de_desarrollo"),
        )

    # ----------------------------------------------------
    # PROBAR CONEXIÓN SQL SERVER
    # ----------------------------------------------------
    try:
        db.init_app(app)
        with app.app_context():
            engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
            conn = engine.connect()
            conn.execute(text("SELECT 1"))
            conn.close()
            logger.debug("Conexión a SQL Server exitosa")
    except OperationalError as e:
        logger.error(f"Error al conectar a SQL Server: {str(e)}")
        raise

    # ----------------------------------------------------
    # INICIALIZAR EXTENSIONES
    # ----------------------------------------------------
    jwt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    # ----------------------------------------------------
    # GOOGLE OAUTH → REDIRIGE AL DASHBOARD CORRECTO
    # ----------------------------------------------------
    if not testing:
        google_bp = make_google_blueprint(
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            scope=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email"
            ],
            redirect_to="redirect_after_login",   # ← Aquí va directo al dashboard correcto
            offline=True,
        )
        app.register_blueprint(google_bp, url_prefix="/login")

    # ----------------------------------------------------
    # RUTAS PRINCIPALES
    # ----------------------------------------------------
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            logout_user()
            session.clear()
        response = make_response(render_template("login.html"))
        response.set_cookie("session", "", expires=0)
        return response

    @app.route("/login/google")
    def google_login():
        return redirect(url_for("google.login"))

    @oauth_authorized.connect_via(google_bp)
    def google_logged_in(blueprint, token):
        if not token:
            flash("Error al autenticar con Google", "error")
            return False

        resp = blueprint.session.get("/oauth2/v3/userinfo")
        if not resp.ok:
            flash("Error al obtener datos del usuario", "error")
            return False

        info = resp.json()
        email = info["email"]
        google_id = info["sub"]
        nombre = info.get("name", email.split("@")[0])
        imagen = info.get("picture")

        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            usuario = Usuario(nombre=nombre, email=email, google_id=google_id, rol="cliente")
            db.session.add(usuario)
            db.session.commit()

        if usuario.google_id != google_id:
            usuario.google_id = google_id
            db.session.commit()

        login_user(usuario, remember=True)
        session["imagen_perfil"] = imagen
        return False

    # ----------------------------------------------------
    # REDIRECCIÓN INTELIGENTE DESPUÉS DEL LOGIN
    # ----------------------------------------------------
    @app.route("/redirect-after-login")
    @login_required
    def redirect_after_login():
        if current_user.rol == "administrador":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("cliente_dashboard"))

    # ----------------------------------------------------
    # RUTA PERFIL (solo cuando el usuario haga clic)
    # ----------------------------------------------------
    @app.route("/perfil")
    @login_required
    def perfil():
        return render_template(
            "perfil.html",
            usuario=current_user,
            imagen=session.get("imagen_perfil") or url_for('static', filename='default-profile.png')
        )

    # ----------------------------------------------------
    # DASHBOARDS
    # ----------------------------------------------------
    @app.route("/admin/dashboard")
    @login_required
    def admin_dashboard():
        if current_user.rol != "administrador":
            return redirect(url_for("cliente_dashboard"))
        return render_template("admin_dashboard.html", nombre=current_user.nombre, rol=current_user.rol)

    @app.route("/cliente/dashboard")
    @login_required
    def cliente_dashboard():
        return render_template("cliente_dashboard.html", nombre=current_user.nombre, rol=current_user.rol)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        session.clear()
        response = make_response(redirect(url_for("index")))
        response.set_cookie("session", "", expires=0)
        return response

    # ----------------------------------------------------
    # REGISTRO DE BLUEPRINTS
    # ----------------------------------------------------
    from app.routes.admin import bp_admin
    from app.routes.cliente import bp_cliente
    from app.routes.auth import auth_bp
    from app.routes.compra import compra_bp
    from app.routes.producto import producto_bp
    from app.routes.historial_ventas import historial_ventas_bp, dashboard_ventas_bp

    app.register_blueprint(bp_admin)
    app.register_blueprint(bp_cliente)
    app.register_blueprint(bp_categoria)
    app.register_blueprint(historial_ventas_bp, url_prefix="/cliente")
    app.register_blueprint(dashboard_ventas_bp, url_prefix="/cliente")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(compra_bp, url_prefix="/api")
    app.register_blueprint(producto_bp, url_prefix="/api")

    @app.cli.command("create-db")
    def create_db():
        with app.app_context():
            db.create_all()
            print("Base de datos creada correctamente.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)