USE ud_pg;

/* idzona - nombrezona */
INSERT INTO zona VALUES (5,'Boyacá');
INSERT INTO zona VALUES (11,'Cundinamarca');
INSERT INTO zona VALUES (17,'Odilia Campos Perdomo');
INSERT INTO zona VALUES (3,'Lidia Aurora Chacón');
INSERT INTO zona VALUES (13,'Meta Casanare');
INSERT INTO zona VALUES (2,'Caquetá');
INSERT INTO zona VALUES (4,'La Dorada');
INSERT INTO zona VALUES (26,'Juan Manuel Villamil');
INSERT INTO zona VALUES (14,'Fabrica Pasto');
INSERT INTO zona VALUES (8,'Tolima');
INSERT INTO zona VALUES (16,'Cali-Rubiel');
INSERT INTO zona VALUES (35,'Eje Cafetero y Magdalena');
INSERT INTO zona VALUES (6,'Medellín');
INSERT INTO zona VALUES (1,'Fábrica');
INSERT INTO zona VALUES (9,'Santander-Efraín');
INSERT INTO zona VALUES (24,'Putumayo');
INSERT INTO zona VALUES (21,'Carlos Mario Reyes Martinez');

/* idzona - iddepartamento - idvendedor */
/*Zona: Boyacá*/
INSERT INTO zona_vendedor VALUES(5, 11);
INSERT INTO zona_departamento VALUES (5,'Byca');
INSERT INTO zona_departamento VALUES (5,'Stdr');

/*Zona: Cundinamarca*/
INSERT INTO zona_vendedor VALUES(11, 22);
INSERT INTO zona_departamento VALUES (11,'Cund');
INSERT INTO zona_departamento VALUES (11,'Tol');

/*Zona: Odilia Campos Perdomo*/
INSERT INTO zona_vendedor VALUES(17, 33);
INSERT INTO zona_departamento VALUES (17,'Hul');
INSERT INTO zona_departamento VALUES (17,'Cqta');

/*Zona: Lidia Aurora Chacón*/
INSERT INTO zona_vendedor VALUES(3, 44);
INSERT INTO zona_departamento VALUES (3,'Bgta');
INSERT INTO zona_departamento VALUES (3,'Mta');
INSERT INTO zona_departamento VALUES (3,'Byca');

/*Zona: Meta Casanare*/
INSERT INTO zona_vendedor VALUES(13, 55);
INSERT INTO zona_departamento VALUES (13,'Mta');
INSERT INTO zona_departamento VALUES (13,'Csnre');
INSERT INTO zona_departamento VALUES (13,'Gvre');
INSERT INTO zona_departamento VALUES (13,'Cund');

/*Zona: Caquetá*/
INSERT INTO zona_vendedor VALUES(2, 66);
INSERT INTO zona_departamento VALUES (2,'Cqta');

/*Zona: La Dorada*/
INSERT INTO zona_vendedor VALUES(4, 77);
INSERT INTO zona_departamento VALUES (4,'Cal');

/*Zona: Juan Manuel Villamil */
INSERT INTO zona_vendedor VALUES(26, 88);
INSERT INTO zona_departamento VALUES (26,'Cauc');
INSERT INTO zona_departamento VALUES (26,'Vcauc');

/*Zona: Fabrica Pasto*/
INSERT INTO zona_vendedor VALUES(14, 99);
INSERT INTO zona_departamento VALUES (14,'Nrño');

/*Zona: Tolima*/
INSERT INTO zona_vendedor VALUES(8, 111);
INSERT INTO zona_departamento VALUES (8,'Tol');
INSERT INTO zona_departamento VALUES (8,'Cund');

/*Zona: Cali-Rubiel*/
INSERT INTO zona_vendedor VALUES(16, 112);
INSERT INTO zona_departamento VALUES (16,'Vcauc');

/*Zona: Eje Cafetero y Magdalena*/
INSERT INTO zona_vendedor VALUES(35, 113);
INSERT INTO zona_departamento VALUES (35,'Cal');
INSERT INTO zona_departamento VALUES (35,'Qdio');
INSERT INTO zona_departamento VALUES (35,'Rslda');
INSERT INTO zona_departamento VALUES (35,'Byca');

/*Zona: Medellin*/
INSERT INTO zona_vendedor VALUES(6, 222);
INSERT INTO zona_departamento VALUES (6,'Antq');

/*Zona: Fabrica*/
INSERT INTO zona_vendedor VALUES (1,333);
INSERT INTO zona_departamento VALUES(1,'Sel');
INSERT INTO zona_departamento VALUES (1,'Bgta');
INSERT INTO zona_departamento VALUES (1,'Cal');
INSERT INTO zona_departamento VALUES (1,'Vcauc');
INSERT INTO zona_departamento VALUES (1,'Stdr');
INSERT INTO zona_departamento VALUES (1,'Qdio');
INSERT INTO zona_departamento VALUES (1,'Rslda');
INSERT INTO zona_departamento VALUES (1,'Ptyo');
INSERT INTO zona_departamento VALUES (1,'Hul');
INSERT INTO zona_departamento VALUES (1,'Cqta');
INSERT INTO zona_departamento VALUES (1,'Byca');
INSERT INTO zona_departamento VALUES (1,'Cund');
INSERT INTO zona_departamento VALUES (1,'Tol');
INSERT INTO zona_departamento VALUES (1,'Mta');
INSERT INTO zona_departamento VALUES (1,'Csnre');
INSERT INTO zona_departamento VALUES (1,'Cauc');
INSERT INTO zona_departamento VALUES (1,'Nrño');
INSERT INTO zona_departamento VALUES (1,'Antq');
INSERT INTO zona_departamento VALUES (1,'Csr');
INSERT INTO zona_departamento VALUES (1,'Arc');
INSERT INTO zona_departamento VALUES (1,'Nstdr');
INSERT INTO zona_departamento VALUES (1,'Blvr');
INSERT INTO zona_departamento VALUES (1,'Gvre');

/*Zona: Santander -Efraín*/
INSERT INTO zona_vendedor VALUES (9,444);
INSERT INTO zona_departamento VALUES (9,'Stdr');
INSERT INTO zona_departamento VALUES (9,'Csr');
INSERT INTO zona_departamento VALUES (9,'Arc');
INSERT INTO zona_departamento VALUES (9,'Nstdr');
INSERT INTO zona_departamento VALUES (9,'Blvr');

/*Zona: Putumayo*/
INSERT INTO zona_vendedor VALUES (24,555);
INSERT INTO zona_departamento VALUES (24,'Ptyo');

/*Zona: Carlos Mario Reyes Martinez*/
INSERT INTO zona_vendedor VALUES (21,666);
INSERT INTO zona_departamento VALUES (21,'Cund');
INSERT INTO zona_departamento VALUES (21,'Bgta');