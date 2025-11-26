from app.extensions import db  
from app.models.logs_acciones import LogsAcciones
from datetime import datetime
import logging

logger_transacciones = logging.getLogger('logs_transacciones')
logger_transacciones.setLevel(logging.INFO)
logger_transacciones.addHandler(logging.StreamHandler()) 

# Logger para autenticación
logger_autenticacion = logging.getLogger('logs_autenticacion')
logger_autenticacion.setLevel(logging.INFO)
logger_autenticacion.addHandler(logging.StreamHandler())

# Logger para errores
logger_errores = logging.getLogger('logs_errores')
logger_errores.setLevel(logging.ERROR)
logger_errores.addHandler(logging.StreamHandler())

# Logger para acciones 
logger_acciones = logging.getLogger('logs_acciones')
logger_acciones.setLevel(logging.INFO)
logger_acciones.addHandler(logging.StreamHandler())

# Funciones de uso 
def log_transaccion(mensaje):
    logger_transacciones.info(mensaje)

def log_autenticacion(mensaje):
    logger_autenticacion.info(mensaje)

def log_error(mensaje):
    logger_errores.error(mensaje)

def log_accion(mensaje):
    logger_acciones.info(mensaje)

def registrar_accion(usuario_id, accion, entidad, descripcion=None):
    try:
        nuevo_log = LogsAcciones(
            usuario_id=usuario_id,
            accion=accion,
            entidad=entidad,
            descripcion=descripcion,
            fecha=datetime.utcnow()
        )
        db.session.add(nuevo_log)
        db.session.commit()
        print(f"[LOG] Acción registrada: {accion} sobre {entidad} por usuario {usuario_id}")
        log_accion(f"Acción registrada: {accion} sobre {entidad} por {usuario_id}")  
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] No se pudo registrar la acción: {e}")
        log_error(f"Error en registrar_accion: {e}")  