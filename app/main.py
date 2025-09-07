import os
from flask import Flask, redirect, url_for, render_template, session, flash
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google

from app.extensions import db, jwt, mail
from app.models.usuario import Usuario
from app.routes.categoria import bp_categoria

# Cargar variables de entorno
load_dotenv()

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

def create_app(testing=False):
    app = Flask(__name__)

    # Configuración general
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

    # Inicializar extensiones
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    # Configuración de Google OAuth
    if not testing:
        # Solo permitir transporte inseguro en desarrollo local
        if os.getenv("FLASK_ENV") == "development":
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

        # Definir redirect_uri según entorno
        redirect_uri = "/login/google/authorized"
        if os.getenv("FLASK_ENV") == "production":
            redirect_uri = "https://flask-app-1-tmtb.onrender.com/login/google/authorized"

        # Crear blueprint de Google OAuth
        google_bp = make_google_blueprint(
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            scope=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email"
            ],
            redirect_url=redirect_uri
        )
        app.register_blueprint(google_bp, url_prefix="/login")

    # Rutas principales
    @app.route('/')
    def index():
        return render_template('login.html')

    @app.route('/perfil')
    def perfil():
        if testing:
            # En testing, solo redirige al index
            return redirect(url_for('index'))

        # Evitar bucle infinito: verificar si ya estamos autorizados
        if not google.authorized:
            return redirect(url_for('google.login'))

        # Obtener información del usuario desde Google
        resp = google.get("/oauth2/v3/userinfo")
        if not resp.ok:
            flash("Error al obtener información de Google.", "error")
            return redirect(url_for('index'))

        info = resp.json()
        email = info.get("email")
        nombre = info.get("name")
        google_id = info.get("sub")
        imagen = info.get("picture")

        # Buscar usuario en base de datos
        usuario_db = Usuario.query.filter_by(email=email).first()
        if not usuario_db:
            flash("Usuario no registrado.", "error")
            return redirect(url_for('index'))

        # Guardar Google ID si aún no existe
        if not usuario_db.google_id:
            usuario_db.google_id = google_id
            db.session.commit()

        # Guardar información de sesión y loguear
        session['imagen_perfil'] = imagen
        login_user(usuario_db)

        # Redirigir según rol
        if usuario_db.rol == 'administrador':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('cliente_dashboard'))

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
        logout_user()
        session.clear()
        return redirect(url_for('index'))

    # Registrar blueprints
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

# Ejecutar
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
