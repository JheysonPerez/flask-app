-- Crear secuencia para usuarios.id
CREATE SEQUENCE IF NOT EXISTS usuarios_id_seq;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id             BIGINT PRIMARY KEY DEFAULT nextval('usuarios_id_seq'),
    google_id      VARCHAR(255) UNIQUE,
    nombre         VARCHAR(100) NOT NULL,
    email          VARCHAR(120) UNIQUE NOT NULL,
    password_hash  VARCHAR(512),
    rol            VARCHAR(20) NOT NULL DEFAULT 'cliente',
    estado         VARCHAR(20) NOT NULL DEFAULT 'activo'
);

-- Crear secuencia para tipos_comprobante.id
CREATE SEQUENCE IF NOT EXISTS tipos_comprobante_id_seq;

-- Tabla de tipos de comprobante
CREATE TABLE IF NOT EXISTS tipos_comprobante (
    id     BIGINT PRIMARY KEY DEFAULT nextval('tipos_comprobante_id_seq'),
    nombre VARCHAR(20) UNIQUE NOT NULL
);

-- Crear secuencia para categorias.id
CREATE SEQUENCE IF NOT EXISTS categorias_id_seq;

-- Tabla de categorías
CREATE TABLE IF NOT EXISTS categorias (
    id     BIGINT PRIMARY KEY DEFAULT nextval('categorias_id_seq'),
    nombre VARCHAR(100) UNIQUE NOT NULL
);

-- Crear secuencia para productos.id
CREATE SEQUENCE IF NOT EXISTS productos_id_seq;

-- Tabla de productos 
CREATE TABLE IF NOT EXISTS productos (
    id           BIGINT PRIMARY KEY DEFAULT nextval('productos_id_seq'),
    cliente_id   BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria_id BIGINT REFERENCES categorias(id) ON DELETE SET NULL,
    nombre       VARCHAR(100) NOT NULL,
    marca        VARCHAR(100),
    descripcion  TEXT,
    precio       NUMERIC(10,2) NOT NULL,
    stock        INT NOT NULL,
    imagen_url   VARCHAR(255)
);

-- Crear secuencia para compras.id
CREATE SEQUENCE IF NOT EXISTS compras_id_seq;

-- Tabla de compras
CREATE TABLE IF NOT EXISTS compras (
    id                  BIGINT PRIMARY KEY DEFAULT nextval('compras_id_seq'),
    cliente_id          BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo_comprobante_id BIGINT NOT NULL REFERENCES tipos_comprobante(id),
    ruc                 VARCHAR(11),
    dni                 VARCHAR(8),
    fecha               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total               NUMERIC(10,2) NOT NULL,
    email_destino       VARCHAR(120) NOT NULL
);

-- Crear secuencia para compra_producto.id
CREATE SEQUENCE IF NOT EXISTS compra_producto_id_seq;

-- Tabla intermedia compra-producto
CREATE TABLE IF NOT EXISTS compra_producto (
    id          BIGINT PRIMARY KEY DEFAULT nextval('compra_producto_id_seq'),
    compra_id   BIGINT NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
    producto_id BIGINT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    cantidad    INT NOT NULL
);

-- Crear secuencia para historial_ventas.id
CREATE SEQUENCE IF NOT EXISTS historial_ventas_id_seq;

-- Historial de ventas
CREATE TABLE IF NOT EXISTS historial_ventas (
    id                  BIGINT PRIMARY KEY DEFAULT nextval('historial_ventas_id_seq'),
    cliente_id          BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    producto_id         BIGINT REFERENCES productos(id) ON DELETE SET NULL,
    cantidad            INT NOT NULL,
    total_venta         NUMERIC(10,2) NOT NULL,
    tipo_comprobante_id BIGINT REFERENCES tipos_comprobante(id),
    fecha_venta         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar usuarios si no existen
INSERT INTO usuarios (id, google_id, nombre, email, rol, estado)
VALUES
    (1, 'admin-google-id-1', 'Jheyson Perez', 'jheysonperezramirez6@gmail.com', 'administrador', 'activo'),
    (2, 'cliente-google-id-2', 'Jheyson Perez Ramirez', 'jheyson.xcalibur.15@gmail.com', 'cliente', 'activo')
ON CONFLICT (email) DO NOTHING;

-- Insertar tipos de comprobante
INSERT INTO tipos_comprobante (id, nombre)
VALUES 
    (1, 'boleta'), 
    (2, 'factura')
ON CONFLICT (nombre) DO NOTHING;

-- Insertar categoría
INSERT INTO categorias (id, nombre)
VALUES (1, 'Electrónica')
ON CONFLICT (nombre) DO NOTHING;

-- Insertar producto de prueba (usado en Locust)
INSERT INTO productos (id, cliente_id, categoria_id, nombre, marca, descripcion, precio, stock, imagen_url)
VALUES (
    1,              -- id
    2,              -- cliente_id (cliente creado anteriormente)
    1,              -- categoria_id
    'Audifonos Gamer',
    'Hyperx',
    'Producto de prueba para Locust',
    100,
    500,
    'https://via.placeholder.com/150'
)
ON CONFLICT (id) DO NOTHING;

-- 🔧 ACTUALIZAR SECUENCIAS PARA EVITAR CONFLICTOS DE ID DUPLICADOS
SELECT setval('usuarios_id_seq',        (SELECT MAX(id) FROM usuarios));
SELECT setval('tipos_comprobante_id_seq', (SELECT MAX(id) FROM tipos_comprobante));
SELECT setval('categorias_id_seq',      (SELECT MAX(id) FROM categorias));
SELECT setval('productos_id_seq',       (SELECT MAX(id) FROM productos));
SELECT setval('compras_id_seq',         COALESCE((SELECT MAX(id) FROM compras), 1));
SELECT setval('compra_producto_id_seq', COALESCE((SELECT MAX(id) FROM compra_producto), 1));
SELECT setval('historial_ventas_id_seq',COALESCE((SELECT MAX(id) FROM historial_ventas), 1));
