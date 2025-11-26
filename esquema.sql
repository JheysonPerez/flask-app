-- 
-- SQL Server schema migration from PostgreSQL dump
-- 
-- Notes:
-- - Sequences replaced with IDENTITY columns for auto-increment.
-- - Data types converted: character varying(N) -> NVARCHAR(N), text -> NVARCHAR(MAX), numeric(10,2) -> DECIMAL(10,2), timestamp without time zone -> DATETIME2.
-- - Defaults: CURRENT_TIMESTAMP -> GETDATE().
-- - Removed PostgreSQL-specific commands (SET, OWNER, sequences, \restrict).
-- - Primary keys inlined where possible.
-- - Run this script in SQL Server Management Studio (SSMS) after creating the database.
-- - Assumes default schema [dbo]; adjust if needed.
-- 

USE [flaskdb];  -- Replace with your target database name
GO

-- Enable quoted identifiers if needed
SET QUOTED_IDENTIFIER ON;
GO

-- Table: categorias
CREATE TABLE [dbo].[categorias] (
    [id] BIGINT IDENTITY(1,1) NOT NULL,
    [nombre] NVARCHAR(100) NOT NULL,
    [cliente_id] BIGINT NULL,
    CONSTRAINT [PK_categorias] PRIMARY KEY ([id]),
    CONSTRAINT [UK_categorias_nombre_cliente_id] UNIQUE ([nombre], [cliente_id])
);
GO

-- Table: compra_producto
CREATE TABLE [dbo].[compra_producto] (
    [id] BIGINT IDENTITY(1,1) NOT NULL,
    [compra_id] BIGINT NOT NULL,
    [producto_id] BIGINT NOT NULL,
    [cantidad] INT NOT NULL,
    CONSTRAINT [PK_compra_producto] PRIMARY KEY ([id])
);
GO

-- Table: compras
CREATE TABLE [dbo].[compras] (
    [id] BIGINT IDENTITY(1,1) NOT NULL,
    [cliente_id] BIGINT NOT NULL,
    [tipo_comprobante_id] BIGINT NOT NULL,
    [ruc] NVARCHAR(11) NULL,
    [dni] NVARCHAR(8) NULL,
    [fecha] DATETIME2 DEFAULT GETDATE() NULL,
    [total] DECIMAL(10,2) NOT NULL,
    [email_destino] NVARCHAR(120) NOT NULL,
    CONSTRAINT [PK_compras] PRIMARY KEY ([id])
);
GO

-- Table: historial_ventas
CREATE TABLE [dbo].[historial_ventas] (
    [id] BIGINT IDENTITY(1,1) NOT NULL,
    [cliente_id] BIGINT NULL,
    [producto_id] BIGINT NULL,
    [cantidad] INT NOT NULL,
    [total_venta] DECIMAL(10,2) NOT NULL,
    [tipo_comprobante_id] BIGINT NULL,
    [fecha_venta] DATETIME2 DEFAULT GETDATE() NULL,
    CONSTRAINT [PK_historial_ventas] PRIMARY KEY ([id])
);
GO

-- Table: logs_acciones
CREATE TABLE [dbo].[logs_acciones] (
    [id] INT IDENTITY(1,1) NOT NULL,
    [usuario_id] INT NOT NULL,
    [accion] NVARCHAR(100) NOT NULL,
    [entidad] NVARCHAR(100) NOT NULL,
    [descripcion] NVARCHAR(MAX) NULL,
    [fecha] DATETIME2 NULL,
    CONSTRAINT [PK_logs_acciones] PRIMARY KEY ([id])
);
GO

-- Table: marcas
CREATE TABLE [dbo].[marcas] (
    [id] BIGINT IDENTITY(1,1) NOT NULL,
    [nombre] NVARCHAR(100) NOT NULL,
    [cliente_id] BIGINT NULL,
    CONSTRAINT [PK_marcas] PRIMARY KEY ([id]),
    CONSTRAINT [UK_marcas_nombre_cliente_id] UNIQUE ([nombre], [cliente_id])
);
GO

-- Table: productos
CREATE TABLE [dbo].[productos] (
    [id] BIGINT IDENTITY(1,1) NOT NULL,
    [cliente_id] BIGINT NOT NULL,
    [categoria_id] BIGINT NULL,
    [marca_id] BIGINT NULL,
    [nombre] NVARCHAR(100) NOT NULL,
    [descripcion] NVARCHAR(MAX) NULL,
    [precio] DECIMAL(10,2) NOT NULL,
    [stock] INT NOT NULL,
    [imagen_url] NVARCHAR(255) NULL,
    CONSTRAINT [PK_productos] PRIMARY KEY ([id])
);
GO

-- Table: registro_sesiones
CREATE TABLE [dbo].[registro_sesiones] (
    [id] INT IDENTITY(1,1) NOT NULL,
    [usuario_id] INT NOT NULL,
    [token_sesion] NVARCHAR(255) NOT NULL,
    [direccion_ip] NVARCHAR(45) NULL,
    [agente_usuario] NVARCHAR(MAX) NULL,
    [fecha_inicio] DATETIME2 DEFAULT GETDATE() NULL,
    [fecha_fin] DATETIME2 NULL,
    [estado] NVARCHAR(20) DEFAULT N'activa' NULL,
    CONSTRAINT [PK_registro_sesiones] PRIMARY KEY ([id]),
    CONSTRAINT [UK_registro_sesiones_token_sesion] UNIQUE ([token_sesion])
);
GO

