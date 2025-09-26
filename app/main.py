import os
import logging
from flask import Flask, redirect, url_for, render_template, session, flash, make_response
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from sqlalchemy.sql import text
from app.extensions import db, jwt, mail
from app.models.usuario import Usuario
from app.routes.categoria import bp_categoria
from sqlalchemy.exc import OperationalError
from flask_dance.consumer import oauth_authorized, oauth_before_login

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = "index"

@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(Usuario, int(user_id))
    if user:
        logger.debug(f"Usuario cargado: id={user_id}, email={user.email}, rol={user.rol}, google_id={user.google_id}")
    else:
        logger.error(f"No se pudo cargar usuario con id={user_id}")
    return user

def create_app(testing=False):
    app = Flask(__name__)
    app.logger.setLevel(logging.DEBUG)

    if testing:
        app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///test.db?check_same_thread=False",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=True,
            SECRET_KEY="clave_test"
        )
    else:
        app.config.update(
            SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db/tienda'),
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY', 'supersecretkey'),
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            SECRET_KEY=os.getenv('FLASK_SECRET_KEY', 'clave_de_desarrollo')
        )

    if os.getenv("FLASK_ENV") == "production":
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'None'
        app.config['SESSION_COOKIE_HTTPONLY'] = True

    try:
        db.init_app(app)
        with app.app_context():
            db.session.execute(text("SELECT 1"))
            logger.debug("Conexión a la base de datos exitosa")
    except OperationalError as e:
        logger.error(f"Error al conectar con la base de datos: {str(e)}")
        raise

    jwt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    if not testing:
        if os.getenv("FLASK_ENV") == "development":
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

        google_bp = make_google_blueprint(
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            scope=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email"
            ],
            redirect_to="perfil",
            offline=True
        )
        app.register_blueprint(google_bp, url_prefix="/login")

        @oauth_before_login.connect_via(google_bp)
        def google_before_login(blueprint, url):
            logger.debug(f"URL de autorización antes: {url}")
            if 'prompt=' not in url:
                url += '&prompt=select_account'
            logger.debug(f"URL de autorización modificada: {url}")
            return url

    @app.route('/')
    def index():
        logger.debug("Accediendo a /index, renderizando login.html")
        if current_user.is_authenticated:
            logger.debug(f"Usuario autenticado en /index, cerrando sesión: {current_user.email}")
            logout_user()
            session.clear()
        response = make_response(render_template('login.html'))
        response.set_cookie('session', '', expires=0)
        return response

    @app.route('/login/google')
    def google_login():
        if not google.authorized:
            logger.debug("Iniciando login con Google, forzando selección de cuenta")
            return redirect(url_for("google.login"))
        logger.debug("Usuario ya autorizado, redirigiendo a /perfil")
        return redirect(url_for('perfil'))

    @oauth_authorized.connect_via(google_bp)
    def google_authorized(blueprint, token):
        logger.debug(f"Token recibido de Google: {token}")
        if token:
            session['google_oauth_token'] = token
            logger.debug("Token guardado en la sesión")
        else:
            logger.error("No se recibió token de Google")
        return False

    @app.route('/perfil')
    def perfil():
        logger.debug(f"Contenido de la sesión en /perfil: {dict(session)}")
        if not google.authorized or 'google_oauth_token' not in session:
            logger.debug("No hay token de Google, redirigiendo a google.login")
            return redirect(url_for("google_login"))

        try:
            logger.debug("Obteniendo información de usuario desde Google")
            resp = google.get("/oauth2/v3/userinfo")
            resp.raise_for_status()
            info = resp.json()

            email = info.get("email")
            google_id = info.get("sub")
            imagen = info.get("picture")
            nombre = info.get("name", "Usuario")

            logger.debug(f"Usuario de Google: email={email}, google_id={google_id}")

            usuario_db = Usuario.query.filter_by(email=email).first()
            if not usuario_db:
                # Crear usuario automáticamente
                usuario_db = Usuario(
                    nombre=nombre,
                    email=email,
                    google_id=google_id,
                    rol="cliente"
                )
                db.session.add(usuario_db)
                db.session.commit()
                logger.debug(f"Usuario creado automáticamente: {email}")

            if usuario_db.google_id != google_id:
                usuario_db.google_id = google_id
                db.session.commit()

            login_user(usuario_db, remember=True)
            session['imagen_perfil'] = imagen
            session.modified = True

            if usuario_db.rol.strip().lower() == 'administrador':
                return redirect(url_for('admin_dashboard'))
            elif usuario_db.rol.strip().lower() == 'cliente':
                return redirect(url_for('cliente_dashboard'))
            else:
                flash("Rol de usuario inválido.", "error")
                return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"Error al autenticar con Google: {str(e)}")
            flash(f"Error al autenticar con Google: {str(e)}", "error")
            return redirect(url_for('index'))

    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        return render_template('admin_dashboard.html', nombre=current_user.nombre, rol=current_user.rol)

    @app.route('/cliente/dashboard')
    @login_required
    def cliente_dashboard():
        return render_template('cliente_dashboard.html', nombre=current_user.nombre, rol=current_user.rol)

    @app.route('/perfil/usuario')
    @login_required
    def perfil_usuario():
        usuario_db = Usuario.query.filter_by(email=current_user.email).first()
        if not usuario_db:
            flash("Usuario no encontrado.", "error")
            return redirect(url_for('index'))
        return render_template('perfil.html', usuario=usuario_db, imagen=session.get('imagen_perfil'))

    @app.route('/logout')
    @login_required
    def logout():
        if 'google_oauth_token' in session:
            token = session.get('google_oauth_token').get('access_token')
            if token:
                try:
                    google.post(
                        "https://accounts.google.com/o/oauth2/revoke",
                        params={"token": token},
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                except Exception as e:
                    logger.error(f"Error al revocar token de Google: {str(e)}")
        logout_user()
        session.clear()
        response = make_response(redirect(url_for('index')))
        response.set_cookie('session', '', expires=0)
        return response

    from app.routes.admin import bp_admin
    from app.routes.cliente import bp_cliente
    from app.routes.auth import auth_bp
    from app.routes.compra import compra_bp
    from app.routes.producto import producto_bp
    from app.routes.historial_ventas import historial_ventas_bp, dashboard_ventas_bp

    app.register_blueprint(bp_admin)
    app.register_blueprint(bp_cliente)
    app.register_blueprint(bp_categoria)
    app.register_blueprint(historial_ventas_bp)
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(compra_bp, url_prefix='/api')
    app.register_blueprint(producto_bp, url_prefix='/api')
    app.register_blueprint(dashboard_ventas_bp)

    @app.cli.command("create-db")
    def create_db():
        with app.app_context():
            db.create_all()
            print("✅ Base de datos creada correctamente.")

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
