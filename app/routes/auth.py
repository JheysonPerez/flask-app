# app/routes/auth.py
import os
from flask import Blueprint, request, jsonify
from flask_login import login_user
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.models.usuario import Usuario
from app.extensions import db

auth_bp = Blueprint("auth", __name__)

# Registro de usuario
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data.get("email") or not data.get("password") or not data.get("nombre"):
        return jsonify({"msg": "Faltan datos obligatorios"}), 400

    if Usuario.query.filter_by(email=data["email"]).first():
        return jsonify({"msg": "El correo ya está registrado"}), 400

    nuevo_usuario = Usuario(
        nombre=data["nombre"],
        email=data["email"],
        rol=data.get("rol", "cliente")
    )
    try:
        nuevo_usuario.set_password(data["password"])
        db.session.add(nuevo_usuario)
        db.session.commit()
        return jsonify({"msg": "Usuario registrado exitosamente"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error al registrar el usuario: {e}"}), 500

# Login con Google OAuth (bypass por email solo en entorno de prueba)
@auth_bp.route("/login/google", methods=["POST"])
def login_google():
    data = request.get_json(silent=True) or {}

    # Bypass para pruebas de carga (si se manda el email directamente)
    if "email" in data and os.getenv("FLASK_ENV") in {"development", "testing"}:
        usuario = Usuario.query.filter_by(email=data["email"]).first()
        if not usuario:
            return jsonify({"msg": "Usuario no registrado"}), 401
        login_user(usuario)
        access_token = create_access_token(identity=usuario.id)
        return jsonify({"access_token": access_token, "rol": usuario.rol}), 200

    token_google = data.get("credential")
    if not token_google:
        return jsonify({"msg": "Token de Google no proporcionado"}), 400

    try:
        id_info = id_token.verify_oauth2_token(token_google, google_requests.Request())
        email = id_info.get("email")

        if not email:
            return jsonify({"msg": "No se pudo obtener el correo electrónico"}), 400

        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            return jsonify({"msg": "Usuario no registrado"}), 401

        login_user(usuario)
        access_token = create_access_token(identity=usuario.id)
        return jsonify({"access_token": access_token, "rol": usuario.rol}), 200

    except ValueError:
        return jsonify({"msg": "Token de Google inválido"}), 401

# Perfil protegido
@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    usuario = db.session.get(Usuario, int(user_id))
    if not usuario:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    return jsonify({
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
    }), 200

# Logout
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    return jsonify({"msg": "Sesión cerrada. Elimine el token del cliente."}), 200

# Login tradicional
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data.get("email") or not data.get("password"):
        return jsonify({"msg": "Faltan datos obligatorios"}), 400

    usuario = Usuario.query.filter_by(email=data["email"]).first()
    if not usuario or not usuario.check_password(data["password"]):
        return jsonify({"msg": "Credenciales inválidas"}), 401

    login_user(usuario)
    access_token = create_access_token(identity=usuario.id)
    return jsonify({"access_token": access_token, "rol": usuario.rol}), 200
