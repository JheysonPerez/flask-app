from app.extensions import db
from datetime import datetime

class LogsAcciones(db.Model):
    __tablename__ = "logs_acciones"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)  
    accion = db.Column(db.String(50), nullable=False)
    entidad = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=db.func.now())

    usuario = db.relationship("Usuario", backref="logs_acciones")
