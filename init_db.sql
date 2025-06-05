-- Crear secuencia para usuarios.id
CREATE SEQUENCE IF NOT EXISTS usuarios_id_seq;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id             BIGINT PRIMARY KEY DEFAULT nextval('usuarios_id_seq'),
    google_id      VARCHAR(255) UNIQUE,
    nombre         VARCHAR(100) NOT NULL,
    email          VARCHAR(120) UNIQUE NOT NULL,
    password_hash  VARCHAR(512),
    rol            VARCHAR(20) NOT NULL DEFAULT 'cliente',   -- cliente / administrador
    estado         VARCHAR(20) NOT NULL DEFAULT 'activo'     -- activo / inactivo
);

-- Crear secuencia para tipos_comprobante.id
CREATE SEQUENCE IF NOT EXISTS tipos_comprobante_id_seq;

-- Tabla de tipos de comprobante
CREATE TABLE IF NOT EXISTS tipos_comprobante (
    id     BIGINT PRIMARY KEY DEFAULT nextval('tipos_comprobante_id_seq'),
    nombre VARCHAR(20) UNIQUE NOT NULL   -- boleta / factura
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
    cliente_id          BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo_comprobante_id BIGINT REFERENCES tipos_comprobante(id),
    ruc                 VARCHAR(11),
    fecha               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total               NUMERIC(10,2) NOT NULL,
    email_destino       VARCHAR(120) NOT NULL,
    nombre_apellidos    VARCHAR(255)
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

-- Insertar usuario administrador si no existe
INSERT INTO usuarios (google_id, nombre, email, rol, estado)
VALUES
    ('admin-google-id-1', 'Jheyson Perez', 'jheyson.xcalibur.15@gmail.com', 'administrador', 'activo'),
    ('cliente-google-id-2', 'Jheyson Perez Ramirez', 'jheysonperezramirez6@gmail.com', 'cliente', 'activo'),
    ('cliente-google-id-3', 'Yordi Salvador Pascual', 'yordisalvador629@gmail.com', 'cliente', 'activo')
ON CONFLICT (email) DO NOTHING;

-- Insertar tipos de comprobante si no existen
INSERT INTO tipos_comprobante (nombre)
VALUES 
    ('boleta'), 
    ('factura')
ON CONFLICT (nombre) DO NOTHING;
