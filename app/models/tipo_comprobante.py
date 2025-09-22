# Modelo TipoComprobante
from app.extensions import db

class TipoComprobante(db.Model):
    __tablename__ = "tipos_comprobante"

    # Atributos principales
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(20), unique=True, nullable=False)

    # Relaciones
    compras = db.relationship('Compra', back_populates='tipo_comprobante', lazy='subquery')

    # Representación legible
    def __repr__(self):
        return f"<TipoComprobante {self.nombre}>"

    # Conversión a diccionario
    def to_dict(self):
        return {
            "id": self.id,  
            "nombre": self.nombre
        }
