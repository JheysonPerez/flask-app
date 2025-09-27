from app.extensions import db
from app.models.usuario import Usuario

class Marca(db.Model):
    __tablename__ = "marcas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    cliente = db.relationship("Usuario", backref=db.backref("marcas", lazy="dynamic"))

    productos = db.relationship("Producto", back_populates="marca", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint('nombre', 'cliente_id', name='uix_nombre_marca_cliente'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "cliente_id": self.cliente_id
        }
