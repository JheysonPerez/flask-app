import os
import logging
import uuid
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app, session, flash
from werkzeug.utils import secure_filename
from functools import wraps
from flask_login import login_required, current_user

from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.marca import Marca
from app.extensions import db

producto_bp = Blueprint('producto', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Logger
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
    """Valida que el usuario esté activo y sea cliente."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        usuario = current_user
        if not usuario or usuario.is_anonymous:
            logger.error(f"[{func.__name__}] Usuario no autenticado")
            return jsonify({'msg': 'Usuario no autenticado'}), 401
        if usuario.estado != "activo":
            logger.warning(f"[{func.__name__}] Usuario {usuario.id} inactivo")
            return jsonify({"msg": "Usuario inactivo"}), 403
        if usuario.rol != 'cliente':
            logger.warning(f"[{func.__name__}] Usuario {usuario.id} rol no autorizado")
            return jsonify({'msg': 'Solo clientes pueden realizar esta acción'}), 403
        return func(*args, **kwargs)
    return wrapper


# ---------------------------
# Formulario nuevo producto
# ---------------------------
@producto_bp.route('/productos/nuevo', methods=['GET'])
@login_required
@validate_active_cliente
def nuevo_producto():
    categorias = Categoria.query.filter_by(cliente_id=current_user.id).all()
    marcas = Marca.query.filter_by(cliente_id=current_user.id).all()
    logger.info(f"[nuevo_producto] Usuario {current_user.id} accede con {len(categorias)} categorías y {len(marcas)} marcas")
    return render_template('nuevo_producto.html', categorias=categorias, marcas=marcas)


# ---------------------------
# Crear producto
# ---------------------------
@producto_bp.route('/productos', methods=['POST'])
@login_required
@validate_active_cliente
def crear_producto():
    data = request.form
    categoria_nombre = data.get('categoria_nombre', '').strip()
    marca_nombre = data.get('marca_nombre', '').strip()

    # Validaciones básicas
    if not all([data.get('nombre'), data.get('precio'), data.get('stock'), categoria_nombre, marca_nombre]):
        return jsonify({'msg': 'Todos los campos obligatorios deben completarse'}), 400

    try:
        precio = float(data.get('precio'))
        stock = int(data.get('stock'))
        if precio <= 0 or stock < 0:
            raise ValueError
    except ValueError:
        return jsonify({'msg': 'Precio o stock inválidos'}), 400

    # Categoría
    categoria = Categoria.query.filter_by(nombre=categoria_nombre, cliente_id=current_user.id).first()
    if not categoria:
        if len(categoria_nombre) < 3:
            return jsonify({'msg': 'Nombre de categoría inválido'}), 400
        categoria = Categoria(nombre=categoria_nombre, cliente_id=current_user.id)
        db.session.add(categoria)
        db.session.commit()

    # Marca
    marca = Marca.query.filter_by(nombre=marca_nombre, cliente_id=current_user.id).first()
    if not marca:
        if len(marca_nombre) < 2:
            return jsonify({'msg': 'Nombre de marca inválido'}), 400
        marca = Marca(nombre=marca_nombre, cliente_id=current_user.id)
        db.session.add(marca)
        db.session.commit()

    # Imagen
    imagen_nombre = None
    file = request.files.get('imagen')
    if file and allowed_file(file.filename):
        file.seek(0, os.SEEK_END)
        if file.tell() > MAX_FILE_SIZE:
            return jsonify({'msg': 'Archivo excede el tamaño máximo'}), 400
        file.seek(0)
        filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        upload_path = os.path.join(current_app.root_path, 'static/uploads')
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        imagen_nombre = filename

    # Crear producto
    nuevo_producto = Producto(
        nombre=data['nombre'].strip(),
        descripcion=data.get('descripcion', '').strip(),
        precio=precio,
        stock=stock,
        imagen_url=imagen_nombre or '',
        categoria_id=categoria.id,
        marca_id=marca.id,
        cliente_id=current_user.id
    )
    db.session.add(nuevo_producto)
    db.session.commit()
    logger.info(f"[crear_producto] Producto creado ID={nuevo_producto.id}")

    return redirect(url_for('producto.listar_mis_productos'))


# ---------------------------
# Listar mis productos
# ---------------------------
@producto_bp.route('/mis-productos', methods=['GET'])
@login_required
@validate_active_cliente
def listar_mis_productos():
    productos = Producto.query.filter_by(cliente_id=current_user.id).all()
    return render_template('mis_productos.html', productos=productos)


# ---------------------------
# Ver / Editar / Actualizar producto
# ---------------------------
@producto_bp.route('/productos/<int:producto_id>', methods=['GET'])
@login_required
@validate_active_cliente
def obtener_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if producto.cliente_id != current_user.id:
        return jsonify({'msg': 'No autorizado'}), 403
    return render_template('detalle_producto.html', producto=producto)


@producto_bp.route('/productos/<int:producto_id>/editar', methods=['GET'])
@login_required
@validate_active_cliente
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if producto.cliente_id != current_user.id:
        return jsonify({'msg': 'No autorizado'}), 403
    categorias = Categoria.query.filter_by(cliente_id=current_user.id).all()
    marcas = Marca.query.filter_by(cliente_id=current_user.id).all()
    return render_template('editar_producto.html', producto=producto, categorias=categorias, marcas=marcas)


@producto_bp.route('/productos/<int:producto_id>', methods=['POST'])
@login_required
@validate_active_cliente
def actualizar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if producto.cliente_id != current_user.id:
        return jsonify({'msg': 'No autorizado'}), 403

    data = request.form
    marca_nombre = data.get('marca_nombre', '').strip()
    categoria_id = data.get('categoria_id')

    # Marca: si no existe, crear automáticamente
    marca = None
    if marca_nombre:
        marca = Marca.query.filter_by(nombre=marca_nombre, cliente_id=current_user.id).first()
        if not marca:
            marca = Marca(nombre=marca_nombre, cliente_id=current_user.id)
            db.session.add(marca)
            db.session.commit()

    producto.nombre = data.get('nombre', producto.nombre).strip()
    producto.descripcion = data.get('descripcion', producto.descripcion).strip()
    producto.precio = float(data.get('precio', producto.precio))
    producto.stock = int(data.get('stock', producto.stock))
    if categoria_id:
        producto.categoria_id = int(categoria_id)
    if marca:
        producto.marca_id = marca.id

    # Imagen
    file = request.files.get('imagen')
    if file and allowed_file(file.filename):
        filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        upload_path = os.path.join(current_app.root_path, 'static/uploads')
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        producto.imagen_url = filename

    db.session.commit()
    logger.info(f"[actualizar_producto] Producto {producto_id} actualizado")
    return redirect(url_for('producto.listar_mis_productos'))


# ---------------------------
# Eliminar producto
# ---------------------------
@producto_bp.route('/productos/<int:producto_id>/eliminar', methods=['POST'])
@login_required
@validate_active_cliente
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if producto.cliente_id != current_user.id:
        return jsonify({'msg': 'No autorizado'}), 403
    if producto.imagen_url:
        path = os.path.join(current_app.root_path, 'static/uploads', producto.imagen_url)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(producto)
    db.session.commit()
    return redirect(url_for('producto.listar_mis_productos'))


# ---------------------------
# Carrito (igual que antes)
# ---------------------------
@producto_bp.route('/carrito/agregar/<int:producto_id>', methods=['POST'])
@login_required
@validate_active_cliente
def agregar_al_carrito(producto_id):
    carrito = session.get('carrito', {})
    str_id = str(producto_id)
    carrito[str_id] = carrito.get(str_id, 0) + 1
    session['carrito'] = carrito
    session.modified = True
    flash('Producto añadido al estante virtual.', 'success')
    return redirect(url_for('producto.listar_mis_productos'))


@producto_bp.route('/carrito', methods=['GET'])
@login_required
@validate_active_cliente
def ver_carrito():
    carrito = session.get('carrito', {})
    productos_carrito = []
    total = 0
    for pid, cantidad in carrito.items():
        p = Producto.query.get(int(pid))
        if p:
            subtotal = p.precio * cantidad
            total += subtotal
            productos_carrito.append({'producto': p, 'cantidad': cantidad, 'subtotal': subtotal})
    return render_template('carrito.html', productos_carrito=productos_carrito, total=total)


# ---------------------------------
# ACTUALIZAR CANTIDAD – MÍNIMO 1, SIN DUPLICADOS
# ---------------------------------
@producto_bp.route('/carrito/actualizar/<int:producto_id>', methods=['POST'])
@login_required
@validate_active_cliente
def actualizar_cantidad(producto_id):
    try:
        nueva_cantidad = int(request.form.get('cantidad', 1))
    except (ValueError, TypeError):
        nueva_cantidad = 1

    if nueva_cantidad < 1:
        nueva_cantidad = 1

    producto = Producto.query.get_or_404(producto_id)
    if nueva_cantidad > producto.stock:
        nueva_cantidad = producto.stock

    carrito = session.get('carrito', {})
    str_id = str(producto_id)
    old_cantidad = carrito.get(str_id, 0)

    if old_cantidad != nueva_cantidad:
        carrito[str_id] = nueva_cantidad
        session['carrito'] = carrito
        session.modified = True
        flash('Cantidad actualizada', 'success')

    from flask import get_flashed_messages
    get_flashed_messages()  # Evita mensaje fantasma

    return redirect(url_for('producto.ver_carrito'))


# ---------------------------------
# ELIMINAR PRODUCTO
# ---------------------------------
@producto_bp.route('/carrito/eliminar/<int:producto_id>', methods=['POST'])
@login_required
@validate_active_cliente
def eliminar_del_carrito(producto_id):
    carrito = session.get('carrito', {})
    str_id = str(producto_id)

    if str_id in carrito:
        del carrito[str_id]
        session['carrito'] = carrito
        session.modified = True
        flash('Producto eliminado del carrito', 'success')

    from flask import get_flashed_messages
    get_flashed_messages()

    return redirect(url_for('producto.ver_carrito'))

# ---------------------------
# API pública de productos
# ---------------------------
@producto_bp.route('/filtro-productos')
@login_required
@validate_active_cliente
def filtro_productos():
    query = db.session.query(Producto).join(Categoria).filter(Producto.cliente_id == current_user.id)
    nombre = request.args.get('nombre', '').strip()
    marca = request.args.get('marca', '').strip()
    categoria_texto = request.args.get('categoria', '').strip()
    precio_min = request.args.get('precio_min', type=float)
    precio_max = request.args.get('precio_max', type=float)

    if nombre:
        query = query.filter(Producto.nombre.ilike(f'%{nombre}%'))
    if marca:
        query = query.join(Marca).filter(Marca.nombre.ilike(f'%{marca}%'))
    if categoria_texto:
        query = query.filter(Categoria.nombre.ilike(f'%{categoria_texto}%'))
    if precio_min is not None:
        query = query.filter(Producto.precio >= precio_min)
    if precio_max is not None:
        query = query.filter(Producto.precio <= precio_max)

    productos = query.all()
    return render_template('mis_productos.html', productos=productos)

@producto_bp.route('/productos', methods=['GET'])
def api_productos_publicos():
    productos = Producto.query.all()
    return jsonify([p.to_dict() for p in productos]), 200
