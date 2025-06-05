from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models.producto import Producto
from app.models.historial_ventas import HistorialVenta  # Modelo de ventas

bp_cliente = Blueprint("bp_cliente", __name__, url_prefix="/cliente")

# Decorador para restringir rutas solo a clientes
def cliente_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.rol != "cliente":
            abort(403)  # Prohibido si no es cliente
        return func(*args, **kwargs)
    return wrapper

# Crear producto asociado al cliente actual
@bp_cliente.route("/productos", methods=["POST"])
@cliente_required
def crear_producto():
    data = request.get_json()
    prod = Producto(
        cliente_id=current_user.id,
        nombre=data["nombre"],
        descripcion=data.get("descripcion"),
        precio=data["precio"],
        stock=data["stock"],
        imagen_url=data.get("imagen_url"),
        marca=data.get("marca")
    )
    db.session.add(prod)
    db.session.commit()
    return jsonify({"msg": "Producto creado", "id": prod.id}), 201

# Listar productos del cliente
@bp_cliente.route("/productos", methods=["GET"])
@cliente_required
def mis_productos():
    productos = Producto.query.filter_by(cliente_id=current_user.id).all()
    return jsonify([p.to_dict() for p in productos]), 200

# Actualizar producto (solo si pertenece al cliente)
@bp_cliente.route("/productos/<int:id>", methods=["PUT"])
@cliente_required
def actualizar_producto(id):
    prod = Producto.query.get_or_404(id)
    if prod.cliente_id != current_user.id:
        abort(403)  # No puede modificar productos de otros
    data = request.get_json()
    prod.nombre      = data.get("nombre", prod.nombre)
    prod.descripcion = data.get("descripcion", prod.descripcion)
    prod.precio      = data.get("precio", prod.precio)
    prod.stock       = data.get("stock", prod.stock)
    prod.imagen_url  = data.get("imagen_url", prod.imagen_url)
    prod.marca       = data.get("marca", prod.marca)
    db.session.commit()
    return jsonify({"msg": "Producto actualizado"}), 200

# Eliminar producto (solo si pertenece al cliente)
@bp_cliente.route("/productos/<int:id>", methods=["DELETE"])
@cliente_required
def borrar_producto(id):
    prod = Producto.query.get_or_404(id)
    if prod.cliente_id != current_user.id:
        abort(403)  # No puede borrar productos de otros
    db.session.delete(prod)
    db.session.commit()
    return jsonify({"msg": "Producto eliminado"}), 200

# Mostrar historial de ventas del cliente
@bp_cliente.route("/ventas", methods=["GET"])
@cliente_required
def mi_historial_ventas():
    ventas = HistorialVenta.query.filter_by(cliente_id=current_user.id).all()
    return jsonify([{
        "id": v.id,
        "producto_id": v.producto_id,
        "cantidad": v.cantidad,
        "total_venta": v.total_venta,
        "fecha": v.fecha_venta.isoformat()
    } for v in ventas]), 200
