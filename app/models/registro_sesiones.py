from app.extensions import db
from datetime import datetime

class RegistroSesiones(db.Model):
    __tablename__ = "registro_sesiones"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    token_sesion = db.Column(db.String(255), nullable=False, unique=True)
    direccion_ip = db.Column(db.String(100))
    agente_usuario = db.Column(db.Text)
    fecha_inicio = db.Column(db.DateTime, default=datetime.now)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), default="activa")

    usuario = db.relationship("Usuario", backref="sesiones")
