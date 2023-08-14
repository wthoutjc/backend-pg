USE ud_pg;

SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS `users` CASCADE;

DROP TABLE IF EXISTS `clients` CASCADE;

DROP TABLE IF EXISTS `presupuesto_zonas` CASCADE;

DROP TABLE IF EXISTS `CEO` CASCADE;

DROP TABLE IF EXISTS `update_password` CASCADE;

DROP TABLE IF EXISTS `token_blocklist` CASCADE;

DROP TABLE IF EXISTS `zona` CASCADE;

DROP TABLE IF EXISTS `zona_departamento` CASCADE;

DROP TABLE IF EXISTS `zona_vendedor` CASCADE;

DROP TABLE IF EXISTS `departamento` CASCADE;

DROP TABLE IF EXISTS `ciudad` CASCADE;

DROP TABLE IF EXISTS `pedidos` CASCADE;

DROP TABLE IF EXISTS `venta` CASCADE;

DROP TABLE IF EXISTS `pedidos_cotizaciones` CASCADE;

DROP TABLE IF EXISTS `venta_cotizaciones` CASCADE;

DROP TABLE IF EXISTS `vendedor_listaprecios` CASCADE;

DROP TABLE IF EXISTS `vendedor_listaprecios_bodegas` CASCADE;

DROP TABLE IF EXISTS `namelp` CASCADE;

DROP TABLE IF EXISTS `listaprecios` CASCADE;

DROP TABLE IF EXISTS `agenda` CASCADE;

DROP TABLE IF EXISTS `pedidos_borrados` CASCADE;

DROP TABLE IF EXISTS `bodegas` CASCADE;

DROP TABLE IF EXISTS `pedidos_bodegas` CASCADE;

DROP TABLE IF EXISTS `venta_bodegas` CASCADE;

DROP TABLE IF EXISTS `namelp_bodegas` CASCADE;

DROP TABLE IF EXISTS `listaprecios_bodegas` CASCADE;

DROP TABLE IF EXISTS `clientes_favoritos` CASCADE;

DROP TABLE IF EXISTS `claims` CASCADE;

