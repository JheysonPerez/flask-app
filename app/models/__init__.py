from sqlalchemy.ext.declarative import declarative_base

# Crear la clase base para los modelos
Base = declarative_base()

# Importar todos los modelos definidos
from .producto import Producto
from .compra import Compra
from .compra_producto import CompraProducto
from .usuario import Usuario
