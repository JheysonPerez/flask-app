import os
from flask import Flask, redirect, url_for, render_template, session, flash
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google

from app.extensions import db, jwt, mail
from app.models.usuario import Usuario
from app.routes.categoria import bp_categoria

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = "index"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

def create_app(testing=False):
    app = Flask(__name__)

    # Configuración básica
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

    # Configuración de cookies para producción
    if os.getenv("FLASK_ENV") == "production":
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Inicializar extensiones
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    # Configuración Google OAuth
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

    # Rutas
    @app.route('/')
    def index():
        return render_template('login.html')

    @app.route('/perfil')
    @login_required
    def perfil():
        if not testing:
            if not google.authorized or 'google_oauth_token' not in session:
                return redirect(url_for("google.login"))

            try:
                resp = google.get("/oauth2/v3/userinfo")
                resp.raise_for_status()
                info = resp.json()

                email = info.get("email")
                nombre = info.get("name")
                google_id = info.get("sub")
                imagen = info.get("picture")

                # Guardar token en sesión
                session['google_oauth_token'] = google.token

                usuario_db = Usuario.query.filter_by(email=email).first()
                if not usuario_db:
                    flash("Usuario no registrado.", "error")
                    return redirect(url_for('index'))

                if not usuario_db.google_id:
                    usuario_db.google_id = google_id
                    db.session.commit()

                session['imagen_perfil'] = imagen
                login_user(usuario_db)

                if usuario_db.rol == 'administrador':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('cliente_dashboard'))

            except Exception as e:
                flash("Error al autenticar con Google: " + str(e), "error")
                return redirect(url_for('index'))
        else:
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

# Ejecutar app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