-- Table: tipos_comprobante
CREATE TABLE [dbo].[tipos_comprobante] (
    [id] BIGINT IDENTITY(1,1) NOT NULL,
    [nombre] NVARCHAR(20) NOT NULL,
    CONSTRAINT [PK_tipos_comprobante] PRIMARY KEY ([id]),
    CONSTRAINT [UK_tipos_comprobante_nombre] UNIQUE ([nombre])
);
GO

-- Table: usuarios
CREATE TABLE [dbo].[usuarios] (
    [id] BIGINT IDENTITY(1,1) NOT NULL,
    [google_id] NVARCHAR(255) NULL,
    [nombre] NVARCHAR(100) NOT NULL,
    [email] NVARCHAR(120) NOT NULL,
    [password_hash] NVARCHAR(512) NULL,
    [rol] NVARCHAR(20) DEFAULT N'cliente' NOT NULL,
    [estado] NVARCHAR(20) DEFAULT N'activo' NOT NULL,
    CONSTRAINT [PK_usuarios] PRIMARY KEY ([id]),
    CONSTRAINT [UK_usuarios_email] UNIQUE ([email]),
    CONSTRAINT [UK_usuarios_google_id] UNIQUE ([google_id])
);
GO

-- Foreign Keys
ALTER TABLE [dbo].[categorias] 
ADD CONSTRAINT [FK_categorias_cliente_id] FOREIGN KEY ([cliente_id]) REFERENCES [dbo].[usuarios] ([id]) ON DELETE CASCADE;
GO

ALTER TABLE [dbo].[compra_producto] 
ADD CONSTRAINT [FK_compra_producto_compra_id] FOREIGN KEY ([compra_id]) REFERENCES [dbo].[compras] ([id]) ON DELETE CASCADE;
GO

ALTER TABLE [dbo].[compra_producto] 
ADD CONSTRAINT [FK_compra_producto_producto_id] FOREIGN KEY ([producto_id]) REFERENCES [dbo].[productos] ([id]) ON DELETE CASCADE;
GO

ALTER TABLE [dbo].[compras] 
ADD CONSTRAINT [FK_compras_cliente_id] FOREIGN KEY ([cliente_id]) REFERENCES [dbo].[usuarios] ([id]) ON DELETE CASCADE;
GO

ALTER TABLE [dbo].[compras] 
ADD CONSTRAINT [FK_compras_tipo_comprobante_id] FOREIGN KEY ([tipo_comprobante_id]) REFERENCES [dbo].[tipos_comprobante] ([id]);
GO

ALTER TABLE [dbo].[historial_ventas] 
ADD CONSTRAINT [FK_historial_ventas_cliente_id] FOREIGN KEY ([cliente_id]) REFERENCES [dbo].[usuarios] ([id]) ON DELETE SET NULL;
GO

ALTER TABLE [dbo].[historial_ventas] 
ADD CONSTRAINT [FK_historial_ventas_producto_id] FOREIGN KEY ([producto_id]) REFERENCES [dbo].[productos] ([id]) ON DELETE SET NULL;
GO

ALTER TABLE [dbo].[historial_ventas] 
ADD CONSTRAINT [FK_historial_ventas_tipo_comprobante_id] FOREIGN KEY ([tipo_comprobante_id]) REFERENCES [dbo].[tipos_comprobante] ([id]);
GO

ALTER TABLE [dbo].[marcas] 
ADD CONSTRAINT [FK_marcas_cliente_id] FOREIGN KEY ([cliente_id]) REFERENCES [dbo].[usuarios] ([id]) ON DELETE CASCADE;
GO

ALTER TABLE [dbo].[productos] 
ADD CONSTRAINT [FK_productos_categoria_id] FOREIGN KEY ([categoria_id]) REFERENCES [dbo].[categorias] ([id]) ON DELETE SET NULL;
GO

ALTER TABLE [dbo].[productos] 
ADD CONSTRAINT [FK_productos_cliente_id] FOREIGN KEY ([cliente_id]) REFERENCES [dbo].[usuarios] ([id]) ON DELETE CASCADE;
GO

ALTER TABLE [dbo].[productos] 
ADD CONSTRAINT [FK_productos_marca_id] FOREIGN KEY ([marca_id]) REFERENCES [dbo].[marcas] ([id]) ON DELETE SET NULL;
GO

ALTER TABLE [dbo].[registro_sesiones] 
ADD CONSTRAINT [FK_registro_sesiones_usuario_id] FOREIGN KEY ([usuario_id]) REFERENCES [dbo].[usuarios] ([id]);
GO

-- Schema migration complete
-- Next steps: Execute this in SSMS, then migrate data using the Import/Export Wizard as previously described.
-- If there are any errors (e.g., due to data types), let me know the exact message!

