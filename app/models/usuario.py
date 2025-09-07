from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import exc, BigInteger

class Usuario(UserMixin, db.Model):  # ✅ Hereda de UserMixin
    __tablename__ = 'usuarios'

    # Atributos principales
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    google_id = db.Column(BigInteger, unique=True, nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=True)
    rol = db.Column(db.String(20), nullable=False, default='cliente')
    estado = db.Column(db.String(20), nullable=False, default='activo')

    # Relaciones
    compras = db.relationship(
        'Compra',
        back_populates='cliente',
        lazy='dynamic',
        cascade="all, delete"
    )
    productos = db.relationship(
        'Producto',
        back_populates='cliente',
        lazy='dynamic',
        cascade="all, delete"
    )

    # Métodos de autenticación
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    # Flask-Login: ya no necesitas definir is_authenticated, is_anonymous ni get_id()
    @property
    def is_active(self):  # ✅ Usado por Flask-Login
        return self.estado == 'activo'

    # Conversión a diccionario
    def to_dict(self):
        return {
            'id': self.id,
            'google_id': self.google_id,
            'nombre': self.nombre,
            'email': self.email,
            'rol': self.rol,
            'estado': self.estado
        }

    @staticmethod
    def create_from_dict(data):
        try:
            nuevo_usuario = Usuario(
                nombre=data['nombre'],
                email=data['email'],
                rol=data.get('rol', 'cliente')
            )
            nuevo_usuario.set_password(data['password'])
            db.session.add(nuevo_usuario)
            db.session.commit()
            return nuevo_usuario
        except exc.IntegrityError:
            db.session.rollback()
            return None
        except KeyError as e:
            db.session.rollback()
            raise ValueError(f"Falta el campo requerido: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise e

    def __repr__(self):
        return (
            f"<Usuario id={self.id}, google_id={self.google_id}, "
            f"nombre={self.nombre}, email={self.email}, rol={self.rol}>"
        )