CREATE TABLE
    `users`(
        `k_users` BIGINT NOT NULL,
        `n_nombre` VARCHAR(75) NOT NULL,
        `n_apellido` VARCHAR(75) NOT NULL,
        `n_correo` VARCHAR(55) NOT NULL,
        `n_categoria` VARCHAR(11) NOT NULL,
        `o_password` VARCHAR(205) NOT NULL,
        `b_active` BOOLEAN NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `clients`(
        `k_cliente` BIGINT NOT NULL,
        `n_cliente` VARCHAR (100) NOT NULL,
        `n_correo` VARCHAR (100),
        `n_direccion` VARCHAR (100) NOT NULL,
        `k_departamento` VARCHAR(40) NOT NULL,
        `n_ciudad` VARCHAR (20) NOT NULL,
        `q_telefono` BIGINT NOT NULL,
        `q_telefono2` BIGINT,
        `k_zona` BIGINT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `presupuesto_zonas`(
        `k_zona` BIGINT NOT NULL,
        `q_mes` SMALLINT NOT NULL,
        `q_presupuesto` BIGINT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `update_password`(
        `k_users` BIGINT NOT NULL UNIQUE,
        `n_code` VARCHAR(36) NOT NULL UNIQUE,
        `f_exp` DATETIME NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `token_blocklist`(
        `k_token` BIGINT UNIQUE auto_increment,
        `n_jti` VARCHAR(36) UNIQUE NOT NULL,
        `f_created` DATETIME NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `zona` (
        `k_zona` BIGINT NOT NULL,
        `n_zona` VARCHAR(40) NOT NULL,
        `b_active` BOOLEAN NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `zona_departamento` (
        `k_zona` BIGINT NOT NULL,
        `k_departamento` VARCHAR(40) NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `zona_vendedor` (
        `k_zona` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `departamento` (
        `k_departamento` VARCHAR(40) NOT NULL,
        `n_departamento` VARCHAR(40) NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `ciudad` (
        `k_departamento` VARCHAR(40) NOT NULL,
        `n_ciudad` VARCHAR(40) NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `pedidos`(
        `k_venta` BIGINT UNIQUE NOT NULL auto_increment,
        `k_cliente` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `f_venta` DATE NOT NULL,
        `f_venta_autorizado` DATE,
        `f_venta_facturado` DATE,
        `f_venta_despachado` DATE,
        `n_estadop0` VARCHAR(20) NOT NULL,
        `n_estadop1` VARCHAR(20) NOT NULL,
        `n_estadop2` VARCHAR(20) NOT NULL,
        `n_observaciones` VARCHAR(255) NOT NULL,
        `b_active` BOOLEAN NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `venta`(
        `k_venta` BIGINT NOT NULL,
        `k_cliente` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `k_productos` VARCHAR(50) NOT NULL,
        `q_cantidad` SMALLINT NOT NULL,
        `q_bonificacion` SMALLINT NOT NULL,
        `q_totalkilos` DECIMAL(25, 1) NOT NULL,
        `q_totalkilosb` DECIMAL(25, 1) NOT NULL,
        `q_vunitario` DECIMAL(25, 1) NOT NULL,
        `q_valortotal` DECIMAL(25, 1) NOT NULL,
        `q_valortotalb` DECIMAL(25, 1) NOT NULL,
        `n_categoria` VARCHAR(14) NOT NULL,
        `q_cantidad_despachada` SMALLINT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `pedidos_cotizaciones`(
        `k_venta_cotizacion` BIGINT UNIQUE NOT NULL auto_increment,
        `k_cliente` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `f_venta` DATE NOT NULL,
        `n_observaciones` VARCHAR(255) NOT NULL,
        `b_active` BOOLEAN NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `venta_cotizaciones`(
        `k_venta_cotizacion` BIGINT NOT NULL,
        `k_listaprecios` INT NOT NULL,
        `k_cliente` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `k_productos` VARCHAR(50) NOT NULL,
        `q_cantidad` SMALLINT NOT NULL,
        `q_bonificacion` SMALLINT NOT NULL,
        `q_totalkilos` DECIMAL(25, 1) NOT NULL,
        `q_totalkilosb` DECIMAL(25, 1) NOT NULL,
        `q_vunitario` DECIMAL(25, 1) NOT NULL,
        `q_valortotal` DECIMAL(25, 1) NOT NULL,
        `q_valortotalb` DECIMAL(25, 1) NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `bodegas`(
        `k_bodega` BIGINT UNIQUE NOT NULL auto_increment,
        `n_nombre` VARCHAR(75) NOT NULL,
        `k_users` BIGINT NOT NULL,
        `b_active` BOOLEAN NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `pedidos_bodegas`(
        `k_venta_bodegas` BIGINT UNIQUE NOT NULL auto_increment,
        `k_bodega` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `f_venta` DATE NOT NULL,
        `f_venta_despachado` DATE,
        `n_estadop0` VARCHAR(20) NOT NULL,
        `n_observaciones` VARCHAR(255) NOT NULL,
        `b_active` BOOLEAN NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `venta_bodegas`(
        `k_venta_bodegas` BIGINT NOT NULL,
        `k_bodega` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `k_productos` VARCHAR(50) NOT NULL,
        `q_cantidad` SMALLINT NOT NULL,
        `q_totalkilos` DECIMAL(25, 1) NOT NULL,
        `n_categoria` VARCHAR(14) NOT NULL,
        `q_cantidad_despachada` SMALLINT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `vendedor_listaprecios` (
        `k_users` BIGINT NOT NULL,
        `k_listaprecios` INT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `vendedor_listaprecios_bodegas` (
        `k_users` BIGINT NOT NULL,
        `k_listaprecios` INT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `namelp` (
        `k_listaprecios` BIGINT NOT NULL,
        `n_nombre` VARCHAR(50) NOT NULL,
        `n_marca` VARCHAR(50) NOT NULL,
        `n_link` LONGTEXT,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `listaprecios` (
        `k_listaprecios` BIGINT NOT NULL,
        `k_marca` VARCHAR(15) NOT NULL,
        `k_productos` VARCHAR(70) NOT NULL,
        `q_valorunit` BIGINT NOT NULL,
        `q_cantkilos` DECIMAL(25, 1) NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `namelp_bodegas` (
        `k_listaprecios` BIGINT NOT NULL,
        `n_nombre` VARCHAR(50) NOT NULL,
        `n_marca` VARCHAR(50) NOT NULL,
        `n_link` LONGTEXT,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `listaprecios_bodegas` (
        `k_listaprecios` BIGINT NOT NULL,
        `k_marca` VARCHAR(15) NOT NULL,
        `k_productos` VARCHAR(70) NOT NULL,
        `q_cantkilos` DECIMAL(25, 1) NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `agenda` (
        `k_users` BIGINT NOT NULL,
        `k_cliente` BIGINT NOT NULL,
        `n_cliente` VARCHAR (100) NOT NULL,
        `n_notas` TEXT,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `pedidos_borrados`(
        `k_venta` BIGINT UNIQUE NOT NULL,
        `k_cliente` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `f_venta_borrado` DATE NOT NULL,
        `n_observaciones` VARCHAR(255) NOT NULL,
        `q_user_deleting` BIGINT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `clientes_favoritos`(
        `k_cliente` BIGINT NOT NULL,
        `k_users` BIGINT NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

CREATE TABLE
    `claims`(
        `k_claim` BIGINT UNIQUE NOT NULL,
        `k_users` BIGINT NOT NULL,
        `n_title` VARCHAR(30) NOT NULL,
        `q_relevance` BIGINT NOT NULL,
        `n_claim` LONGTEXT NOT NULL,
        `n_status` LONGTEXT NOT NULL,
        `b_active` BOOLEAN NOT NULL,
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

/* PRIMARY KEYS */

ALTER TABLE `users`
ADD
    CONSTRAINT `PK_k_users` PRIMARY KEY (k_users);

ALTER TABLE `clients`
ADD
    CONSTRAINT `PK_k_cliente` PRIMARY KEY (k_cliente);

ALTER TABLE `update_password`
ADD
    CONSTRAINT `PK_k_users` PRIMARY KEY (k_users);

ALTER TABLE `token_blocklist`
ADD
    CONSTRAINT `PK_k_token` PRIMARY KEY (k_token);

ALTER TABLE `zona` ADD CONSTRAINT `PK_k_zona` PRIMARY KEY (k_zona);

ALTER TABLE `departamento`
ADD
    CONSTRAINT `PK_k_departamento` PRIMARY KEY (k_departamento);

ALTER TABLE `pedidos_borrados`
ADD
    CONSTRAINT `PK_k_users` PRIMARY KEY (k_venta);

/* ALTER TABLE `pedidos` ADD CONSTRAINT `PK_k_venta` PRIMARY KEY (k_venta); */

ALTER TABLE `namelp`
ADD
    CONSTRAINT `PK_k_listaprecios` PRIMARY KEY (k_listaprecios);

/* CHECKS */

ALTER TABLE `claims`
ADD
    CONSTRAINT `CK_n_status` CHECK (
        n_status in ('No revisado', 'Revisado')
    );

ALTER TABLE `users`
ADD
    CONSTRAINT `CK_n_categoria` CHECK (
        n_categoria in (
            'CEO',
            'Admin',
            'Vendedor',
            'Facturador',
            'Despachador'
        )
    );

ALTER TABLE `users` ADD CONSTRAINT `CK_k_users` CHECK (k_users > 0);

ALTER TABLE `pedidos`
ADD
    CONSTRAINT `CK_n_estadop0` CHECK (
        n_estadop0 in ('No autorizado', 'Autorizado')
    );

ALTER TABLE `pedidos`
ADD
    CONSTRAINT `CK_n_estadop1` CHECK (
        n_estadop1 in ('Por facturar', 'Facturado')
    );

ALTER TABLE `pedidos`
ADD
    CONSTRAINT `CK_n_estadop2` CHECK (
        n_estadop2 in (
            'Por despachar',
            'Despachado',
            'Incompleto'
        )
    );

ALTER TABLE `venta`
ADD
    CONSTRAINT `CK_v_n_categoria` CHECK (
        n_categoria in (
            'Por despachar',
            'Despachado',
            'Incompleto'
        )
    );

ALTER TABLE `venta_bodegas`
ADD
    CONSTRAINT `CK_pb_n_categoria` CHECK (
        n_categoria in (
            'Por despachar',
            'Despachado',
            'Incompleto'
        )
    );

ALTER TABLE `pedidos_bodegas`
ADD
    CONSTRAINT `CK_pb_n_estadop0` CHECK (
        n_estadop0 in (
            'Por despachar',
            'Despachado',
            'Incompleto'
        )
    );

ALTER TABLE `listaprecios`
ADD
    CONSTRAINT `CK_k_listaprecios` CHECK (k_listaprecios > 0);

SET FOREIGN_KEY_CHECKS=1;

/*ALTER TABLE pedidos_borrados ADD q_user_deleting BIGINT NOT NULL;*/

/*ALTER TABLE namelp ADD COLUMN n_link LONGTEXT AFTER n_marca;*/

/*ALTER TABLE zona MODIFY `n_zona` LONGTEXT;*/

/*ALTER TABLE users ADD FULLTEXT (n_nombre);*/