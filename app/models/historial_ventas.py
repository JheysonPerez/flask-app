# Modelo HistorialVenta con relaciones a cliente, producto y tipo de comprobante
from app.extensions import db

class HistorialVenta(db.Model):
    __tablename__ = "historial_ventas"

    # Columnas principales
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    total_venta = db.Column(db.Float, nullable=False)
    tipo_comprobante_id = db.Column(db.Integer, db.ForeignKey("tipos_comprobante.id"))
    fecha_venta = db.Column(db.DateTime, server_default=db.func.now())

    # Relaciones
    cliente = db.relationship("Usuario", backref="historial_ventas")
    producto = db.relationship("Producto", backref="historial_ventas")
    tipo_comprobante = db.relationship("TipoComprobante")

    # Conversión a diccionario
    def to_dict(self):
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "producto_id": self.producto_id,
            "cantidad": self.cantidad,
            "total_venta": self.total_venta,
            "tipo_comprobante_id": self.tipo_comprobante_id,
            "fecha_venta": self.fecha_venta.isoformat() if self.fecha_venta else None,
        }

    # Representación legible
    def __repr__(self):
        return f"<HistorialVenta id={self.id} total_venta={self.total_venta}>"
