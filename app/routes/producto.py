import sys
import os
import logging
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app, session, flash
from werkzeug.utils import secure_filename
from functools import wraps
from flask_login import login_required, current_user

from app.models.producto import Producto
from app.models.categoria import Categoria
from app.extensions import db

producto_bp = Blueprint('producto', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Configura el logger
logger = logging.getLogger("flask_backend")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_active_cliente(func):
    """Decorador para validar que el usuario está activo y es cliente."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        usuario = current_user
        if not usuario or usuario.is_anonymous:
            logger.error(f"[{func.__name__}] Usuario no autenticado")
            return jsonify({'msg': 'Usuario no autenticado'}), 401
        if usuario.estado != "activo":
            logger.warning(f"[{func.__name__}] Usuario {usuario.id} inactivo intentó acceder")
            return jsonify({"msg": "Usuario inactivo"}), 403
        if usuario.rol != 'cliente':
            logger.warning(f"[{func.__name__}] Usuario {usuario.id} con rol {usuario.rol} intentó acceder")
            return jsonify({'msg': 'Solo los clientes pueden realizar esta acción'}), 403
        return func(*args, **kwargs)
    return wrapper


@producto_bp.route('/productos/nuevo', methods=['GET'])
@login_required
@validate_active_cliente
def nuevo_producto():
    categorias = Categoria.query.all()
    logger.info(f"[nuevo_producto] Usuario {current_user.id} accede al formulario con {len(categorias)} categorías")
    return render_template('nuevo_producto.html', categorias=categorias)


@producto_bp.route('/productos', methods=['POST'])
@login_required
@validate_active_cliente
def crear_producto():
    data = request.form
    categoria_nombre = data.get('categoria_nombre', '').strip()
    marca = data.get('marca', '').strip()

    if not all([data.get('nombre'), data.get('precio'), data.get('stock'), categoria_nombre]):
        logger.error("[crear_producto] Datos incompletos en el formulario")
        return jsonify({'msg': 'Todos los campos obligatorios deben completarse'}), 400

    try:
        precio = float(data.get('precio'))
        stock = int(data.get('stock'))
        if precio <= 0 or stock < 0:
            raise ValueError("Precio debe ser positivo y stock no negativo")
    except ValueError as e:
        logger.error(f"[crear_producto] Error en datos numéricos: {e}")
        return jsonify({'msg': 'Precio o stock inválidos'}), 400

    categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()
    if not categoria:
        if len(categoria_nombre) < 3:
            logger.error("[crear_producto] Nombre de categoría inválido")
            return jsonify({'msg': 'El nombre de la categoría debe tener al menos 3 caracteres'}), 400
        categoria = Categoria(nombre=categoria_nombre)
        db.session.add(categoria)
        db.session.commit()
        logger.info(f"[crear_producto] Categoría creada: {categoria_nombre} con ID {categoria.id}")

    file = request.files.get('imagen')
    imagen_nombre = None
    if file and allowed_file(file.filename):
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        if file_length > MAX_FILE_SIZE:
            logger.error("[crear_producto] Archivo excede el tamaño máximo")
            return jsonify({'msg': 'El archivo excede el tamaño máximo de 16MB'}), 400
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.root_path, 'static/uploads')
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        imagen_nombre = filename
        logger.info(f"[crear_producto] Imagen guardada en: {file_path}")

    nuevo_producto = Producto(
        nombre=data['nombre'].strip(),
        descripcion=data.get('descripcion', '').strip(),
        precio=precio,
        stock=stock,
        imagen_url=imagen_nombre or '',
        categoria_id=categoria.id,
        cliente_id=current_user.id,
        marca=marca
    )
    db.session.add(nuevo_producto)
    db.session.commit()
    logger.info(f"[crear_producto] Producto creado con ID: {nuevo_producto.id} por usuario {current_user.id}")
    return redirect(url_for('producto.listar_mis_productos'))


@producto_bp.route('/mis-productos', methods=['GET'])
@login_required
@validate_active_cliente
def listar_mis_productos():
    productos = Producto.query.filter_by(cliente_id=int(current_user.id)).all()
    logger.info(f"[listar_mis_productos] Usuario {current_user.id} tiene {len(productos)} productos")
    return render_template('mis_productos.html', productos=productos)


@producto_bp.route('/productos/<int:producto_id>', methods=['GET'])
@login_required
@validate_active_cliente
def obtener_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)

    if str(producto.cliente_id) != str(current_user.id):
        logger.warning(f"[obtener_producto] Usuario {current_user.id} intentó acceder a producto {producto_id} sin permiso")
        return jsonify({'msg': 'No tienes permiso para ver este producto'}), 403

    logger.info(f"[obtener_producto] Usuario {current_user.id} accede a producto {producto_id}")
    return render_template('detalle_producto.html', producto=producto)


@producto_bp.route('/productos/<int:producto_id>/editar', methods=['GET'])
@login_required
@validate_active_cliente
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if str(producto.cliente_id) != str(current_user.id):
        logger.warning(f"[editar_producto] Usuario {current_user.id} intentó editar producto {producto_id} sin permiso")
        return jsonify({'msg': 'No tienes permiso para editar este producto'}), 403
    categorias = Categoria.query.all()
    logger.info(f"[editar_producto] Usuario {current_user.id} accede al formulario de edición del producto {producto_id}")
    return render_template('editar_producto.html', producto=producto, categorias=categorias)


@producto_bp.route('/productos/<int:producto_id>', methods=['POST'])
@login_required
@validate_active_cliente
def actualizar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if str(producto.cliente_id) != str(current_user.id):
        logger.warning(f"[actualizar_producto] Usuario {current_user.id} intentó actualizar producto {producto_id} sin permiso")
        return jsonify({'msg': 'No tienes permiso para editar este producto'}), 403

    data = request.form
    if not all([data.get('nombre'), data.get('precio'), data.get('stock')]):
        logger.error("[actualizar_producto] Datos incompletos en el formulario")
        return jsonify({'msg': 'Todos los campos obligatorios deben completarse'}), 400

    try:
        precio = float(data.get('precio'))
        stock = int(data.get('stock'))
        if precio <= 0 or stock < 0:
            raise ValueError("Precio debe ser positivo y stock no negativo")
    except ValueError as e:
        logger.error(f"[actualizar_producto] Error en datos numéricos: {e}")
        return jsonify({'msg': 'Precio o stock inválidos'}), 400

    file = request.files.get('imagen')
    if file and allowed_file(file.filename):
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        if file_length > MAX_FILE_SIZE:
            logger.error("[actualizar_producto] Archivo excede el tamaño máximo")
            return jsonify({'msg': 'El archivo excede el tamaño máximo de 16MB'}), 400
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.root_path, 'static/uploads')
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        if producto.imagen_url:
            old_file_path = os.path.join(upload_path, producto.imagen_url)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
                logger.info(f"[actualizar_producto] Imagen antigua eliminada: {old_file_path}")
        producto.imagen_url = filename
        logger.info(f"[actualizar_producto] Imagen actualizada para producto {producto_id}")

    producto.nombre = data.get('nombre', producto.nombre).strip()
    producto.descripcion = data.get('descripcion', producto.descripcion).strip()
    producto.precio = precio
    producto.stock = stock
    categoria_id = data.get('categoria_id')
    if categoria_id:
        producto.categoria_id = int(categoria_id)
    producto.marca = data.get('marca', producto.marca).strip()

    db.session.commit()
    logger.info(f"[actualizar_producto] Producto {producto_id} actualizado por usuario {current_user.id}")
    return redirect(url_for('producto.listar_mis_productos'))


@producto_bp.route('/productos/<int:producto_id>/eliminar', methods=['POST'])
@login_required
@validate_active_cliente
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if str(producto.cliente_id) != str(current_user.id):
        logger.warning(f"[eliminar_producto] Usuario {current_user.id} intentó eliminar producto {producto_id} sin permiso")
        return jsonify({'msg': 'No tienes permiso para eliminar este producto'}), 403

    if producto.imagen_url:
        archivo_path = os.path.join(current_app.root_path, 'static/uploads', producto.imagen_url)
        if os.path.exists(archivo_path):
            try:
                os.remove(archivo_path)
                logger.info(f"[eliminar_producto] Archivo imagen eliminado: {archivo_path}")
            except Exception as e:
                logger.error(f"[eliminar_producto] Error eliminando archivo: {e}")

    db.session.delete(producto)
    db.session.commit()
    logger.info(f"[eliminar_producto] Producto {producto_id} eliminado por usuario {current_user.id}")
    return redirect(url_for('producto.listar_mis_productos'))


@producto_bp.route('/carrito/agregar/<int:producto_id>', methods=['POST'])
@login_required
@validate_active_cliente
def agregar_al_carrito(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    carrito = session.get('carrito', {})
    str_id = str(producto_id)
    carrito[str_id] = carrito.get(str_id, 0) + 1
    session['carrito'] = carrito
    session.modified = True
    flash('Producto añadido al estante virtual.', 'success')
    logger.info(f"[agregar_al_carrito] Usuario {current_user.id} añadió producto {producto_id} al estante virtual. Cantidad: {carrito[str_id]}")
    return redirect(url_for('producto.listar_mis_productos'))


@producto_bp.route('/carrito', methods=['GET'])
@login_required
@validate_active_cliente
def ver_carrito():
    carrito = session.get('carrito', {})
    productos_carrito = []
    total = 0

    for producto_id_str, cantidad in carrito.items():
        producto = Producto.query.get(int(producto_id_str))
        if producto:
            subtotal = producto.precio * cantidad
            total += subtotal
            productos_carrito.append({
                'producto': producto,
                'cantidad': cantidad,
                'subtotal': subtotal
            })

    logger.info(f"[ver_carrito] Usuario {current_user.id} visualiza estante virtual con {len(productos_carrito)} productos y total {total}")
    return render_template('carrito.html', productos_carrito=productos_carrito, total=total)


@producto_bp.route('/carrito/editar/<int:producto_id>', methods=['POST'])
@login_required
@validate_active_cliente
def editar_cantidad_carrito(producto_id):
    carrito = session.get('carrito', {})
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        logger.error(f"[editar_cantidad_carrito] Cantidad inválida para producto {producto_id}")
        return jsonify({'msg': 'Cantidad inválida'}), 400

    str_id = str(producto_id)
    if cantidad < 1:
        carrito.pop(str_id, None)
    else:
        carrito[str_id] = cantidad

    session['carrito'] = carrito
    session.modified = True
    flash('Cantidad actualizada.', 'success')
    logger.info(f"[editar_cantidad_carrito] Usuario {current_user.id} actualizó cantidad producto {producto_id} a {cantidad}")
    return redirect(url_for('producto.ver_carrito'))


@producto_bp.route('/carrito/eliminar/<int:producto_id>', methods=['POST'])
@login_required
@validate_active_cliente
def eliminar_producto_carrito(producto_id):
    carrito = session.get('carrito', {})
    str_id = str(producto_id)
    if str_id in carrito:
        carrito.pop(str_id)
        session['carrito'] = carrito
        session.modified = True
        flash('Producto eliminado del carrito.', 'success')
        logger.info(f"[eliminar_producto_carrito] Usuario {current_user.id} eliminó producto {producto_id} del estante virtual")
    return redirect(url_for('producto.ver_carrito'))


@producto_bp.route('/filtro-productos')
@login_required
@validate_active_cliente
def filtro_productos():
    query = db.session.query(Producto).join(Categoria)

    nombre = request.args.get('nombre', '').strip()
    marca = request.args.get('marca', '').strip()
    categoria_texto = request.args.get('categoria', '').strip()
    precio_min = request.args.get('precio_min', type=float)
    precio_max = request.args.get('precio_max', type=float)
    orden_stock = request.args.get('orden_stock')

    if nombre:
        query = query.filter(Producto.nombre.ilike(f'%{nombre}%'))
    if marca:
        query = query.filter(Producto.marca.ilike(f'%{marca}%'))
    if categoria_texto:
        query = query.filter(Categoria.nombre.ilike(f'%{categoria_texto}%'))
    if precio_min is not None:
        query = query.filter(Producto.precio >= precio_min)
    if precio_max is not None:
        query = query.filter(Producto.precio <= precio_max)

    if orden_stock == 'asc':
        query = query.order_by(Producto.stock.asc())
    elif orden_stock == 'desc':
        query = query.order_by(Producto.stock.desc())

    productos = query.all()
    return render_template('mis_productos.html', productos=productos)



#Prueba con Locust 

@producto_bp.route('/productos', methods=['GET'])
def api_productos_publicos():
    productos = Producto.query.all()
    resultado = [p.to_dict() for p in productos]
    return jsonify(resultado), 200
