# Definición del modelo Categoria
from app.extensions import db

class Categoria(db.Model):
    __tablename__ = "categorias"

    # Columnas de la tabla
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    # Relación con productos
    productos = db.relationship("Producto", back_populates="categoria", lazy="dynamic")

    # Representación en formato diccionario
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre
        }
