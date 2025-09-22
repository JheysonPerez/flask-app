from flask import Blueprint, request, render_template, jsonify
from flask_login import login_required, current_user
from app.models.historial_ventas import HistorialVenta
from app.models.usuario import Usuario
from collections import defaultdict, Counter
from datetime import datetime
from app.extensions import db
import pytz
import logging


# Crear blueprints
historial_ventas_bp = Blueprint("historial_ventas", __name__)
dashboard_ventas_bp  = Blueprint("dashboard_ventas",  __name__)

# Configurar logger personalizado para el backend Flask
logger = logging.getLogger("flask_backend")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


@historial_ventas_bp.route("/historial_ventas")
@login_required
def mostrar_historial_ventas():
    usuario = current_user
    if usuario.estado != "activo":
        logger.warning(f"[mostrar_historial_ventas] Usuario {usuario.id} inactivo intentó acceder")
        return jsonify({"msg": "Usuario inactivo"}), 403

    historial = HistorialVenta.query.filter_by(cliente_id=usuario.id).all()
    logger.info(f"[mostrar_historial_ventas] Usuario {usuario.id} visualiza {len(historial)} ventas")

    return render_template("historial_ventas.html", historial=historial)


@dashboard_ventas_bp.route('/dashboard_ventas')
@login_required
def dashboard_ventas():
    agrupacion = request.args.get('agrupacion', 'dia')
    ventas = db.session.query(HistorialVenta).all()
    filtro = request.args.get('filtro', 'tipo_comprobante')

    datos_agrupados = defaultdict(float)
    etiquetas = []

    zona_local = pytz.timezone('America/Lima')
    hoy = datetime.now(zona_local)

    if agrupacion == 'dia':
        etiquetas = [f'{hora:02d}:00' for hora in range(24)]
        for venta in ventas:
            fecha_local = venta.fecha_venta.astimezone(zona_local)
            if fecha_local.date() == hoy.date():
                hora = fecha_local.hour
                datos_agrupados[f'{hora:02d}:00'] += venta.total_venta  

    elif agrupacion == 'semana':
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        etiquetas = dias_semana
        for venta in ventas:
            fecha_local = venta.fecha_venta.astimezone(zona_local)
            if (hoy - fecha_local).days < 7:
                nombre_dia = fecha_local.strftime('%A')
                traducciones = {
                    'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                    'Thursday': 'Jueves', 'Friday': 'Viernes',
                    'Saturday': 'Sábado', 'Sunday': 'Domingo'
                }
                nombre_dia = traducciones.get(nombre_dia, nombre_dia)
                datos_agrupados[nombre_dia] += venta.total_venta  

    elif agrupacion == 'mes':
        etiquetas = ['Semana 1', 'Semana 2', 'Semana 3', 'Semana 4']
        for venta in ventas:
            fecha_local = venta.fecha_venta.astimezone(zona_local)
            if fecha_local.month == hoy.month and fecha_local.year == hoy.year:
                dia = fecha_local.day
                if dia <= 7:
                    semana = 'Semana 1'
                elif dia <= 14:
                    semana = 'Semana 2'
                elif dia <= 21:
                    semana = 'Semana 3'
                else:
                    semana = 'Semana 4'
                datos_agrupados[semana] += venta.total_venta  

    montos = [round(datos_agrupados.get(etiqueta, 0), 2) for etiqueta in etiquetas]

    # Gráficos de comprobantes
    comprobantes_montos = defaultdict(float)
    comprobantes_conteo = Counter()

    for venta in ventas:
        if hasattr(venta, "tipo_comprobante") and venta.tipo_comprobante:
            nombre = venta.tipo_comprobante.nombre
            comprobantes_montos[nombre] += venta.total_venta
            comprobantes_conteo[nombre] += 1

    nombres_comprobantes = list(comprobantes_montos.keys())
    totales_comprobantes = list(comprobantes_montos.values())

    nombres_conteo = list(comprobantes_conteo.keys())
    valores_conteo = list(comprobantes_conteo.values())
    total_conteos = sum(valores_conteo) or 1
    conteos = [round((v / total_conteos) * 100, 2) for v in valores_conteo]

    # Gráfico dinámico 
    agrupaciones_montos = defaultdict(float)
    agrupaciones_conteo = Counter()

    for venta in ventas:
        key = None

        if filtro == 'tipo_comprobante' and hasattr(venta, 'tipo_comprobante') and venta.tipo_comprobante:
            key = venta.tipo_comprobante.nombre
            if key:
                agrupaciones_montos[key] += venta.total_venta
                agrupaciones_conteo[key] += 1
        elif filtro == 'producto' and hasattr(venta, 'producto') and venta.producto:
            key = venta.producto.nombre
        elif filtro == 'marca' and hasattr(venta, 'producto') and venta.producto and venta.producto.marca:
            key = venta.producto.marca
        elif filtro == 'categoria' and hasattr(venta, 'producto') and venta.producto and venta.producto.categoria:
            key = venta.producto.categoria.nombre

        if key and filtro != 'tipo_comprobante':
            agrupaciones_montos[key] += venta.total_venta
            agrupaciones_conteo[key] += venta.cantidad

    nombres_grafico = list(agrupaciones_montos.keys())
    montos_grafico = list(agrupaciones_montos.values())
    valores_conteo_grafico = list(agrupaciones_conteo.values())
    total_conteo_grafico = sum(valores_conteo_grafico) or 1
    porcentajes_grafico = [round((v / total_conteo_grafico) * 100, 2) for v in valores_conteo_grafico]
    cantidades_grafico = valores_conteo_grafico 

    return render_template(
        'dashboard_ventas.html',
        fechas=etiquetas,
        montos=montos,
        nombres_comprobantes=nombres_comprobantes,
        totales_comprobantes=totales_comprobantes,
        nombres_conteo=nombres_conteo,
        conteos=conteos,
        agrupacion=agrupacion,
        filtro=filtro,
        nombres_grafico=nombres_grafico,
        montos_grafico=montos_grafico,
        porcentajes_grafico=porcentajes_grafico,
        cantidades_grafico=cantidades_grafico  
    )


#Pruebas con locust
@dashboard_ventas_bp.route('/api/dashboard/ventas')
def api_dashboard_ventas():
    from collections import defaultdict
    from datetime import datetime
    import pytz

    zona_local = pytz.timezone('America/Lima')
    hoy = datetime.now(zona_local)

    ventas = HistorialVenta.query.all()
    datos = defaultdict(float)

    for venta in ventas:
        fecha_local = venta.fecha_venta.astimezone(zona_local)
        if fecha_local.date() == hoy.date():
            hora = fecha_local.hour
            datos[f'{hora:02d}:00'] += venta.total_venta

    return jsonify({
        "fechas": list(datos.keys()),
        "montos": list(datos.values()),
        "total_ventas": round(sum(datos.values()), 2),
        "cantidad_ventas": len(ventas)
    }), 200
