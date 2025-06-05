import os
from flask import Flask, redirect, url_for, render_template, session, flash
from dotenv import load_dotenv
from app.extensions import db, jwt, mail
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import LoginManager, login_user, logout_user, UserMixin, login_required, current_user
from app.models.usuario import Usuario as UsuarioDB
from app.routes.categoria import bp_categoria

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Clase para manejar usuarios en Flask-Login
class Usuario(UserMixin):
    def __init__(self, id_, nombre, email, rol):
        self.id = id_
        self.nombre = nombre
        self.email = email
        self.rol = rol
        self.google_id = None

login_manager = LoginManager()

# Carga el usuario desde la base de datos para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # Busca usuario en la BD y lo convierte en objeto Usuario para Flask-Login
    usuario_db = UsuarioDB.query.get(int(user_id))
    if not usuario_db:
        return None
    user = Usuario(
        id_=str(usuario_db.id),
        nombre=usuario_db.nombre,
        email=usuario_db.email,
        rol=usuario_db.rol
    )
    user.google_id = usuario_db.google_id
    return user

# Función para crear la aplicación Flask
def create_app():
    app = Flask(__name__)
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

    # Inicializa extensiones
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    # Configura blueprint para autenticación con Google OAuth
    google_bp = make_google_blueprint(
        client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        scope=["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"],
        redirect_to="perfil"  # Redirige a la ruta 'perfil' tras autenticación
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    # Ruta principal para mostrar la página de login
    @app.route('/')
    def index():
        # Renderiza la plantilla 'login.html'
        return render_template('login.html')

    # Ruta para manejar el perfil tras autenticación con Google
    @app.route('/perfil')
    def perfil():
        # Valida autenticación con Google, obtiene datos del usuario y lo loguea
        if not google.authorized:
            return redirect(url_for('google.login'))

        info = google.get("/oauth2/v3/userinfo").json()
        email, nombre, google_id = info["email"], info["name"], info["sub"]
        imagen = info.get("picture")

        usuario_db = UsuarioDB.query.filter_by(email=email).first()

        if not usuario_db:
            return redirect(url_for('index'))  

        # Actualiza google_id si no está registrado
        if not usuario_db.google_id:
            usuario_db.google_id = google_id
            db.session.commit()

        session['imagen_perfil'] = imagen

        user = Usuario(id_=str(usuario_db.id), nombre=nombre, email=email, rol=usuario_db.rol)
        user.google_id = google_id
        login_user(user)

        # Redirige según el rol del usuario
        if usuario_db.rol == 'administrador':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('cliente_dashboard'))

    # Ruta para el dashboard de administradores
    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        # Renderiza 'admin_dashboard.html' con datos del usuario
        return render_template('admin_dashboard.html', nombre=current_user.nombre, rol=current_user.rol)

    # Ruta para el dashboard de clientes
    @app.route('/cliente/dashboard')
    @login_required
    def cliente_dashboard():
        # Renderiza 'cliente_dashboard.html' con datos del usuario
        return render_template('cliente_dashboard.html', nombre=current_user.nombre, rol=current_user.rol)

    # Ruta para mostrar el perfil del usuario
    @app.route('/perfil/usuario')
    @login_required
    def perfil_usuario():
        # Obtiene datos del usuario de la BD y renderiza 'perfil.html'
        usuario_db = UsuarioDB.query.filter_by(email=current_user.email).first()
        if not usuario_db:
            flash("Usuario no encontrado.", "error")
            return redirect(url_for('index'))
        return render_template('perfil.html', usuario=usuario_db, imagen=session.get('imagen_perfil'))

    # Ruta para cerrar sesión
    @app.route('/logout')
    @login_required
    def logout():
        # Cierra sesión, limpia la sesión y redirige a 'index'
        logout_user()
        session.clear()
        return redirect(url_for('index'))

    # Registra blueprints de otras rutas
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


    # Comando CLI para crear la base de datos
    @app.cli.command("create-db")
    def create_db():
        # Crea todas las tablas de la base de datos
        with app.app_context():
            db.create_all()
            print("✅ Base de datos creada correctamente.")

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)