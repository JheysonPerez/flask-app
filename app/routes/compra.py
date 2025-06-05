import json
import os
import pika
from flask import Blueprint, request, jsonify, session, render_template, url_for, make_response
from flask_login import login_required, current_user
from weasyprint import HTML
from app.extensions import db
from app.models.compra import Compra
from app.models.compra_producto import CompraProducto
from app.models.historial_ventas import HistorialVenta
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.models.tipo_comprobante import TipoComprobante


compra_bp = Blueprint("compra", __name__)

@compra_bp.route("/comprar", methods=["POST"])
@login_required
def comprar():
    print("---- Inicio de compra ----")
    try:
        if not current_user.is_authenticated:
            return jsonify({"msg": "No hay usuario autenticado"}), 401

        cliente_id = current_user.id
        tipo_nombre = request.form.get("tipo_comprobante")
        ruc = request.form.get("ruc", "")  # Siempre obtener, default ""
        nombre_completo = request.form.get("nombre_completo", "")

        if tipo_nombre not in ["boleta", "factura"]:
            return jsonify({"msg": "Tipo de comprobante inválido"}), 400

        if tipo_nombre == "factura":
            if not ruc or len(ruc) != 11 or not ruc.isdigit():
                return jsonify({"msg": "RUC inválido (11 dígitos numéricos)"}), 400

        tipo_comprobante_obj = TipoComprobante.query.filter_by(nombre=tipo_nombre).first()
        if not tipo_comprobante_obj:
            return jsonify({"msg": f'Tipo comprobante "{tipo_nombre}" no existe'}), 400
        tipo_comprobante_id = tipo_comprobante_obj.id

        usuario = Usuario.query.get(cliente_id)
        if not usuario:
            return jsonify({"msg": "Usuario no encontrado"}), 404
        if usuario.estado != "activo":
            return jsonify({"msg": "Usuario inactivo"}), 403

        items = session.get("carrito", [])
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except json.JSONDecodeError as e:
                return jsonify({"msg": "Formato del estante virtual inválido", "error": str(e)}), 400
        elif isinstance(items, dict):
            items = [items]

        if not items or not isinstance(items, list):
            return jsonify({"msg": "El cestante virtual está vacío o tiene formato inválido"}), 400

        converted_items = []
        total = 0

        for item in items:
            if not isinstance(item, dict):
                return jsonify({"msg": "Item inválido", "item": str(item)}), 400

            if "producto_id" not in item or "cantidad" not in item:
                try:
                    pid, cantidad = next(iter(item.items()))
                    item = {"producto_id": pid, "cantidad": cantidad}
                except Exception:
                    return jsonify({"msg": "Estructura de item inválida"}), 400

            try:
                producto_id = int(item["producto_id"])
                cantidad = int(item["cantidad"])
            except (ValueError, TypeError):
                return jsonify({"msg": "producto_id o cantidad no numéricos"}), 400

            prod = Producto.query.get(producto_id)
            if not prod:
                return jsonify({"msg": f"Producto {producto_id} no existe"}), 400

            if prod.stock < cantidad:
                return jsonify({"msg": f"Stock insuficiente para producto {producto_id}"}), 400

            total += prod.precio * cantidad

            converted_items.append({
                "producto_id": producto_id,
                "cantidad": cantidad,
                "producto": prod
            })

        email_destino = request.form.get("email_destino") or usuario.email

        compra = Compra(
            cliente_id=cliente_id,
            tipo_comprobante_id=tipo_comprobante_id,
            ruc=ruc,
            total=total,
            email_destino=email_destino,
            nombre_apellidos=nombre_completo if tipo_nombre == "boleta" else None
            
        )
        db.session.add(compra)
        db.session.flush()  # Para obtener compra.id sin commit

        productos_detalle = []

        for item in converted_items:
            prod = item["producto"]
            prod.stock -= item["cantidad"]

            compra_producto = CompraProducto(
                compra_id=compra.id,
                producto_id=prod.id,
                cantidad=item["cantidad"]
            )
            db.session.add(compra_producto)

            historial = HistorialVenta(
                cliente_id=cliente_id,
                producto_id=prod.id,
                cantidad=item["cantidad"],
                total_venta=prod.precio * item["cantidad"],
                tipo_comprobante_id=tipo_comprobante_id
            )
            db.session.add(historial)

            productos_detalle.append({
                "cantidad": item["cantidad"],
                "marca": prod.marca,
                "nombre": prod.nombre,
                "precio_unitario": prod.precio,
                "producto_id": prod.id,
                "subtotal": prod.precio * item["cantidad"]
            })

        session.pop("carrito", None)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Error procesando la compra: {e}")
        return jsonify({"msg": "Error procesando la compra", "error": str(e)}), 500

    msg = {
        "compra_id": compra.id,
        "tipo_comprobante": tipo_nombre,
        "email_destino": email_destino,
    }

    if tipo_nombre == "factura":
        msg["ruc"] = ruc

    if tipo_nombre == "boleta":
        msg["nombre_apellidos"] = nombre_completo

    msg["productos"] = productos_detalle
    msg["total"] = total


    try:
        rabbit_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rabbit_host,
                port=5672,
                credentials=pika.PlainCredentials("guest", "guest")
            )
        )
        channel = connection.channel()

        queue_name = "cola_boletas" if tipo_nombre == "boleta" else "cola_facturas"
        channel.queue_declare(queue=queue_name, durable=True)

        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(msg),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()

    except Exception as e:
        print(f"[PUBLISH] Error enviando a RabbitMQ: {e}")
        return jsonify({
            "msg": "Compra guardada, pero falló envío a cola RabbitMQ",
            **msg,
            "error": str(e)
        }), 202

    return jsonify({
        "msg": "Compra confirmada correctamente",
        **msg
    }), 201

@compra_bp.route("/compras/<int:compra_id>", methods=["GET"])
@login_required
def detalle_compra(compra_id):
    compra = Compra.query.get_or_404(compra_id)

    if compra.tipo_comprobante.nombre == "boleta":
        return render_template("boletas.html", compra=compra)

    elif compra.tipo_comprobante.nombre == "factura":
        return render_template("facturas.html", compra=compra)

    else:
        return "Tipo de comprobante no soportado", 400


@compra_bp.route('/compra/<int:id>/pdf')
@login_required
def compra_pdf(id):
    compra = Compra.query.get_or_404(id)

    # Elegir plantilla según tipo de comprobante
    if compra.tipo_comprobante and compra.tipo_comprobante.nombre.lower() == 'factura':
        plantilla = 'factura_pdf.html'
    else:
        plantilla = 'boleta_pdf.html'

    # Renderizar la plantilla correspondiente
    html = render_template(plantilla, compra=compra)

    # Generar PDF
    pdf = HTML(string=html, base_url=url_for('static', filename='', _external=True)).write_pdf()

    # Crear respuesta PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={plantilla.replace("_pdf.html", "")}_{id}.pdf'

    return response