from app.extensions import db
from sqlalchemy import BigInteger

class Marca(db.Model):
    __tablename__ = "marcas"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    cliente_id = db.Column(BigInteger, db.ForeignKey("usuarios.id"), nullable=False)

    # Relación con productos
    productos = db.relationship("Producto", back_populates="marca", cascade="all, delete")

    __table_args__ = (
        db.UniqueConstraint('nombre', 'cliente_id', name='uq_marca_nombre_cliente'),
    )

    def __repr__(self):
        return f"<Marca(id={self.id}, nombre={self.nombre!r}, cliente_id={self.cliente_id})>"
