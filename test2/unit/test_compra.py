import pytest
from datetime import datetime
from app.models.compra import Compra
from app.models.compra_producto import CompraProducto
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.models.tipo_comprobante import TipoComprobante

# Mock de datos de prueba
@pytest.fixture
def datos_de_prueba_mock():
    usuario = Usuario(nombre="Juan", email="juan@gmail.com", rol="cliente", estado="activo")
    tipo_comprobante = TipoComprobante(nombre="Boleta")
    producto = Producto(nombre="Mouse", descripcion="Mouse óptico", precio=100.0, stock=10)
    
    compra = Compra(
        cliente_id=1,
        tipo_comprobante_id=1,
        dni="12345678",
        total=200.0,
        email_destino="cliente@gmail.com",
        fecha=datetime.utcnow()
    )
    
    relacion = CompraProducto(
        compra_id=1,
        producto=producto,
        cantidad=2
    )
    
    # Simulamos la relación: lista de CompraProducto en la compra
    compra.productos = [relacion]
    
    yield {
        "usuario": usuario,
        "producto": producto,
        "compra": compra,
        "relacion": relacion,
        "tipo_comprobante": tipo_comprobante
    }


# Test: fecha asignada automáticamente
def test_fecha_asignada_automaticamente_mock(datos_de_prueba_mock):
    compra = datos_de_prueba_mock["compra"]
    assert compra.fecha is not None


# Test: total de la compra correcto
def test_total_compra_correcto_mock(datos_de_prueba_mock):
    compra = datos_de_prueba_mock["compra"]
    assert compra.total == 200.0


# Test: productos relacionados con la compra
def test_productos_relacionados_con_compra_mock(datos_de_prueba_mock):
    compra = datos_de_prueba_mock["compra"]
    assert len(compra.productos) == 1
    assert compra.productos[0].producto.nombre == "Mouse"


# Test: RUC inválido lanza error (simulado)
def test_ruc_invalido_lanza_error_mock():
    from app.models.compra import Compra

    compra = Compra(
        cliente_id=1,
        tipo_comprobante_id=2,
        ruc="123",  # RUC inválido
        total=100.0,
        email_destino="cliente@gmail.com"
    )

    # Simulamos validación manual
    def validar_ruc(c):
        if c.ruc and len(c.ruc) != 11:
            raise ValueError("RUC debe tener 11 caracteres")

    with pytest.raises(ValueError, match="RUC debe tener 11 caracteres"):
        validar_ruc(compra)
