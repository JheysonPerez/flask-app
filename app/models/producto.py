# Modelo Producto con relaciones a Usuario (cliente) y Categoria
from app.extensions import db
from sqlalchemy import BigInteger

class Producto(db.Model):
    __tablename__ = "productos"

    # Atributos principales
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    marca = db.Column(db.String(100))  
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    imagen_url = db.Column(db.String(255))

    # Relaciones
    cliente_id = db.Column(BigInteger, db.ForeignKey("usuarios.id"), nullable=False)
    cliente = db.relationship("Usuario", back_populates="productos")

    categoria_id = db.Column(BigInteger, db.ForeignKey("categorias.id"), nullable=True)
    categoria = db.relationship("Categoria", back_populates="productos")

    compra_productos = db.relationship(
        "CompraProducto",
        back_populates="producto",
        lazy="dynamic",
        cascade="all, delete"
    )

    # Conversión a diccionario
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "marca": self.marca,  
            "descripcion": self.descripcion,
            "precio": self.precio,
            "stock": self.stock,
            "imagen_url": self.imagen_url,
            "cliente_id": self.cliente_id,
            "categoria_id": self.categoria_id,
            "categoria_nombre": self.categoria.nombre if self.categoria else None
        }

    # Representación legible
    def __repr__(self):
        return (
            f"<Producto(id={self.id}, nombre={self.nombre!r}, marca={self.marca!r}, "
            f"precio={self.precio}, stock={self.stock}, "
            f"cliente_id={self.cliente_id}, categoria_id={self.categoria_id})>"
        )
