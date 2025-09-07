# Modelo Compra con validación y relaciones
from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship, Session
from sqlalchemy import event

class Compra(db.Model):
    __tablename__ = 'compras'

    # Columnas principales
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    tipo_comprobante_id = db.Column(db.Integer, db.ForeignKey('tipos_comprobante.id'), nullable=False)
    ruc = db.Column(db.String(11), nullable=True)
    dni = db.Column(db.String(8), nullable=True)  # Nuevo campo
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, nullable=False)
    email_destino = db.Column(db.String(120), nullable=False)

    # Relaciones
    tipo_comprobante = relationship('TipoComprobante', back_populates='compras')
    cliente = db.relationship('Usuario', back_populates='compras')
    productos = db.relationship('CompraProducto', back_populates='compra', lazy='subquery', cascade="all, delete")

    # Validación de reglas de negocio
    def validar_entidad(self):
        if self.tipo_comprobante_id not in (1, 2):
            raise ValueError("El tipo de comprobante debe ser válido (1=boleta, 2=factura).")

        if self.tipo_comprobante_id == 2:
            if not self.ruc or len(self.ruc) != 11:
                raise ValueError("El RUC debe tener 11 caracteres para una factura.")

        if self.tipo_comprobante_id == 1:
            if not self.dni or len(self.dni) != 8:
                raise ValueError("El DNI debe tener 8 caracteres para una boleta.")

    # Conversión a diccionario
    def to_dict(self):
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'tipo_comprobante': self.tipo_comprobante.nombre if self.tipo_comprobante else None,
            'ruc': self.ruc,
            'dni': self.dni,  # Incluimos el DNI en la respuesta
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'total': self.total,
            'email_destino': self.email_destino,
            'productos': [producto.to_dict() for producto in self.productos] if self.productos else []
        }

    def __repr__(self):
        return (f"<Compra(id={self.id}, cliente_id={self.cliente_id}, "
                f"tipo_comprobante={self.tipo_comprobante.nombre if self.tipo_comprobante else None}, total={self.total})>")

# Validación automática antes de guardar cambios
@event.listens_for(Session, "before_flush")
def validar_compra(session, flush_context, instances):
    for obj in session.new.union(session.dirty):
        if isinstance(obj, Compra):
            obj.validar_entidad()
