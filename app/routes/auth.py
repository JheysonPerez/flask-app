# app/routes/auth.py
from flask import Blueprint, request, jsonify
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

    # Validar campos obligatorios
    if not data.get("email") or not data.get("password") or not data.get("nombre"):
        return jsonify({"msg": "Faltan datos obligatorios"}), 400

    # Verificar si el email ya existe
    if Usuario.query.filter_by(email=data["email"]).first():
        return jsonify({"msg": "El correo ya está registrado"}), 400

    nuevo_usuario = Usuario(
        nombre=data["nombre"],
        email=data["email"],
        rol=data.get("rol", "cliente")  # rol por defecto
    )
    try:
        nuevo_usuario.set_password(data["password"])
        db.session.add(nuevo_usuario)
        db.session.commit()
        return jsonify({"msg": "Usuario registrado exitosamente"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error al registrar el usuario: {e}"}), 500

# Login con Google OAuth
@auth_bp.route("/login/google", methods=["POST"])
def login_google():
    data = request.get_json(silent=True) or {}
    token_google = data.get("credential")

    if not token_google:
        return jsonify({"msg": "Token de Google no proporcionado"}), 400

    try:
        # Verificar token Google
        id_info = id_token.verify_oauth2_token(token_google, google_requests.Request())
        email = id_info.get("email")

        if not email:
            return jsonify({"msg": "No se pudo obtener el correo electrónico"}), 400

        # Buscar usuario en DB
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            return jsonify({"msg": "Usuario no registrado"}), 401

        # Crear token JWT
        access_token = create_access_token(identity=usuario.id)
        return jsonify({"access_token": access_token, "rol": usuario.rol}), 200

    except ValueError:
        return jsonify({"msg": "Token de Google inválido"}), 401

# Obtener perfil del usuario (protegido)
@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(int(user_id))
    if not usuario:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    return jsonify({
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
    }), 200

# Logout (solo mensaje, el token se maneja en cliente)
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    return jsonify({"msg": "Sesión cerrada. Elimine el token del cliente."}), 200
