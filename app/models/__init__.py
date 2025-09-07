from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .producto import Producto
from .compra import Compra
from .compra_producto import CompraProducto
from .usuario import Usuario
from .categoria import Categoria
from .tipo_comprobante import TipoComprobante

__all__ = [
    "Producto",
    "Compra",
    "CompraProducto",
    "Usuario",
    "Categoria",
    "TipoComprobante"
]
