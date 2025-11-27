import json
from datetime import datetime
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
    """Procesa la compra: valida, crea la compra, actualiza stock, crea historial y devuelve resultado."""
    
    # DEBUG COMPLETO - Todo lo que llega al hacer la compra
    print("\n" + "="*80)
    print("COMPRA INICIADA - DEBUG COMPLETO")
    print(f"Usuario: {current_user.id} ({current_user.email})")
    print(f"Datos del formulario: {dict(request.form)}")
    print(f"Carrito en sesión (session['carrito']): {session.get('carrito')}")
    print(f"Tipo de dato en sesión: {type(session.get('carrito'))}")
    print("-"*80)

    try:
        cliente_id = current_user.id
        tipo_nombre = (request.form.get("tipo_comprobante") or "").lower().strip()
        ruc = request.form.get("ruc", "").strip()
        dni = request.form.get("dni", "").strip()
        email_destino = request.form.get("email_destino") or current_user.email

        print(f"Tipo comprobante seleccionado: {tipo_nombre}")
        print(f"RUC: {ruc} | DNI: {dni} | Email: {email_destino}")

        # Validaciones
        if tipo_nombre not in ["boleta", "factura"]:
            return jsonify({"msg": "Tipo de comprobante inválido"}), 400

        if tipo_nombre == "factura" and (not ruc or len(ruc) != 11 or not ruc.isdigit()):
            return jsonify({"msg": "RUC inválido (11 dígitos numéricos)"}), 400

        if tipo_nombre == "boleta" and (not dni or len(dni) != 8 or not dni.isdigit()):
            return jsonify({"msg": "DNI inválido (8 dígitos numéricos)"}), 400

        tipo_comprobante_obj = TipoComprobante.query.filter_by(nombre=tipo_nombre).first()
        if not tipo_comprobante_obj:
            return jsonify({"msg": f'Tipo comprobante "{tipo_nombre}" no existe'}), 400
        tipo_comprobante_id = tipo_comprobante_obj.id

        if getattr(current_user, "estado", "activo") != "activo":
            return jsonify({"msg": "Usuario inactivo"}), 403

        # Obtener carrito de sesión
        items = session.get("carrito", [])
        if isinstance(items, str):
            try:
                items = json.loads(items)
                print(f"Carrito convertido desde string JSON → {len(items)} items")
            except json.JSONDecodeError as e:
                print("ERROR al parsear JSON del carrito:", str(e))
                return jsonify({"msg": "Formato del estante virtual inválido", "error": str(e)}), 400
        elif isinstance(items, dict):
            items = [items]
            print("Carrito era un dict → convertido a lista de 1 item")

        print(f"Total de items detectados en el carrito: {len(items) if items else 0}")

        if not items or not isinstance(items, list):
            return jsonify({"msg": "El estante virtual está vacío o tiene formato inválido"}), 400

        converted_items = []
        total = 0.0
        items_detalle = []  # para mostrar en el JSON final

        for idx, item in enumerate(items):
            print(f"Procesando item {idx + 1}: {item}")

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
                return jsonify({"msg": f"Stock insuficiente para producto {prod.nombre}"}), 400

            subtotal = float(prod.precio) * cantidad
            total += subtotal

            converted_items.append({"producto_id": producto_id, "cantidad": cantidad, "producto": prod})
            items_detalle.append({
                "nombre": prod.nombre,
                "precio_unitario": float(prod.precio),
                "cantidad": cantidad,
                "subtotal": subtotal
            })

            print(f"→ {prod.nombre} x{cantidad} = S/ {subtotal:.2f}")

        print(f"TOTAL CALCULADO: S/ {total:.2f}")

        # Crear compra
        compra = Compra(
            cliente_id=cliente_id,
            tipo_comprobante_id=tipo_comprobante_id,
            ruc=ruc if tipo_nombre == "factura" else None,
            total=total,
            email_destino=email_destino,
            dni=dni if tipo_nombre == "boleta" else None
        )
        db.session.add(compra)
        db.session.flush()

        print(f"Compra creada con ID: {compra.id}")

        # Guardar detalle y historial
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
                total_venta=float(prod.precio) * item["cantidad"],
                tipo_comprobante_id=tipo_comprobante_id
            )
            db.session.add(historial)

        session.pop("carrito", None)
        db.session.commit()

        print(f"COMPRA CONFIRMADA CORRECTAMENTE → ID: {compra.id} | Total: S/ {total:.2f}")

        # JSON FINAL CON TODOS LOS DATOS QUE QUERÍAS VER
        return jsonify({
            "msg": "COMPRA CONFIRMADA CORRECTAMENTE",
            "success": True,
            "compra_id": compra.id,
            "cliente_id": cliente_id,
            "tipo_comprobante": tipo_nombre,
            "total": round(total, 2),
            "email_enviado_a": email_destino,
            "cantidad_productos": len(converted_items),
            "productos": items_detalle,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200

    except Exception as e:
        db.session.rollback()
        print("ERROR EN COMPRA:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({
            "msg": "Error procesando la compra",
            "error": str(e),
            "success": False
        }), 500

@compra_bp.route("/compra/<int:id>/pdf")
@login_required
def compra_pdf(id):
    compra = Compra.query.get_or_404(id)
    plantilla = 'factura_pdf.html' if compra.tipo_comprobante and compra.tipo_comprobante.nombre.lower() == 'factura' else 'boleta_pdf.html'
    html = render_template(plantilla, compra=compra)
    pdf = HTML(string=html, base_url=url_for('static', filename='', _external=True)).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={plantilla.replace("_pdf.html", "")}_{id}.pdf'
    return response


@compra_bp.route("/detalle/<int:compra_id>")
@login_required
def detalle_compra(compra_id):
    compra = Compra.query.get_or_404(compra_id)
    productos = compra.productos  # Usar relación directa

    # Asegurar fecha correcta
    if isinstance(compra.fecha, str):
        try:
            compra.fecha = datetime.fromisoformat(compra.fecha)
        except Exception:
            compra.fecha = None

    plantilla = "facturas.html" if compra.tipo_comprobante and compra.tipo_comprobante.nombre.lower() == "factura" else "boletas.html"
    return render_template(plantilla, compra=compra, productos=productos)

