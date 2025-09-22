# Definición del modelo CompraProducto (tabla intermedia entre Compra y Producto)
from app.extensions import db

class CompraProducto(db.Model):
    __tablename__ = 'compra_producto'

    # Columnas principales
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compras.id', ondelete='CASCADE'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

    # Relaciones con Compra y Producto
    compra = db.relationship('Compra', back_populates='productos')
    producto = db.relationship('Producto', back_populates='compra_productos')

    # Representación en formato diccionario
    def to_dict(self):
        return {
            'id': self.id,
            'compra_id': self.compra_id,
            'producto_id': self.producto_id,
            'cantidad': self.cantidad,
            'producto': self.producto.to_dict() if self.producto else None
        }

    # Representación legible del objeto
    def __repr__(self):
        return f"<CompraProducto(id={self.id}, compra_id={self.compra_id}, producto_id={self.producto_id}, cantidad={self.cantidad})>"
