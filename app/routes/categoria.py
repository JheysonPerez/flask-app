from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.categoria import Categoria

bp_categoria = Blueprint("bp_categoria", __name__, url_prefix="/categorias")

# Decorador para que solo clientes accedan a ciertas rutas
def cliente_required(func):
    from functools import wraps
    @wraps(func)
    @login_required
    def wrapper(*a, **kw):
        if current_user.rol != "cliente":
            abort(403)  # acceso prohibido si no es cliente
        return func(*a, **kw)
    return wrapper

# Crear nueva categoría (solo cliente)
@bp_categoria.route("/", methods=["POST"])
@cliente_required
def crear_categoria():
    data = request.json
    cat = Categoria(nombre=data["nombre"])
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201

# Editar categoría por id (solo cliente)
@bp_categoria.route("/<int:id>", methods=["PUT"])
@cliente_required
def editar_categoria(id):
    cat = Categoria.query.get_or_404(id)
    cat.nombre = request.json.get("nombre", cat.nombre)
    db.session.commit()
    return jsonify(cat.to_dict())

# Borrar categoría por id (solo cliente)
@bp_categoria.route("/<int:id>", methods=["DELETE"])
@cliente_required
def borrar_categoria(id):
    cat = Categoria.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    return jsonify({'msg': 'Categoría eliminada'})

# Listar todas las categorías (público)
@bp_categoria.route("/", methods=["GET"])
def listar_categorias():
    categorias = Categoria.query.all()
    return jsonify([c.to_dict() for c in categorias])
