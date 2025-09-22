from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from functools import wraps
from flask_mail import Message

from app.extensions import db, mail
from app.models.usuario import Usuario as UsuarioDB

bp_admin = Blueprint("bp_admin", __name__, url_prefix="/admin")

# Middleware personalizado: acceso solo a administradores 
def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.rol != "administrador":
            abort(403)
        return func(*args, **kwargs)
    return wrapper

# Listar todos los clientes
@bp_admin.route("/clientes")
@admin_required
def listar_clientes():
    clientes = UsuarioDB.query.filter_by(rol="cliente").all()
    return render_template("admin_clientes.html", clientes=clientes)

# Crear nuevo cliente (formulario + alta)
@bp_admin.route("/clientes/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo_cliente():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        estado = request.form.get("estado", "activo")
        passwd = request.form.get("password")

        if UsuarioDB.query.filter_by(email=email).first():
            flash("El correo ya existe", "error")
            return redirect(url_for("bp_admin.nuevo_cliente"))

        nuevo = UsuarioDB(nombre=nombre, email=email, rol="cliente", estado=estado)
        if passwd:
            nuevo.password_hash = generate_password_hash(passwd)

        db.session.add(nuevo)
        db.session.commit()

        # ---------- Enviar correo de confirmación ----------
        try:
            msg = Message(
                subject="¡Registro exitoso en la tienda!",
                sender=("Tienda Virtual", current_app.config["MAIL_USERNAME"]),
                recipients=[email],
            )
            msg.html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #2c3e50;">¡Bienvenido/a, {nombre}!</h2>
                <p>Tu cuenta ha sido creada exitosamente en nuestra prestigiosa tienda.</p>

                <p><strong>Correo:</strong> {email}<br>
                <strong>Rol:</strong> {nuevo.rol.capitalize()}</p>

                <p>Gracias por formar parte de nuestra comunidad.</p>
                <p style="margin-top: 30px;">Atentamente,<br><strong>El equipo de Sheriff Store</strong></p>
            </body>
            </html>
            """
            mail.send(msg)
        except Exception as e:
            flash(f"No se pudo enviar el correo: {e}", "error")

        flash("Cliente creado ✅")
        return redirect(url_for("bp_admin.listar_clientes"))

    return render_template("admin_nuevo_cliente.html")

# Ver detalles de un cliente
@bp_admin.route("/clientes/<int:id>")
@admin_required
def detalle_cliente(id):
    cliente = UsuarioDB.query.get_or_404(id)
    return render_template("admin_detalle_cliente.html", cliente=cliente)

# Editar cliente
@bp_admin.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar_cliente(id):
    cliente = UsuarioDB.query.get_or_404(id)

    if request.method == "POST":
        cliente.nombre = request.form["nombre"]
        cliente.email = request.form["email"]
        cliente.estado = request.form.get("estado", cliente.estado)
        db.session.commit()
        flash("Cliente actualizado ✅")
        return redirect(url_for("bp_admin.detalle_cliente", id=id))

    return render_template("admin_editar_cliente.html", cliente=cliente)

# Eliminar cliente
@bp_admin.route("/clientes/<int:id>/borrar", methods=["POST"])
@admin_required
def borrar_cliente(id):
    cliente = UsuarioDB.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash("Cliente eliminado")
    return redirect(url_for("bp_admin.listar_clientes"))

# Cambiar estado (activo/inactivo)
@bp_admin.route("/clientes/<int:id>/estado", methods=["POST"])
@admin_required
def cambiar_estado(id):
    cliente = UsuarioDB.query.get_or_404(id)
    cliente.estado = request.form["estado"]
    db.session.commit()
    flash("Estado actualizado")
    return redirect(url_for("bp_admin.listar_clientes"))
