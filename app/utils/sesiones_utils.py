from app.extensions import db
from app.models.registro_sesiones import RegistroSesiones
from datetime import datetime
import uuid

def iniciar_sesion(usuario, ip=None, user_agent=None):
    token = str(uuid.uuid4())
    nueva = RegistroSesiones(
        usuario_id=usuario.id,
        token_sesion=token,
        direccion_ip=ip,
        agente_usuario=user_agent,
        fecha_inicio=datetime.utcnow(),
        estado="activa"
    )
    db.session.add(nueva)
    db.session.commit()
    return token


def cerrar_sesion(token):
    sesion = RegistroSesiones.query.filter_by(token_sesion=token, estado="activa").first()
    if sesion:
        sesion.estado = "cerrada"
        sesion.fecha_fin = datetime.utcnow()
        db.session.commit()
