from flask_mysqldb import MySQL
import mysql.connector

# Herramientas
import json
from functools import reduce

# Manejo de fechas
import datetime
import calendar
from datetime import timedelta

# Decouple
from decouple import config

class Database():
    def __init__(self, app):
        '''
        Configuración de la base de datos MySQL
        '''
        print('Inicializando base de datos...')

        self.controller = None

        self.app = app

        # Config session
        self.app.config['MYSQL_USER'] = config('USER')
        self.app.config['MYSQL_HOST'] = config('HOST')
        self.app.config['MYSQL_PASSWORD'] = config('PASSWD')
        self.app.config['MYSQL_DB'] = config('DATABASE')
        self.app.config['MYSQL_CONNECT_TIMEOUT'] = 60
        
        self.mysql = MySQL(self.app)

    def set_controller(self, controller):
        self.controller = controller


    #Config Access
    def login_database(self) -> 'mysql.connector.cursor':
        '''
        Iniciamos una conexion a la base de datos.
        '''
        try:
            print('login_database')
            return self.mysql.connection.cursor()
        except mysql.connector.Error as error:
            print('Login database Error: ' + str(error))

    # SELECTS
    def consultar_presupuestos_vendedor(self, id_vendedor):
        '''
        Consulta los presupuestos de un vendedor
        Args:
            id_vendedor (int): Id del vendedor
        '''
        try:
            ncursor = self.login_database()
            # 1. Verificar todas las zonas del vendedor
            query = """
            SELECT k_zona FROM zona_vendedor
            WHERE k_users = %s;
            """
            ncursor.execute(query, (id_vendedor, ))
            zonas = ncursor.fetchall()
            # 2. Consultar y añadir al array los presupuestos de cada zona
            ncursor.execute("SET lc_time_names = 'es_ES';")
            presupuestos_zonas = []
            query = """SELECT JSON_OBJECT(
                'idZona', k_zona,
                'nameZona', n_zona
            ) FROM zona WHERE k_zona = %s AND b_active = 1;"""
            for zona in zonas:
                # 3. Consultar información de la zona
                ncursor.execute(query, (zona[0], ))
                info_zona = ncursor.fetchone()
                query_zona = """
                SELECT MONTHNAME(STR_TO_DATE(q_mes,'%%m')), FORMAT(q_presupuesto, 0, 'de_DE') FROM presupuesto_zonas, zona_vendedor
                WHERE presupuesto_zonas.k_zona = zona_vendedor.k_zona
                AND k_users = %s
                AND presupuesto_zonas.k_zona = %s;
                """
                ncursor.execute(query_zona, (id_vendedor, zona[0], ))
                presupuestos = ncursor.fetchall()
                presupuestos_zonas.append({
                    "zona": json.loads(info_zona[0]),
                    "presupuestos": presupuestos
                })
            return [presupuestos_zonas, True]
        except mysql.connector.Error as error:
            print('Error consultar_presupuestos_vendedor: ' + str(error))
            return [[], False]

    def analizar_pedido(self, id_pedido, info_pedido):
        '''
        Dado un pedido, consigue el pedido anterior a ese del mismo cliente
        analiza y compara los productos de ambos, y de acuerdo con la información
        del producto que se esta despachando, si hay coincidencia conm el pedido
        anterior devuelve un truthy.
        '''
        try:
            ncursor = self.login_database()
            query = """
            SELECT k_venta FROM pedidos WHERE k_cliente = (
                SELECT k_cliente FROM pedidos WHERE k_venta = %s
            ) AND k_venta < %s 
            AND f_venta_facturado IS NOT NULL 
            AND b_active = 1
            AND (
                n_estadop2 = 'Por despachar' OR
                n_estadop2 = 'Incompleto'
            )
            ORDER BY k_venta DESC LIMIT 1;
            """
            ncursor.execute(query, (id_pedido, id_pedido, ))
            pedido_anterior = ncursor.fetchone()
            if pedido_anterior:
                query = """
                SELECT k_productos, q_cantidad_despachada
                FROM venta
                WHERE k_venta = %s
                AND k_productos IN (SELECT k_productos FROM venta WHERE k_venta = %s);
                AND (
                    n_categoria = 'Por despachar' OR
                    n_categoria = 'Incompleto'
                );
                """
                ncursor.execute(query, (pedido_anterior[0], id_pedido, ))
                productos_pedido_anterior = ncursor.fetchall() # Productos en común con el pedido anterior
                if productos_pedido_anterior:
                    return [
                    True,
                    productos_pedido_anterior, 
                    f"Se detectaron ({len(productos_pedido_anterior)}) producto(s) en común faltos por despachar en el pedido anterior #({pedido_anterior[0]}) de este cliente. ¿Desea actualizar el estado de estos productos a 'Despachado'?",
                    pedido_anterior[0]
                    ]
            return [False, [], 'No se detectaron productos en común faltos por despachar.', None]
        except mysql.connector.Error as error:
            print('Error analizar_pedido: ' + str(error))
            return [False, [], 'Error analizando el pedido.', None]
        
    def consultar_reclamaciones(self, category, filter, limit, offset):
        '''
        Consulta todas las reclamaciones
        Args:
            - category: str
            - filter: str
            - limit: int
            - offset: int
        '''
        try:
            ncursor = self.login_database()
            # Total claims
            if filter:
                query = """
                SELECT COUNT(k_claim)
                FROM users, claims
                WHERE users.k_users = claims.k_users
                AND claims.b_active = 1
                AND n_status = %s
                AND (
                    LOWER(REPLACE(CONCAT(users.n_nombre, " ", users.n_apellido), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                    LOWER(REPLACE(n_title, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                )
                ORDER BY q_relevance DESC, claims.created_at DESC, k_claim DESC;
                """
            else:
                query = """
                SELECT COUNT(k_claim)
                FROM users, claims
                WHERE users.k_users = claims.k_users
                AND claims.b_active = 1
                AND n_status = %s
                ORDER BY q_relevance DESC, claims.created_at DESC, k_claim DESC;
                """
            ncursor.execute(query, (category, '%' + filter + '%', '%' + filter + '%', ) if filter else (category, ))
            total_claims = ncursor.fetchone()[0]
            if filter:
                query = """
                SELECT k_claim, CONCAT(users.n_nombre, " ", users.n_apellido),
                n_title, 
                CASE 
                    WHEN q_relevance = 1 THEN 'Baja'
                    WHEN q_relevance = 2 THEN 'Normal'
                    WHEN q_relevance = 3 THEN 'Alta'
                END AS relevance,
                DATE_FORMAT(claims.created_at,"%%e/%%m/%%Y")
                FROM users, claims
                WHERE users.k_users = claims.k_users
                AND claims.b_active = 1
                AND n_status = %s
                AND (
                    LOWER(REPLACE(CONCAT(users.n_nombre, " ", users.n_apellido), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                    LOWER(REPLACE(n_title, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                )
                ORDER BY q_relevance DESC, claims.created_at DESC, k_claim DESC
                LIMIT %s OFFSET %s;
                """
            else:
                query = """
                SELECT k_claim, CONCAT(users.n_nombre, " ", users.n_apellido),
                n_title, 
                CASE 
                    WHEN q_relevance = 1 THEN 'Baja'
                    WHEN q_relevance = 2 THEN 'Normal'
                    WHEN q_relevance = 3 THEN 'Alta'
                END AS relevance,
                DATE_FORMAT(claims.created_at,"%%e/%%m/%%Y")
                FROM users, claims
                WHERE users.k_users = claims.k_users
                AND claims.b_active = 1
                AND n_status = %s
                ORDER BY q_relevance DESC, claims.created_at DESC, k_claim DESC
                LIMIT %s OFFSET %s;
                """
            ncursor.execute(query, (category, '%' + filter + '%', '%' + filter + '%', limit, offset, ) if filter else (category, limit, offset, ))
            claims = ncursor.fetchall()
            return [total_claims, claims, True]
        except mysql.connector.Error as error:
            print('Error: ' + str(error))
            return [0, [], False]
            


    def consultar_reclamacion(self, id_reclamacion):
        '''
        Consulta una reclamación en la base de datos
        '''
        try:
            ncursor = self.login_database()
            query = """
            SELECT JSON_OBJECT(
                'id', k_claim,
                'idUser', claims.k_users,
                'nameUser', CONCAT(users.n_nombre, " ", users.n_apellido), 
                'title', n_title, 
                'relevance', q_relevance, 
                'claim', n_claim, 
                'status', n_status, 
                'date', DATE_FORMAT(claims.created_at,"%%e/%%m/%%Y")
            )
            FROM claims, users
            WHERE claims.k_users = users.k_users
            AND k_claim = %s;
            """
            ncursor.execute(query, (id_reclamacion,))
            claim = ncursor.fetchone()
            return [json.loads(claim[0]), True] if claim else [None, False]
        except mysql.connector.Error as error:
            print('Error: ' + str(error))
            return [None, False]


    def consultar_reclamaciones_vendedor(self, id_vendedor, filter, category, limit, offset):
        '''
        Consulta todas las reclamaciones registradas por un vendedor
        '''
        try:
            ncursor = self.login_database()
            # Total claims
            if filter:
                query = """
                SELECT COUNT(k_claim)
                FROM claims
                WHERE k_users = %s
                AND n_status = %s
                AND b_active = 1
                AND LOWER(REPLACE(n_title, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                """
            else:
                query = """
                SELECT COUNT(k_claim)
                FROM claims
                WHERE k_users = %s
                AND n_status = %s
                AND b_active = 1
                """
            ncursor.execute(query, (id_vendedor, category, '%' + filter + '%', ) if filter else (id_vendedor, category, ))
            total_claims = ncursor.fetchone()[0]
            if filter:
                query = """
                SELECT k_claim,
                n_title,
                CASE 
                    WHEN q_relevance = 1 THEN 'Baja'
                    WHEN q_relevance = 2 THEN 'Normal'
                    WHEN q_relevance = 3 THEN 'Alta'
                END AS relevance,
                DATE_FORMAT(claims.created_at, "%%e/%%m/%%Y")
                FROM claims, users
                WHERE claims.k_users = users.k_users
                AND claims.k_users = %s
                AND n_status = %s
                AND claims.b_active = 1
                AND LOWER(REPLACE(n_title, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                ORDER BY q_relevance DESC, claims.created_at DESC, k_claim DESC
                LIMIT %s OFFSET %s;
                """
            else:
                query = """
                SELECT k_claim,
                n_title,
                CASE 
                    WHEN q_relevance = 1 THEN 'Baja'
                    WHEN q_relevance = 2 THEN 'Normal'
                    WHEN q_relevance = 3 THEN 'Alta'
                END AS relevance,
                DATE_FORMAT(claims.created_at, "%%e/%%m/%%Y")
                FROM claims, users
                WHERE claims.k_users = users.k_users
                AND claims.k_users = %s
                AND n_status = %s
                AND claims.b_active = 1
                ORDER BY q_relevance DESC, claims.created_at DESC, k_claim DESC
                LIMIT %s OFFSET %s;
                """
            ncursor.execute(query, (id_vendedor, category, '%' + filter + '%', limit, offset, ) if filter else (id_vendedor, category, limit, offset, ))
            claims = ncursor.fetchall()
            return [total_claims, claims, True] if claims else [0, [], False]
        except mysql.connector.Error as error:
            print('consultar_reclamaciones_vendedor Error: ' + str(error))
            return [0, [], False]

    def consultar_zonas_vendedor(self, id_user):
        '''
        Consulta todas las zonas asociadas a un vendedor
        Args:
            - id_user: id del usuario int
        '''
        try:
            ncursor = self.login_database()
            query = """
            SELECT JSON_OBJECT(
                'id', zona.k_zona,
                'name', n_zona
            ) FROM zona_vendedor, zona WHERE zona_vendedor.k_zona = zona.k_zona
            AND k_users = %s;
            """
            ncursor.execute(query, (id_user, ))
            zonas = ncursor.fetchall()
            return [zonas, True] if zonas else [[], False]
        except mysql.connector.Error as error:
            print('consultar_zonas_vendedor Error: ' + str(error))
            return [[], False]
        

    def consultar_presupuesto_zona(self, id_zona):
        '''
        Consulta el presupuesto de una zona en un mes
        '''
        try:
            ncursor = self.login_database()
            ncursor.execute("SET lc_time_names = 'es_ES';")
            query = """SELECT q_mes, q_presupuesto FROM presupuesto_zonas WHERE k_zona = %s"""
            ncursor.execute(query, (id_zona, ))
            presupuesto = ncursor.fetchall()
            return [presupuesto, True] if presupuesto else [[], False]
        except mysql.connector.Error as error:
            print('consultar_presupuesto_zona Error: ' + str(error))
            return [[], False]

    def consultar_resumen_exportacion(self, config, advanced_config):
        '''
        Consulta el registro de pedidos y ventas segundo la configuración
        establecida
        Args:
            config: {type: "pedidos" | "bodegas"; fileExtension: "xlsx" | "csv"; date: "todos" | number;category}
            advanced_config: string[] de atributos
        '''
        try:
            ncursor = self.login_database()
            if config['type'] == "bodegas":
                query = """SELECT pedidos_bodegas.k_venta_bodegas, pedidos_bodegas.k_bodega"""
                for config_option in advanced_config:
                    if config_option == 'ID Vendedor': # 2
                        query += ', pedidos_bodegas.k_users'
                    elif config_option == 'Nombre vendedor': # 4
                        query += ', CONCAT(users.n_nombre, " ", users.n_apellido)'  
                    elif config_option == 'Fecha pedido': # 5
                        query += ', DATE_FORMAT(pedidos_bodegas.f_venta,"%e/%m/%Y")'
                    elif config_option == 'Fecha despachado': # 8
                        query += ', DATE_FORMAT(pedidos_bodegas.f_venta_despachado,"%e/%m/%Y")'
                    elif config_option == 'Estado 0': # 9
                        query += ', pedidos_bodegas.n_estadop0'
                    elif config_option == 'Observaciones': # 12
                        query += ', pedidos_bodegas.n_observaciones'
                    elif config_option == 'Producto': # 13
                        query += ', k_productos'
                    elif config_option == 'Cantidad': # 14
                        query += ', q_cantidad'
                    elif config_option == 'Total kg': # 16
                        query += ', q_totalkilos'
                    elif config_option == 'Cantidad despachada': # 21
                        query += ', q_cantidad_despachada'
                    elif config_option == 'Estado 0 producto': # 22
                        query += ', venta_bodegas.n_categoria'
                query += """
                FROM pedidos_bodegas, venta_bodegas, users
                WHERE pedidos_bodegas.k_venta_bodegas = venta_bodegas.k_venta_bodegas
                AND pedidos_bodegas.k_users = users.k_users
                """
                if config['date'] != "todos":
                    query += """AND DATE_FORMAT(pedidos_bodegas.f_venta,"%%Y") = %s """ % int(config['date'])
                if config['category'] != "todos":
                    if config['category'] == "Por despachar":
                        query += """AND pedidos_bodegas.n_estadop0 = 'Por despachar' AND pedidos_bodegas.b_active = 1"""
                    elif config['category'] == "Despachados":
                        query += """AND pedidos_bodegas.n_estadop0 = 'Despachado' AND pedidos_bodegas.b_active = 1 ORDER BY pedidos_bodegas.k_venta_bodegas DESC"""
                    elif config['category'] == "Incompletos":
                        query += """AND pedidos_bodegas.n_estadop0 = 'Incompleto' AND pedidos_bodegas.b_active = 1 ORDER BY pedidos_bodegas.k_venta_bodegas DESC"""
                    elif config['category'] == "Eliminados":
                        query += """AND pedidos_bodegas.b_active = 0 ORDER BY pedidos_bodegas.k_venta_bodegas DESC"""
                else:
                    query += """AND pedidos_bodegas.b_active = 1 ORDER BY pedidos_bodegas.k_venta_bodegas DESC"""
                ncursor.execute(query)
                result = ncursor.fetchall()
                return [result, True]
            else:
                query = """SELECT pedidos.k_venta"""
                for config_option in advanced_config:
                    if config_option == 'ID Cliente': # 1
                        query += ', pedidos.k_cliente'
                    elif config_option == 'ID Vendedor': # 2
                        query += ', pedidos.k_users'
                    elif config_option == 'Nombre cliente': # 3
                        query += ', clients.n_cliente'
                    elif config_option == 'Nombre vendedor': # 4
                        query += ', CONCAT(users.n_nombre, " ", users.n_apellido)'
                    elif config_option == 'Nombre zona': # 5
                        query += ', n_zona'  
                    elif config_option == 'Fecha pedido': # 5
                        query += ", DATE_FORMAT(pedidos.f_venta,'%e/%m/%Y')"
                    elif config_option == 'Fecha autorizado': # 6
                        query += ", DATE_FORMAT(pedidos.f_venta_autorizado,'%e/%m/%Y')"
                    elif config_option == 'Fecha facturado': # 7
                        query += ", DATE_FORMAT(pedidos.f_venta_facturado,'%e/%m/%Y')"
                    elif config_option == 'Fecha despachado': # 8
                        query += ", DATE_FORMAT(pedidos.f_venta_despachado,'%e/%m/%Y')"
                    elif config_option == 'Estado 0': # 9
                        query += ', pedidos.n_estadop0'
                    elif config_option == 'Estado 1': # 10
                        query += ', pedidos.n_estadop1'
                    elif config_option == 'Estado 2':   # 11
                        query += ', pedidos.n_estadop2'
                    elif config_option == 'Observaciones': # 12
                        query += ', pedidos.n_observaciones'
                    elif config_option == 'Producto': # 13
                        query += ', k_productos'
                    elif config_option == 'Cantidad': # 14
                        query += ', q_cantidad'
                    elif config_option == 'Cantidad bonificada': # 15
                        query += ', q_bonificacion'
                    elif config_option == 'Total kg': # 16
                        query += ', q_totalkilos'
                    elif config_option == 'Total kg bonificado': # 17
                        query += ', q_totalkilosb'
                    elif config_option == 'Valor unitario': # 18
                        query += ', q_vunitario'
                    elif config_option == 'Valor total': # 19
                        query += ', q_valortotal'
                    elif config_option == 'Valor total bonificado': # 20
                        query += ', q_valortotalb'
                    elif config_option == 'Cantidad despachada': # 21
                        query += ', q_cantidad_despachada'
                    elif config_option == 'Estado 0 producto': # 22
                        query += ', venta.n_categoria'
                query += """
                FROM pedidos, venta, users, clients, zona
                WHERE pedidos.k_venta = venta.k_venta
                AND pedidos.k_users = users.k_users
                AND pedidos.k_cliente = clients.k_cliente
                AND clients.k_zona = zona.k_zona
                """
                if config['date'] != "todos":
                    query += """AND DATE_FORMAT(pedidos.f_venta,"%%Y") = %s """ % int(config['date'])
                if config['category'] != "todos":
                    if config['category'] == "No autorizados":
                        query += """AND pedidos.n_estadop0 = 'No autorizado' AND pedidos.b_active = 1"""
                    elif config['category'] == "Autorizados":
                        query += """AND pedidos.n_estadop0 = 'Autorizado' AND pedidos.n_estadop1 = 'Por facturar' AND pedidos.b_active = 1 ORDER BY pedidos.k_venta DESC"""
                    elif config['category'] == "Por despachar":
                        query += """AND pedidos.n_estadop0 = 'Autorizado' AND pedidos.n_estadop1 = 'Facturado' AND pedidos.n_estadop2 = 'Por despachar' AND pedidos.b_active = 1 ORDER BY pedidos.k_venta DESC"""
                    elif config['category'] == "Despachados":
                        query += """AND pedidos.n_estadop0 = 'Autorizado' AND pedidos.n_estadop1 = 'Facturado' AND pedidos.n_estadop2 = 'Despachado' AND pedidos.b_active = 1 ORDER BY pedidos.k_venta DESC"""
                    elif config['category'] == "Incompletos":
                        query += """AND pedidos.n_estadop0 = 'Autorizado' AND pedidos.n_estadop1 = 'Facturado' AND pedidos.n_estadop2 = 'Incompleto' AND pedidos.b_active = 1 ORDER BY pedidos.k_venta DESC"""
                    elif config['category'] == "Eliminados":
                        query += """AND pedidos.b_active = 0 ORDER BY pedidos.k_venta DESC"""
                else:
                    query += """AND pedidos.b_active = 1 ORDER BY pedidos.k_venta DESC"""
                ncursor.execute(query)
                result = ncursor.fetchall()
                return [result, True]
        except mysql.connector.Error as error:
            print('Consultar solicitud contraseña Error: '+str(error))
            return ['Falló la descarga de extracción de datos', False]

    def consultar_solicitud_contraseña(self, id):
        '''
        Consulta la información específica de una solicitud de cambio de contraseña
        Args:
            id: cedula 
        '''
        try:
            ncursor = self.login_database()
            query = "SELECT * FROM update_password WHERE k_users = %s"
            ncursor.execute(query, (id, ))
            result = ncursor.fetchone()
            if result:
                return [result,True]
            return ['Usuario no encontrado', False]
        except mysql.connector.Error as error:
            print('Consultar solicitud contraseña Error: '+str(error))
            return ['Falló la consulta de solicitud de contraseña', False]

    def consultar_pedidos_recientes(self, category):
        '''
        Consulta los pedidos recientes dada una categoria
        Args:
            category: "" | "CEO" | "Admin" | "Facturador" | "Vendedor" | "Despachador"
        '''
        try:
            print('consultar_pedidos_recientes')
            cinco_dias_atras = datetime.datetime.now() - timedelta(days=5)
            hoy = datetime.datetime.now()

            ncursor = self.login_database()
            if category == "Facturador":
                query = """
                SELECT k_venta, n_cliente, CONCAT(users.n_nombre, " ", users.n_apellido),
                DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_autorizado,'%%e/%%m/%%Y'), 
                DATE_FORMAT(f_venta_facturado,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'),
                n_estadop0, n_estadop1, n_estadop2
                FROM pedidos, clients, users
                WHERE pedidos.k_cliente = clients.k_cliente
                AND pedidos.k_users = users.k_users
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Por facturar"
                AND pedidos.n_estadop2 = "Por despachar"
                AND pedidos.f_venta_autorizado BETWEEN %s AND %s
                AND pedidos.b_active = 1
                ORDER BY k_venta DESC LIMIT 5 OFFSET 0;
                """
                ncursor.execute(query, (cinco_dias_atras, hoy))
            elif category == "Despachador":
                query = """
                SELECT k_venta, n_cliente, CONCAT(users.n_nombre, " ", users.n_apellido),
                DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_autorizado,'%%e/%%m/%%Y'), 
                DATE_FORMAT(f_venta_facturado,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'),
                n_estadop0, n_estadop1, n_estadop2
                FROM pedidos, clients, users
                WHERE pedidos.k_cliente = clients.k_cliente
                AND pedidos.k_users = users.k_users
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Facturado"
                AND pedidos.n_estadop2 = "Por despachar"
                AND pedidos.f_venta_facturado BETWEEN %s AND %s
                AND pedidos.b_active = 1
                ORDER BY k_venta DESC LIMIT 5 OFFSET 0;
                """
                ncursor.execute(query, (cinco_dias_atras, hoy))
            elif category == "Admin":
                query = """
                SELECT k_venta, n_cliente, CONCAT(users.n_nombre, " ", users.n_apellido),
                DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_autorizado,'%%e/%%m/%%Y'), 
                DATE_FORMAT(f_venta_facturado,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'),
                n_estadop0, n_estadop1, n_estadop2
                FROM pedidos, clients, users
                WHERE pedidos.k_cliente = clients.k_cliente
                AND pedidos.k_users = users.k_users
                AND pedidos.n_estadop0 = "No autorizado"
                AND pedidos.n_estadop1 = "Por facturar"
                AND pedidos.n_estadop2 = "Por despachar"
                AND pedidos.f_venta BETWEEN %s AND %s
                AND pedidos.b_active = 1
                ORDER BY k_venta DESC LIMIT 5 OFFSET 0;
                """
                ncursor.execute(query, (cinco_dias_atras, hoy))
            pedidos = ncursor.fetchall()
            return [pedidos, True] if pedidos else ['No hay pedidos recientes', False]
        except mysql.connector.Error as error:
            print('Consultar pedidos recientes Error: ' + str(error))
            return ['Falló la consulta de pedidos recientes.', False]

    def consultar_obs_cotizacion(self, id_cotizacion):
        '''
        Consulta:
            1.1. Observaciones de la cotización
        Args:
            id_cotizacion: int
        '''
        try:
            print("consultar_obs_cotizacion")
            ncursor = self.login_database()
            query = """
            SELECT n_observaciones FROM pedidos_cotizaciones WHERE k_venta_cotizacion = %s
            """
            ncursor.execute(query, (id_cotizacion,))
            obs = ncursor.fetchone()
            return [obs[0], True] if obs else ['La cotización no existe', False]
        except mysql.connector.Error as error:
            print('Consultar obs cotizacion Error: ' + str(error))
            return ['Falló la consulta de la cotización.', False]

    def consultar_cotizacion(self, id_cotizacion):
        '''
        Consulta:
            1.1. Información (cédula y nombre) del cliente de la cotización
            1.2. Información (cédula y nombre) del vendedor de la cotización
            1.3. Información (id y nombre) de la zona de la cotización

            2.1. Todo el registro de venta (Producto, Cnt, CntBnf, TKg, TKgBnf, VU, VT, VTBnf)
        '''
        try:
            print("consultar_cotizacion")
            ncursor = self.login_database()
            # 1. 1.1 & 1.2 & 1.3
            query = """
            SELECT JSON_OBJECT(
                'idClient', clients.k_cliente,
                'idSeller', users.k_users,
                'idZone', clients.k_zona, 
                'nameClient', clients.n_cliente, 
                'clientAddress', clients.n_direccion, 
                'clientPhone', clients.q_telefono, 
                'clientCity', clients.n_ciudad, 
                'clientDepartment', departamento.n_departamento, 
                'nameSeller', CONCAT(n_nombre, " ", n_apellido), 
                'nameZone', zona.n_zona, 
                'totalKg', FORMAT(SUM(q_totalkilos), 0, 'de_DE'),
                'totalPesos', FORMAT(SUM(q_valortotal), 0, 'de_DE'),
                'ivaBnf', FORMAT(SUM(q_valortotalb), 0, 'de_DE'),
                'totalKgBnf', FORMAT(SUM(q_totalkilosb), 0, 'de_DE'),
                'active', IF(pedidos_cotizaciones.b_active, 'true', 'false'),
                'iva', FORMAT((SUM(q_valortotal) + SUM(q_valortotalb)) * 0.05, 0, 'de_DE'),
                'total', FORMAT((SUM(q_valortotal) + SUM(q_valortotalb)) * 0.05 + (SUM(q_valortotal) + SUM(q_valortotalb)), 0, 'de_DE'),
                'date', DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), 
                'obs', pedidos_cotizaciones.n_observaciones
            )
            FROM pedidos_cotizaciones, clients, users, zona, departamento, venta_cotizaciones
            WHERE pedidos_cotizaciones.k_cliente = clients.k_cliente
            AND clients.k_departamento = departamento.k_departamento
            AND pedidos_cotizaciones.k_users = users.k_users
            AND clients.k_zona = zona.k_zona
            AND pedidos_cotizaciones.k_venta_cotizacion = venta_cotizaciones.k_venta_cotizacion
            AND pedidos_cotizaciones.k_venta_cotizacion = %s
            GROUP BY pedidos_cotizaciones.k_venta_cotizacion
            """
            ncursor.execute(query, (id_cotizacion,))
            info_cotizacion = ncursor.fetchone()
            # 2.1
            query = """
            SELECT k_productos, FORMAT(q_cantidad, 0, 'de_DE'), FORMAT(q_bonificacion, 0, 'de_DE'), 
            FORMAT(q_totalkilos, 0, 'de_DE'), FORMAT(q_totalkilosb, 0, 'de_DE'), 
            FORMAT(q_vunitario, 0, 'de_DE'), FORMAT(q_valortotal, 0, 'de_DE'), 
            FORMAT(q_valortotalb, 0, 'de_DE'),
            k_listaprecios
            FROM venta_cotizaciones
            WHERE k_venta_cotizacion = %s"""
            ncursor.execute(query, (id_cotizacion,))
            cotizacion = ncursor.fetchall()
            return [info_cotizacion, cotizacion, True] if cotizacion else ['La cotización no existe', cotizacion, False]
        except mysql.connector.Error as error:
            print('Consultar cotización Error: ' +str(error))
            return ['Falló la consulta de la cotización.', False]

    def consultar_nota_agenda(self, id_cliente, id_vendedor):
        '''
        Consulta la nota de un cliente en la agenda de un vendedor
        Args:
            - id_cliente: int
            - id_vendedor: int
        '''
        try:
            print("consultar_nota_agenda")
            ncursor = self.login_database()
            query = "SELECT n_notas FROM agenda WHERE k_cliente = %s AND k_users = %s"
            ncursor.execute(query, (id_cliente, id_vendedor))
            nota = ncursor.fetchone()
            return [nota, True] if nota else ['El cliente no registra notas', False]
        except mysql.connector.Error as error:
            print('Consultar nota agenda Error: ' +str(error))
            return ['Falló la consulta de nota de agenda.', False]

    def consultar_agenda_cliente(self, id_vendedor, id_cliente):
        '''
        Devuelve la información de un cliente en la agenda de un vendedor
        Args:
            - id_vendedor: int
            - id_cliente: int
        '''
        try:
            print("consultar_agenda_cliente")
            cliente, success = self.consultar_cliente(id_cliente)
            ncursor = self.login_database()
            # 1. Consultar la información del cliente
            query = """
            SELECT k_cliente, n_cliente, n_notas FROM agenda
            WHERE k_users = %s AND k_cliente = %s;
            """
            ncursor.execute(query, (id_vendedor, id_cliente))
            agenda_cliente = ncursor.fetchone()
            return [agenda_cliente, cliente[0], True] if agenda_cliente else ['El cliente no existe en la agenda', cliente[0],  False]
        except mysql.connector.Error as error:
            print('Consultar agenda cliente Error: ' +str(error))
            return ['Falló la consulta de cliente en agenda.', False]

    def consultar_agenda(self, id_vendedor, limit, offset, filter):
        '''
        Consulta la agenda de un venededor
        Args:
            - id_vendedor: int
            - limit: int
            - offset: int
            - filter: str
        '''
        try:
            print("consultar_agenda")
            ncursor = self.login_database()
            # Calcular total de clientes
            if filter: 
                query = """SELECT COUNT(k_cliente) FROM agenda WHERE k_users = %s AND LOWER(REPLACE(n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))"""
                ncursor.execute(query, (id_vendedor, filter, ))
            else:
                query = "SELECT COUNT(k_cliente) FROM agenda WHERE k_users = %s"
                ncursor.execute(query, (id_vendedor, ))
            total_agenda = ncursor.fetchone()
            # Consultar agenda
            if filter:
                query = """
                SELECT k_cliente, n_cliente FROM agenda WHERE k_users = %s
                AND LOWER(REPLACE(n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                LIMIT %s OFFSET %s
                """
                ncursor.execute(query, (id_vendedor, filter, limit, offset,))
            else:
                query = "SELECT k_cliente, n_cliente FROM agenda WHERE k_users = %s LIMIT %s OFFSET %s"
                ncursor.execute(query, (id_vendedor, limit, offset, ))
            agenda = ncursor.fetchall()
            return [total_agenda[0], agenda, True] if agenda else [0, [], False]
        except mysql.connector.Error as error:
            print('Consultar agenda Error: ' +str(error))
            return ['Falló la consulta de la agenda.', False]

    def consultar_cotizaciones_vendedor(self, id_vendedor, limit, offset, month, filter):
        '''
        Consulta las cotizaciones de un vendedor
        Args:
            - id_vendedor: int
        '''
        try:
            print("consultar_cotizaciones_vendedor")
            ncursor = self.login_database()
            if filter:
                query = """
                SELECT COUNT(pedidos_cotizaciones.k_venta_cotizacion)
                FROM pedidos_cotizaciones, venta_cotizaciones, clients
                WHERE venta_cotizaciones.k_venta_cotizacion = pedidos_cotizaciones.k_venta_cotizacion
                AND clients.k_cliente = venta_cotizaciones.k_cliente
                AND clients.k_cliente = pedidos_cotizaciones.k_cliente
                AND pedidos_cotizaciones.k_users = %s
                AND pedidos_cotizaciones.b_active = 1 
                AND MONTH(f_venta) = %s
                AND (
                        LOWER(REPLACE(clients.n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )
                GROUP BY venta_cotizaciones.k_venta_cotizacion
                """
                ncursor.execute(query, (id_vendedor, int(month), '%'+filter+'%', '%'+filter+'%'))
            else:
                query = """
                SELECT COUNT(pedidos_cotizaciones.k_venta_cotizacion)
                FROM pedidos_cotizaciones, venta_cotizaciones, clients
                WHERE venta_cotizaciones.k_venta_cotizacion = pedidos_cotizaciones.k_venta_cotizacion
                AND clients.k_cliente = venta_cotizaciones.k_cliente
                AND clients.k_cliente = pedidos_cotizaciones.k_cliente
                AND pedidos_cotizaciones.k_users = %s
                AND pedidos_cotizaciones.b_active = 1 
                AND MONTH(f_venta) = %s
                GROUP BY venta_cotizaciones.k_venta_cotizacion
                """
                ncursor.execute(query, (id_vendedor, int(month)))
            total_cotizaciones = ncursor.fetchone()
            if filter:
                query = """
                SELECT pedidos_cotizaciones.k_venta_cotizacion, clients.n_cliente, DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), 
                FORMAT(SUM(q_valortotal), 0, 'de_DE'), FORMAT(SUM(q_totalkilos), 0, 'de_DE')
                FROM pedidos_cotizaciones, venta_cotizaciones, clients
                WHERE venta_cotizaciones.k_venta_cotizacion = pedidos_cotizaciones.k_venta_cotizacion
                AND clients.k_cliente = venta_cotizaciones.k_cliente
                AND clients.k_cliente = pedidos_cotizaciones.k_cliente
                AND pedidos_cotizaciones.b_active = 1
                AND MONTH(f_venta) = %s
                AND pedidos_cotizaciones.k_users = %s
                AND (
                    LOWER(REPLACE(clients.n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                    LOWER(REPLACE(DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )
                GROUP BY venta_cotizaciones.k_venta_cotizacion 
                ORDER BY pedidos_cotizaciones.k_venta_cotizacion DESC
                LIMIT %s OFFSET %s
                """
                ncursor.execute(query, (int(month), id_vendedor, '%'+filter+'%', '%'+filter+'%', limit, offset,))
            else:
                query = """
                SELECT pedidos_cotizaciones.k_venta_cotizacion, clients.n_cliente, DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), 
                FORMAT(SUM(q_valortotal), 0, 'de_DE'), FORMAT(SUM(q_totalkilos), 0, 'de_DE')
                FROM pedidos_cotizaciones, venta_cotizaciones, clients
                WHERE venta_cotizaciones.k_venta_cotizacion = pedidos_cotizaciones.k_venta_cotizacion
                AND clients.k_cliente = venta_cotizaciones.k_cliente
                AND clients.k_cliente = pedidos_cotizaciones.k_cliente
                AND pedidos_cotizaciones.k_users = %s
                AND pedidos_cotizaciones.b_active = 1
                AND MONTH(f_venta) = %s
                GROUP BY venta_cotizaciones.k_venta_cotizacion 
                ORDER BY pedidos_cotizaciones.k_venta_cotizacion DESC
                LIMIT %s OFFSET %s
                """
                ncursor.execute(query, (id_vendedor, int(month), limit, offset,))
            cotizaciones = ncursor.fetchall()
            return [cotizaciones, total_cotizaciones, True] if cotizaciones else [[], 0, False]
        except mysql.connector.Error as error:
            print('Consultar cotizaciones vendedor Error: ' +str(error))
            return [[], 0, False]

    def pedido_fase1_bodega(self, pedido):
        '''
        Calcula: Cantidad - Cantidad bonificada - Total de Kilos - Total de Kilos Bonificados - V/U - V/T - V/T Bonificado
        Args:
            - pedido: list [producto, lp, cnt, cnt bnf, vu, kg]
        '''
        try:
            print('pedido_fase1_bodega')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            fase1 = []
            for producto in pedido:
                query = """SELECT q_cantkilos FROM listaprecios_bodegas WHERE k_productos = %s AND k_listaprecios = %s"""
                ncursor.execute(query, (producto[0], producto[1]))
                info_producto = ncursor.fetchone() # Cantidad Kilos
                fase1.append([
                    producto[0], # Nombre del producto
                    int(producto[2]), # Cantidad
                    float(producto[2]) * float(info_producto[0]), # Total de kilos
                ])
            return [fase1, True]
        except mysql.connector.Error as error:
            print('Consultar bodegas vendedor Error: ' +str(error))
            self.mysql.connection.rollback()
            return ['Falló la consulta de bodegas.', False]

    def pedido_fase1(self, pedido):
        '''
        Calcula: Cantidad - Cantidad bonificada - Total de Kilos - Total de Kilos Bonificados - V/U - V/T - V/T Bonificado
        Args:
            - pedido: list [producto, lp, cnt, cnt bnf, vu, kg]
        '''
        try:
            print('pedido_fase1')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            fase1 = []
            for producto in pedido:
                query = """SELECT q_valorunit, q_cantkilos FROM listaprecios WHERE k_productos = %s AND k_listaprecios = %s"""
                ncursor.execute(query, (producto[0], producto[1]))
                info_producto = ncursor.fetchone() #V/U, Cantidad Kilos
                fase1.append([
                    producto[0], # Nombre del producto
                    int(producto[2]), # Cantidad
                    int(producto[3]), # Cantidad bonificada 
                    float(info_producto[1]) * float(producto[2]), # Total de kilos
                    float(info_producto[1]) * float(producto[3]), # Total de kilos bonificados
                    round(float(info_producto[0]), 0), # V/U
                    round(float(info_producto[0]) * float(producto[2]), 0), # V/T
                    round(float(info_producto[0]) * float(config('IVA')) * float(producto[3]), 0), # V/T Bonificado
                    producto[1]
                ])
            return [fase1, True]
        except mysql.connector.Error as error:
            print('Consultar bodegas vendedor Error: ' +str(error))
            self.mysql.connection.rollback()
            return ['Falló la consulta de bodegas.', False]

    def consultar_bodegas_vendedor(self, id_vendedor):
        '''
        Consulta las bodegas de un vendedor
        '''
        try:
            print('consultar_bodegas_vendedor')
            ncursor = self.login_database()
            query = """
            SELECT JSON_OBJECT(
                'id', k_bodega,
                'nameBodega', bodegas.n_nombre,
                'idSeller', bodegas.k_users,
                'nameSeller', users.n_nombre,
                'active', IF(bodegas.b_active, 'true', 'false')
            ) FROM bodegas, users
            WHERE bodegas.k_users = %s 
            AND bodegas.k_users = users.k_users
            AND bodegas.b_active = 1"""
            ncursor.execute(query, (id_vendedor, ))
            bodegas = ncursor.fetchone()
            return [bodegas, True] if bodegas else ['No se encontró bodegas asociadas', False]
        except mysql.connector.Error as error:
            print('Consultar bodegas vendedor Error: ' +str(error))
            return ['Falló la consulta de bodegas.', False]

    def consultar_favoritos_cliente(self, id_user, mes, limit, offset, filter):
        '''
        Consulta los productos favoritos de un cliente
        Args:
            -id: int
        '''
        try:
            print('consultar_favoritos_cliente')
            año = datetime.datetime.now().strftime('%Y')
            ncursor = self.login_database()
            if filter:
                query = """
                SELECT COUNT(Q1.k_cliente) FROM (
                    SELECT clients.k_cliente, clients.n_cliente FROM clients, clientes_favoritos
                    WHERE clients.k_cliente = clientes_favoritos.k_cliente
                    AND k_users = %s
                    AND (
                        LOWER(REPLACE(clients.k_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(clients.n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )
                ) AS Q1 LEFT JOIN (
                    SELECT Q2.k_cliente, totalPesos, totalKg FROM (
                        SELECT pedidos.k_cliente, SUM(venta.q_vunitario*venta.q_cantidad_despachada) AS 'totalPesos', 
                        SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad_despachada) AS 'totalKg'
                        FROM venta, pedidos WHERE venta.k_venta = pedidos.k_venta
                        AND pedidos.b_active = 1
                        AND n_estadop0 = 'Autorizado'
                        AND n_estadop1 = 'Facturado'
                        AND MONTH(f_venta_facturado) = %s
                        AND YEAR(f_venta_facturado) = %s
                        GROUP BY k_cliente
                    ) AS Q2
                ) AS Q3 ON Q1.k_cliente = Q3.k_cliente
                LIMIT %s OFFSET %s;
                """
                ncursor.execute(query, (id_user, '%'+filter+'%', '%'+filter+'%', mes, año, limit, offset))
            else:
                query = """SELECT COUNT(k_cliente) FROM clientes_favoritos WHERE k_users = %s"""
                ncursor.execute(query, (id_user, ))
            total_favorites = ncursor.fetchone()[0]
            if filter:
                query = """
                SELECT Q1.k_cliente, Q1.n_cliente, FORMAT(Q3.totalPesos, 0, 'de_DE'), FORMAT(Q3.totalKg, 0, 'de_DE') FROM (
                    SELECT clients.k_cliente, clients.n_cliente FROM clients, clientes_favoritos
                    WHERE clients.k_cliente = clientes_favoritos.k_cliente
                    AND k_users = %s
                    AND (
                        LOWER(REPLACE(clients.k_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(clients.n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )
                ) AS Q1 LEFT JOIN (
                    SELECT Q2.k_cliente, totalPesos, totalKg FROM (
                        SELECT pedidos.k_cliente, SUM(venta.q_vunitario*venta.q_cantidad_despachada) AS 'totalPesos', 
                        SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad_despachada) AS 'totalKg'
                        FROM venta, pedidos WHERE venta.k_venta = pedidos.k_venta
                        AND pedidos.b_active = 1
                        AND n_estadop0 = 'Autorizado'
                        AND n_estadop1 = 'Facturado'
                        AND MONTH(f_venta_facturado) = %s
                        AND YEAR(f_venta_facturado) = %s
                        GROUP BY k_cliente
                    ) AS Q2
                ) AS Q3 ON Q1.k_cliente = Q3.k_cliente
                LIMIT %s OFFSET %s;
                """
                ncursor.execute(query, (id_user, '%'+filter+'%', '%'+filter+'%', int(mes), año, limit, offset,))
            else:
                query = """
                SELECT Q1.k_cliente, Q1.n_cliente, FORMAT(Q3.totalPesos, 0, 'de_DE'), FORMAT(Q3.totalKg, 0, 'de_DE') FROM (
                    SELECT clients.k_cliente, clients.n_cliente FROM clients, clientes_favoritos
                    WHERE clients.k_cliente = clientes_favoritos.k_cliente
                    AND k_users = %s
                ) AS Q1 LEFT JOIN (
                    SELECT Q2.k_cliente, totalPesos, totalKg FROM (
                        SELECT pedidos.k_cliente, SUM(venta.q_vunitario*venta.q_cantidad_despachada) AS 'totalPesos', 
                        SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad_despachada) AS 'totalKg'
                        FROM venta, pedidos WHERE venta.k_venta = pedidos.k_venta
                        AND pedidos.b_active = 1
                        AND n_estadop0 = 'Autorizado'
                        AND n_estadop1 = 'Facturado'
                        AND MONTH(f_venta_facturado) = %s
                        AND YEAR(f_venta_facturado) = %s
                        GROUP BY k_cliente
                    ) AS Q2
                ) AS Q3 ON Q1.k_cliente = Q3.k_cliente
                LIMIT %s OFFSET %s
                """
                ncursor.execute(query, (id_user, int(mes), año, limit, offset, ))
            favoritos = ncursor.fetchall()
            return [[favoritos, total_favorites], True] if favoritos else [[[], 0], False]
        except mysql.connector.Error as error:
            print('Consultar favoritos cliente Error: ' +str(error))
            return [[[], 0], False]


    def consultar_pedido_bodega(self, id_pedido):
        '''
        Consulta un pedido de bodega
        Args:
            -id: int
        '''
        try:
            print('consultar_pedido_bodega')
            ncursor = self.login_database()
            query = """
            SELECT JSON_OBJECT(
                'idBodega', pedidos_bodegas.k_bodega,
                'idSeller', pedidos_bodegas.k_users,
                'nameBodega', bodegas.n_nombre,
                'nameSeller', CONCAT(users.n_nombre, ' ', users.n_apellido),
                'totalKg', SUM((q_totalkilos/q_cantidad)*q_cantidad),
                'totalKgDespachados', SUM((q_totalkilos/q_cantidad)*q_cantidad_despachada),
                'active', IF(pedidos_bodegas.b_active, 'true', 'false'),
                'date', DATE_FORMAT(pedidos_bodegas.f_venta,'%%e/%%m/%%Y'),
                'dateDispatch', DATE_FORMAT(pedidos_bodegas.f_venta_despachado,'%%e/%%m/%%Y'),
                'status', pedidos_bodegas.n_estadop0,
                'obs', pedidos_bodegas.n_observaciones
            )
            FROM venta_bodegas, users, pedidos_bodegas, bodegas
            WHERE users.k_users = venta_bodegas.k_users
            AND venta_bodegas.k_bodega = bodegas.k_bodega
            AND pedidos_bodegas.k_bodega = bodegas.k_bodega
            AND pedidos_bodegas.k_venta_bodegas = venta_bodegas.k_venta_bodegas
            AND pedidos_bodegas.k_venta_bodegas = %s
            GROUP BY pedidos_bodegas.k_venta_bodegas"""
            ncursor.execute(query, (id_pedido, ))
            info_pedido = ncursor.fetchone()
            query = """SELECT k_productos, FORMAT(q_cantidad, 0, 'de_DE'), FORMAT(q_totalkilos, 0, 'de_DE'), n_categoria, q_cantidad_despachada FROM venta_bodegas WHERE k_venta_bodegas = %s"""
            ncursor.execute(query, (id_pedido, ))
            pedido = ncursor.fetchall()
            return [[pedido, info_pedido[0]], True] if pedido else [['No se encontró el pedido', None], False]
        except mysql.connector.Error as error:
            print('Consultar pedido bodega Error: ' +str(error))
            return ['Falló la consulta de pedido bodega.', False]
            
    def consultar_pedidos_bodegas(self, limit, offset, filter, category):
        '''
        Consulta todos los pedidos de todas las bodegas
        Args:
            -limit: int
            -offset: int
            -filter: str
            -category: str
        '''
        try:
            print('consultar_pedidos_bodegas')
            # Pedidos bodegas
            ncursor = self.login_database()
            if category == "Eliminados":
                query = """SELECT COUNT(k_venta_bodegas) FROM pedidos_bodegas WHERE b_active = 0"""
                ncursor.execute(query)
                total_pedidos_bodega = ncursor.fetchone()
                query = """
                SELECT k_venta_bodegas, CONCAT(users.n_nombre, " ", n_apellido), DATE_FORMAT(pedidos_bodegas.f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(pedidos_bodegas.f_venta_despachado,'%%e/%%m/%%Y'), n_estadop0 FROM pedidos_bodegas, users
                WHERE users.k_users = pedidos_bodegas.k_users
                AND pedidos_bodegas.b_active = 0
                LIMIT %s OFFSET %s
                """
                ncursor.execute(query, (limit, offset))
                pedidos = ncursor.fetchall()
                return [[total_pedidos_bodega[0], pedidos], True] if pedidos else [[0, []], False]
            else:
                if category == "Por despachar":
                    query_complement = """AND n_estadop0 = 'Por despachar'"""
                elif category == "Despachado":
                    query_complement = """AND n_estadop0 = 'Despachado'"""
                elif category == "Incompletos":
                    query_complement = """AND n_estadop0 = 'Incompleto'"""
                else:
                    query_complement = """AND n_estadop0 = 'Por despachar'"""
                query = """SELECT COUNT(k_venta_bodegas), CONCAT(users.n_nombre, " ", n_apellido), DATE_FORMAT(pedidos_bodegas.f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(pedidos_bodegas.f_venta_despachado,'%%e/%%m/%%Y'), n_estadop0 FROM pedidos_bodegas, users
                WHERE users.k_users = pedidos_bodegas.k_users """ + query_complement + """ AND pedidos_bodegas.b_active = 1"""
                if filter:
                    filter = '%' + filter + '%'
                    query += """ AND (
                        LOWER(REPLACE(pedidos_bodegas.k_venta_bodegas, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(CONCAT(users.n_nombre, " ", n_apellido), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(pedidos_bodegas.f_venta, '%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(pedidos_bodegas.f_venta_despachado, '%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )"""
                    ncursor.execute(query, (filter, filter, filter, filter))
                else:
                    ncursor.execute(query)
                total_pedidos_bodega = ncursor.fetchone()[0]
                if category == "Por despachar":
                    query_complement = """AND pedidos_bodegas.n_estadop0 = 'Por despachar'"""
                elif category == "Despachado":
                    query_complement = """AND pedidos_bodegas.n_estadop0 = 'Despachado'"""
                elif category == "Incompletos":
                    query_complement = """AND pedidos_bodegas.n_estadop0 = 'Incompleto'"""
                else:
                    query_complement = """AND pedidos_bodegas.n_estadop0 = 'Por despachar'"""
                if filter:
                    query = """
                    SELECT k_venta_bodegas, CONCAT(users.n_nombre, " ", n_apellido), DATE_FORMAT(pedidos_bodegas.f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(pedidos_bodegas.f_venta_despachado,'%%e/%%m/%%Y'), n_estadop0 FROM pedidos_bodegas, users
                    WHERE users.k_users = pedidos_bodegas.k_users
                    """ + query_complement + """ 
                    AND (
                        LOWER(REPLACE(pedidos_bodegas.k_venta_bodegas, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(CONCAT(users.n_nombre, " ", n_apellido), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(pedidos_bodegas.f_venta, '%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(pedidos_bodegas.f_venta_despachado, '%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )
                    AND pedidos_bodegas.b_active = 1
                    ORDER BY n_estadop0 DESC, f_venta DESC, k_venta_bodegas DESC
                    LIMIT %s OFFSET %s
                    """
                    ncursor.execute(query, (filter, filter, filter, filter, limit, offset,))
                else:
                    query = """
                    SELECT k_venta_bodegas, CONCAT(users.n_nombre, " ", n_apellido), DATE_FORMAT(pedidos_bodegas.f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(pedidos_bodegas.f_venta_despachado,'%%e/%%m/%%Y'), n_estadop0 FROM pedidos_bodegas, users
                    WHERE users.k_users = pedidos_bodegas.k_users
                    """ + query_complement + """ 
                    AND pedidos_bodegas.b_active = 1
                    ORDER BY n_estadop0 DESC, f_venta DESC, k_venta_bodegas DESC
                    LIMIT %s OFFSET %s
                    """
                    ncursor.execute(query, (limit, offset,))
                pedidos = ncursor.fetchall()
                return [[total_pedidos_bodega, pedidos], True] if pedidos else [[0, []], False]
        except mysql.connector.Error as error:
            print('Consultar pedidos bodegas Error: ' +str(error))
            return [[0, []], False]

    def consultar_pedidos_bodega(self, id_bodega, limit, offset):
        '''
        Consulta los pedidos de una bodega
        Args:
            -id_bodega: int
            -limit: int
            -offset: int
        '''
        try:
            print('consultar_pedidos_bodega')
            # Pedidos bodegas
            ncursor = self.login_database()
            query = """SELECT COUNT(k_venta_bodegas), CONCAT(users.n_nombre, " ", n_apellido), f_venta, f_venta_despachado, n_estadop0 FROM pedidos_bodegas, users
            WHERE users.k_users = pedidos_bodegas.k_users
            AND pedidos_bodegas.b_active = 1
            AND k_bodega = %s"""
            ncursor.execute(query, (id_bodega, ))
            total_pedidos_bodega = ncursor.fetchone()
            query = """
            SELECT k_venta_bodegas, CONCAT(users.n_nombre, " ", n_apellido), DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'), n_estadop0 FROM pedidos_bodegas, users
            WHERE users.k_users = pedidos_bodegas.k_users
            AND pedidos_bodegas.b_active = 1
            AND k_bodega = %s
            LIMIT %s OFFSET %s
            """
            ncursor.execute(query, (id_bodega, limit, offset))
            pedidos = ncursor.fetchall()
            return [[total_pedidos_bodega[0], pedidos], True] if total_pedidos_bodega else [['No se encontró la bodega', 0, []], False]
        except mysql.connector.Error as error:
            print('Consultar pedidos bodega Error: ' +str(error))
            return ['Falló la consulta de pedidos bodega.', False]

    def consultar_bodega(self, id_bodega):
        '''
        Consulta una bodega
        Args:
            -id: int
        '''
        try:
            print('consultar_bodega')
            ncursor = self.login_database()
            query = """SELECT JSON_OBJECT(
                'id', k_bodega, 
                'nameBodega', bodegas.n_nombre,
                'idSeller', users.k_users,
                'nameSeller', CONCAT(users.n_nombre, " ", n_apellido),
                'active', IF(bodegas.b_active, 'true', 'false')
            )
            FROM bodegas, users 
            WHERE bodegas.k_users = users.k_users
            AND k_bodega = %s"""
            ncursor.execute(query, (id_bodega, ))
            bodega = ncursor.fetchone()
            return [bodega[0], True] if bodega else ['No se encontró la bodega', False]
        except mysql.connector.Error as error:
            print('Consultar bodega Error: ' +str(error))
            return ['Falló la consulta de bodega.', False]
    
    def consultar_listas_precios_bodegas(self):
        '''
        Consulta las listas de precios de las bodegas
        '''
        try:
            print('consultar_listas_precios_bodegas')
            ncursor = self.login_database()
            query = """SELECT k_listaprecios, n_nombre, n_marca FROM namelp_bodegas"""
            ncursor.execute(query)
            listas_precios = ncursor.fetchall()
            return [listas_precios, True] if listas_precios else ['No se encontraron listas de precios', False]
        except mysql.connector.Error as error:
            print('Consultar listas precios bodegas Error: ' +str(error))
            return ['Falló la consulta de listas precios bodegas.', False]

    def consultar_productos_lp_bodegas(self, id_lp_bodega):
        '''
        Consulta los productos registrados en la lista de precios de una bodega
        Args:
            - id_lp_bodega: int
        '''
        try:
            print('consultar_productos_lp_bodegas')
            ncursor = self.login_database()
            query = """SELECT k_productos, q_cantkilos FROM listaprecios_bodegas WHERE k_listaprecios = %s"""
            ncursor.execute(query, (id_lp_bodega, ))
            productos = ncursor.fetchall()
            return [productos, True] if productos else ['No se encontraron productos', False]
        except mysql.connector.Error as error:
            print('Consultar productos lp bodegas Error: ' +str(error))
            return ['Falló la consulta de productos lp bodegas.', False]


    def consultar_bodegas(self):
        '''
        Consulta todas las bodegas registradas en el sistema
        '''
        try:
            print('consultar_bodegas')
            ncursor = self.login_database()
            query = """SELECT k_bodega, bodegas.n_nombre, CONCAT(users.n_nombre, " ", n_apellido) 
            FROM bodegas, users 
            WHERE bodegas.k_users = users.k_users
            AND bodegas.b_active = 1"""
            ncursor.execute(query)
            bodegas = ncursor.fetchall()
            return [bodegas, True] if bodegas else ['No se encontraron bodegas', False]
        except mysql.connector.Error as error:
            print('Consultar bodegas Error: ' +str(error))
            return ['Falló la consulta de bodegas.', False]

    def consultar_obs_bodega(self, id):
        '''
        Consultamos las observaciones de un pedido
        Args:
            -id: int
            -category: str
        '''
        try:
            print('consultar_obs_bodega')
            ncursor = self.login_database()
            query = "SELECT n_observaciones FROM pedidos_bodegas WHERE k_venta_bodegas = %s"
            ncursor.execute(query, (id, ))
            result = ncursor.fetchone()
            return [result, True] if result else ['No se encontraron observaciones', False]
        except mysql.connector.Error as error:
            print('Consultar observaciones Error: ' +str(error))
            return ['Falló la consulta de observaciones.', False]

    def consultar_obs(self, id, category):
        '''
        Consultamos las observaciones de un pedido
        Args:
            -id: int
            -category: str
        '''
        try:
            print('consultar_obs')
            ncursor = self.login_database()
            query = "SELECT n_observaciones FROM pedidos WHERE k_venta = %s"
            if category == 'Eliminados':
                query = "SELECT n_observaciones FROM pedidos_borrados WHERE k_venta = %s"
            ncursor.execute(query, (id, ))
            result = ncursor.fetchone()
            return [result, True] if result else ['No se encontraron observaciones', False]
        except mysql.connector.Error as error:
            print('Consultar observaciones Error: ' +str(error))
            return ['Falló la consulta de observaciones.', False]

    def consultar_pedido(self, id):
        '''
        Consulta un pedido
        Args:
            - id: int
        '''
        try:
            print('consultar_pedido')
            ncursor = self.login_database()
            query = """
            SELECT JSON_OBJECT(
                'idClient', venta.k_cliente,
                'nameClient', n_cliente,
                'idSeller', venta.k_users,
                'idZone', clients.k_zona, 
                'clientAddress', clients.n_direccion,
                'clientCity', clients.n_ciudad,
                'clientPhone', clients.q_telefono,
                'clientDepartment',departamento.n_departamento,
                'nameZone', zona.n_zona,
                'nameSeller', CONCAT(n_nombre, ' ', n_apellido),
                'totalKg', SUM((q_totalkilos/q_cantidad)*q_cantidad),
                'totalPesos', SUM(q_cantidad*q_vunitario),
                'totalKgBnf', SUM(q_totalkilosb),
                'active', IF(pedidos.b_active, 'true', 'false'),
                'date',DATE_FORMAT(pedidos.f_venta,'%%e/%%m/%%Y'),
                'autorized', n_estadop0,
                'billed', n_estadop1,
                'shipped', n_estadop2,
                'iva', ROUND(SUM(q_cantidad*q_vunitario) * %s),
                'ivaBnf', SUM(q_valortotalb),
                'total', (SUM(q_cantidad*q_vunitario) * %s) + SUM(q_cantidad*q_vunitario) + SUM(q_valortotalb),
                'obs', pedidos.n_observaciones,
                'totalPesosDespachados', SUM(q_cantidad_despachada*q_vunitario),
                'totalKgDespachados', SUM((q_totalkilos/q_cantidad)*q_cantidad_despachada)
            )
            FROM venta, clients, users, zona, pedidos, departamento
            WHERE venta.k_cliente = clients.k_cliente
            AND clients.k_departamento = departamento.k_departamento
            AND pedidos.k_venta = venta.k_venta
            AND clients.k_zona = zona.k_zona
            AND venta.k_users = users.k_users
            AND pedidos.k_venta = %s
            GROUP BY pedidos.k_venta
            """
            ncursor.execute(query, (float(config('IVA')), float(config('IVA')), id,))
            info_pedido = ncursor.fetchone()
            query = """
            SELECT k_productos, 
            FORMAT(q_cantidad, 0, 'de_DE'), FORMAT(q_bonificacion, 0, 'de_DE'), FORMAT(q_totalkilos, 0, 'de_DE'), 
            FORMAT(q_totalkilosb, 0, 'de_DE'), FORMAT(q_vunitario, 0, 'de_DE'), FORMAT(q_valortotal, 0, 'de_DE'), 
            FORMAT(q_valortotalb, 0, 'de_DE'), n_categoria, q_cantidad_despachada
            FROM venta WHERE k_venta = %s
            """
            ncursor.execute(query, (id, ))
            pedido = ncursor.fetchall()
            return [[pedido, info_pedido], True] if pedido else [['No se encontró el pedido', None], False]
        except mysql.connector.Error as error:
            print('Consultar pedido Error: ' +str(error))
            return ['Falló la consulta de pedido.', False]

    def consultar_pedidos_bodegas_por_vendedor(self, id_vendedor, limit, offset, filter, category):
        '''
        Devuelve todos los pedidos registrados
        Args:
            - id_vendedor: int
            - limit: int
            - offset: int
            - filter: string
            - category: string
        '''
        try:
            print('consultar_pedidos_bodegas_por_vendedor')
            ncursor = self.login_database()
            if category == "Eliminados":
                query = """SELECT COUNT(k_venta_bodegas) FROM pedidos_bodegas WHERE b_active = 0 AND k_users = %s"""
                ncursor.execute(query, (id_vendedor, ))
                total_pedidos = ncursor.fetchone()[0]
                query = """SELECT k_venta_bodegas, k_bodega, DATE_FORMAT(f_venta,'%%e/%%m/%%Y') FROM pedidos_bodegas
                WHERE b_active = 0 
                AND pedidos_bodegas.k_users = %s
                ORDER BY k_venta_bodegas DESC
                LIMIT %s OFFSET %s"""
                ncursor.execute(query, (id_vendedor, limit, offset))
                pedidos = ncursor.fetchall()
                return [[pedidos, total_pedidos], True] if pedidos else [[[], 0], False]
            else:
                if category == "Despachado":
                    query_complement = """WHERE n_estadop0 = 'Despachado'"""
                elif category == "Incompletos":
                    query_complement = """WHERE n_estadop0 = 'Incompleto'"""
                else:
                    query_complement = """WHERE n_estadop0 = 'Por despachar'"""
                query = """SELECT COUNT(pedidos_bodegas.k_venta_bodegas) FROM pedidos_bodegas, (
                    SELECT k_venta_bodegas, k_users, FORMAT(SUM(q_totalkilos), 0, 'de_DE') AS totalkg
                    FROM venta_bodegas GROUP BY k_venta_bodegas
                ) AS vgrouped """ + query_complement + """ AND pedidos_bodegas.k_venta_bodegas = vgrouped.k_venta_bodegas
                AND pedidos_bodegas.b_active = 1
                AND pedidos_bodegas.k_users = %s"""
                if filter:
                    filter = '%' + filter + '%'
                    query += """ AND (
                        LOWER(REPLACE(pedidos_bodegas.k_venta_bodegas, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(totalkg, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )"""
                    ncursor.execute(query, (id_vendedor, filter, filter, filter, filter, ))
                else: 
                    ncursor.execute(query, (id_vendedor, ))
                total_pedidos = ncursor.fetchone()[0]
                query_order_complement = "f_venta DESC, pedidos_bodegas.k_venta_bodegas DESC"
                if category == "Despachado":
                    query_complement = "AND n_estadop0 = 'Despachado'"
                elif category == "Incompletos":
                    query_complement = "AND n_estadop0 = 'Incompleto'"
                else:
                    query_complement = "AND n_estadop0 = 'Por despachar'"
                if filter:
                    query = """
                    SELECT pedidos_bodegas.k_venta_bodegas,
                    DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'),
                    totalkg, n_estadop0
                    FROM pedidos_bodegas, (
                        SELECT k_venta_bodegas, k_users, FORMAT(SUM(q_totalkilos), 0, 'de_DE') AS totalkg
                        FROM venta_bodegas GROUP BY k_venta_bodegas
                    ) AS vgrouped
                    WHERE pedidos_bodegas.k_venta_bodegas = vgrouped.k_venta_bodegas
                    AND pedidos_bodegas.b_active = 1
                    AND pedidos_bodegas.k_users = %s
                    """ + query_complement + """  
                    AND (
                        LOWER(REPLACE(pedidos_bodegas.k_venta_bodegas, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(totalkg, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    ) 
                    ORDER BY f_venta DESC, pedidos_bodegas.k_venta_bodegas DESC
                    LIMIT %s OFFSET %s
                    """
                    ncursor.execute(query, (id_vendedor, filter, filter, filter, filter, limit, offset,))
                else:
                    query = """
                    SELECT pedidos_bodegas.k_venta_bodegas,
                    DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'),
                    totalkg, n_estadop0
                    FROM pedidos_bodegas, (
                        SELECT k_venta_bodegas, FORMAT(SUM(q_totalkilos), 0, 'de_DE') AS totalkg
                        FROM venta_bodegas GROUP BY k_venta_bodegas
                    ) AS vgrouped
                    WHERE pedidos_bodegas.k_venta_bodegas = vgrouped.k_venta_bodegas
                    AND pedidos_bodegas.b_active = 1
                    AND pedidos_bodegas.k_users = %s
                    """ + query_complement + """
                    ORDER BY """ + query_order_complement + """
                    LIMIT %s OFFSET %s;
                    """
                    ncursor.execute(query, (id_vendedor, limit, offset, ))
                pedidos = ncursor.fetchall()
                return [[pedidos, total_pedidos], True] if pedidos else [[[], 0], False]
        except mysql.connector.Error as error:
            print('Consultar pedidos bodega Error: ' +str(error))
            return  [[[], 0], False]

    def consultar_pedidos(self,limit, offset, filter, category):
        '''
        Devuelve todos los pedidos registrados
        Args:
            -limit: int
            -offset: int
            -filter: string
            -category: string
        '''
        try:
            print('consultar_pedidos')
            ncursor = self.login_database()
            if category == "Eliminados":
                if filter:
                    filter = '%' + filter + '%'
                    query = """
                    SELECT COUNT(Q3.k_venta) FROM (SELECT Q1.k_venta, k_cliente, n_cliente, k_users, nombre_vendedor, fecha_borrado, q_user_deleting, nombre_borra FROM (
                        SELECT k_venta, pedidos_borrados.k_cliente, n_cliente, pedidos_borrados.k_users, 
                        CONCAT(n_nombre, ' ', n_apellido) AS nombre_vendedor, DATE_FORMAT(f_venta_borrado,'%%e/%%m/%%Y') AS fecha_borrado
                        FROM pedidos_borrados, clients, users
                        WHERE pedidos_borrados.k_cliente = clients.k_cliente
                        AND pedidos_borrados.k_users = users.k_users
                        ) AS Q1
                    LEFT JOIN (
                        SELECT k_venta, q_user_deleting, CONCAT(n_nombre, ' ', n_apellido) AS nombre_borra FROM pedidos_borrados, users
                        WHERE pedidos_borrados.q_user_deleting = users.k_users
                    ) AS Q2 ON Q1.k_venta = Q2.k_venta) AS Q3 WHERE (
                        LOWER(REPLACE(Q3.k_venta, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.k_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.k_users, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.nombre_vendedor, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.fecha_borrado, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.q_user_deleting, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.nombre_borra, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    );"""
                    ncursor.execute(query, (filter, filter, filter, filter, filter, filter, filter, filter,))
                    total_pedidos = ncursor.fetchone()[0]
                    query = """
                    SELECT * FROM (SELECT Q1.k_venta, k_cliente, n_cliente, k_users, nombre_vendedor, fecha_borrado, q_user_deleting, nombre_borra FROM (
                        SELECT k_venta, pedidos_borrados.k_cliente, n_cliente, pedidos_borrados.k_users, 
                        CONCAT(n_nombre, ' ', n_apellido) AS nombre_vendedor, DATE_FORMAT(f_venta_borrado,'%%e/%%m/%%Y') AS fecha_borrado
                        FROM pedidos_borrados, clients, users
                        WHERE pedidos_borrados.k_cliente = clients.k_cliente
                        AND pedidos_borrados.k_users = users.k_users
                        ) AS Q1
                    LEFT JOIN (
                        SELECT k_venta, q_user_deleting, CONCAT(n_nombre, ' ', n_apellido) AS nombre_borra FROM pedidos_borrados, users
                        WHERE pedidos_borrados.q_user_deleting = users.k_users
                    ) AS Q2 ON Q1.k_venta = Q2.k_venta) AS Q3 WHERE (
                        LOWER(REPLACE(Q3.k_venta, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.k_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.k_users, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.nombre_vendedor, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.fecha_borrado, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.q_user_deleting, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(Q3.nombre_borra, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )
                    ORDER BY Q3.k_venta DESC LIMIT %s OFFSET %s"""
                    ncursor.execute(query, (filter, filter, filter, filter, filter, filter, filter, filter, limit, offset))
                    pedidos = ncursor.fetchall()
                    return [[pedidos, total_pedidos], True] if pedidos else [[[], 0], False]
                else:
                    query = """
                    SELECT COUNT(Q1.k_venta) FROM (
                        SELECT k_venta, pedidos_borrados.k_cliente, n_cliente, pedidos_borrados.k_users, 
                        CONCAT(n_nombre, ' ', n_apellido), DATE_FORMAT(f_venta_borrado,'%%e/%%m/%%Y') 
                        FROM pedidos_borrados, clients, users
                        WHERE pedidos_borrados.k_cliente = clients.k_cliente
                        AND pedidos_borrados.k_users = users.k_users
                        ) AS Q1
                    LEFT JOIN (
                        SELECT k_venta, q_user_deleting, CONCAT(n_nombre, ' ', n_apellido) FROM pedidos_borrados, users
                        WHERE pedidos_borrados.q_user_deleting = users.k_users
                    ) AS Q2 ON Q1.k_venta = Q2.k_venta
                    """
                    ncursor.execute(query)
                    total_pedidos = ncursor.fetchone()[0]
                    query = """
                    SELECT Q1.k_venta, k_cliente, n_cliente, k_users, nombre_vendedor, fecha_borrado, q_user_deleting, nombre_borra FROM (
                        SELECT k_venta, pedidos_borrados.k_cliente, n_cliente, pedidos_borrados.k_users, 
                        CONCAT(n_nombre, ' ', n_apellido) AS nombre_vendedor, DATE_FORMAT(f_venta_borrado,'%%e/%%m/%%Y') AS fecha_borrado
                        FROM pedidos_borrados, clients, users
                        WHERE pedidos_borrados.k_cliente = clients.k_cliente
                        AND pedidos_borrados.k_users = users.k_users
                        ) AS Q1
                    LEFT JOIN (
                        SELECT k_venta, q_user_deleting, CONCAT(n_nombre, ' ', n_apellido) AS nombre_borra FROM pedidos_borrados, users
                        WHERE pedidos_borrados.q_user_deleting = users.k_users
                    ) AS Q2 ON Q1.k_venta = Q2.k_venta
                    ORDER BY Q1.k_venta DESC LIMIT %s OFFSET %s"""
                    ncursor.execute(query, (limit, offset))
                    pedidos = ncursor.fetchall()
                    return [[pedidos, total_pedidos], True] if pedidos else [[[], 0], False]
            else:
                if category == "No autorizado":
                    query_complement = """WHERE n_estadop0 = 'No autorizado' AND n_estadop1 = 'Por facturar'"""
                elif category == "Autorizado":
                    query_complement = """WHERE n_estadop0 = 'Autorizado' AND n_estadop1 = 'Por facturar'"""
                elif category == "Por despachar":
                    query_complement = """WHERE n_estadop0 = 'Autorizado' AND n_estadop1 = 'Facturado' AND n_estadop2 = 'Por despachar'"""
                elif category == "Despachado":
                    query_complement = """WHERE n_estadop0 = 'Autorizado' AND n_estadop1 = 'Facturado' AND n_estadop2 = 'Despachado'"""
                elif category == "Incompletos":
                    query_complement = """WHERE n_estadop0 = 'Autorizado' AND n_estadop1 = 'Facturado' AND n_estadop2 = 'Incompleto'"""
                else:
                    query_complement = """WHERE n_estadop0 = 'No autorizado' AND n_estadop1 = 'Por facturar'"""
                query = """SELECT COUNT(pedidos.k_venta) FROM pedidos, clients, zona, (
                    SELECT k_venta, k_cliente, k_users, FORMAT(SUM(q_valortotal), 0, 'de_DE') AS subtotal, FORMAT(SUM(q_valortotalb), 0, 'de_DE') as ivabonif,
                    FORMAT((SUM(q_valortotal)* %s), 0, 'de_DE') AS ivasubtotal, FORMAT(((SUM(q_valortotal)* %s) + SUM(q_valortotal)), 0, 'de_DE') AS total
                    FROM venta GROUP BY k_venta
                ) AS vgrouped """ + query_complement + """ AND pedidos.k_venta = vgrouped.k_venta
                AND pedidos.k_cliente = clients.k_cliente
                AND clients.k_zona = zona.k_zona
                AND pedidos.b_active = 1"""
                if filter:
                    filter = '%' + filter + '%'
                    query += """ AND (
                        LOWER(REPLACE(pedidos.k_venta, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(n_zona, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(n_ciudad, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(clients.k_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(pedidos.k_users, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta_autorizado,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta_facturado,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(subtotal, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(ivabonif, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(ivasubtotal, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(total, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    )"""
                    ncursor.execute(query, (float(config('IVA')), float(config('IVA')), filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, ))
                else: 
                    ncursor.execute(query, (float(config('IVA')), float(config('IVA')),))
                total_pedidos = ncursor.fetchone()[0]
                query_order_complement = "n_estadop1 DESC, n_estadop2 ASC, f_venta DESC, pedidos.k_venta DESC"
                if category == "No autorizado":
                    query_complement = "AND n_estadop0 = 'No autorizado' AND n_estadop1 = 'Por facturar'"
                elif category == "Autorizado":
                    query_complement = "AND n_estadop0 = 'Autorizado' AND n_estadop1 = 'Por facturar'"
                    query_order_complement = "pedidos.k_venta DESC, f_venta_autorizado DESC"
                elif category == "Por despachar":
                    query_complement = "AND n_estadop0 = 'Autorizado' AND n_estadop1 = 'Facturado' AND n_estadop2 = 'Por despachar'"
                elif category == "Despachado":
                    query_complement = "AND n_estadop0 = 'Autorizado' AND n_estadop1 = 'Facturado' AND n_estadop2 = 'Despachado'"
                elif category == "Incompletos":
                    query_complement = "AND n_estadop0 = 'Autorizado' AND n_estadop1 = 'Facturado' AND n_estadop2 = 'Incompleto'"
                else:
                    query_complement = "AND n_estadop0 = 'No autorizado' AND n_estadop1 = 'Por facturar'"
                if filter:
                    query = """
                    SELECT pedidos.k_venta, n_zona, n_ciudad, clients.k_cliente, n_cliente, pedidos.k_users,
                    DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_autorizado,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_facturado,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'),
                    subtotal, ivabonif, ivasubtotal, total, n_estadop0, n_estadop1, n_estadop2
                    FROM pedidos, clients, zona, (
                        SELECT k_venta, k_cliente, k_users, FORMAT(SUM(q_valortotal), 0, 'de_DE') AS subtotal, FORMAT(SUM(q_valortotalb), 0, 'de_DE') as ivabonif,
                        FORMAT((SUM(q_valortotal)* %s), 0, 'de_DE') AS ivasubtotal, FORMAT(((SUM(q_valortotal)* %s) + SUM(q_valortotal)), 0, 'de_DE') AS total
                        FROM venta GROUP BY k_venta
                    ) AS vgrouped
                    WHERE pedidos.k_venta = vgrouped.k_venta
                    AND pedidos.k_cliente = clients.k_cliente
                    AND clients.k_zona = zona.k_zona
                    AND pedidos.b_active = 1
                    """ + query_complement + """  
                    AND (
                        LOWER(REPLACE(pedidos.k_venta, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(n_zona, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(n_ciudad, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(clients.k_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(pedidos.k_users, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta_autorizado,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta_facturado,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'), ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(subtotal, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(ivabonif, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(ivasubtotal, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                        LOWER(REPLACE(total, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                    ) 
                    ORDER BY n_estadop1 DESC, n_estadop2 ASC, pedidos.k_venta DESC, f_venta DESC
                    LIMIT %s OFFSET %s
                    """
                    ncursor.execute(query, (float(config('IVA')), float(config('IVA')), filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, filter, limit, offset,))
                else:
                    query = """
                    SELECT pedidos.k_venta, n_zona, n_ciudad, clients.k_cliente, n_cliente, pedidos.k_users,
                    DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_autorizado,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_facturado,'%%e/%%m/%%Y'), DATE_FORMAT(f_venta_despachado,'%%e/%%m/%%Y'),
                    subtotal, ivabonif, ivasubtotal, total, n_estadop0, n_estadop1, n_estadop2
                    FROM pedidos, clients, zona, (
                        SELECT k_venta, k_cliente, k_users, FORMAT(SUM(q_valortotal), 0, 'de_DE') AS subtotal, FORMAT(SUM(q_valortotalb), 0, 'de_DE') as ivabonif,
                        FORMAT((SUM(q_valortotal)*%s), 0, 'de_DE') AS ivasubtotal, FORMAT(((SUM(q_valortotal)*%s) + SUM(q_valortotal)), 0, 'de_DE') AS total
                        FROM venta GROUP BY k_venta
                    ) AS vgrouped
                    WHERE pedidos.k_venta = vgrouped.k_venta
                    AND pedidos.k_cliente = clients.k_cliente
                    AND clients.k_zona = zona.k_zona
                    """ + query_complement + """       
                    AND pedidos.b_active = 1
                    ORDER BY """ + query_order_complement + """
                    LIMIT %s OFFSET %s;
                    """
                    ncursor.execute(query, (float(config('IVA')),float(config('IVA')), limit, offset, ))
                pedidos = ncursor.fetchall()
                return [[pedidos, total_pedidos], True] if pedidos else [[[], 0], False]
        except mysql.connector.Error as error:
            print('Consultar pedidos Error: ' +str(error))
            return  [[[], 0], False]

    def consultar_lista_precio(self, id, category):
        '''
        Devuelve una lista de precio
        Args:
            id: Integer
            category: String
        '''
        try:
            print('consultar_lista_precio')
            ncursor = self.login_database()
            if category == "Bodegas":
                # Información general
                query = "SELECT JSON_OBJECT('id', k_listaprecios, 'name', n_nombre, 'brand', n_marca, 'link', n_link) FROM namelp_bodegas WHERE k_listaprecios = %s"
                ncursor.execute(query, (id, ))
                lp = ncursor.fetchone()
                query = "SELECT k_productos, FORMAT(q_cantkilos, 1, 'de_DE') FROM listaprecios_bodegas WHERE k_listaprecios = %s"
                ncursor.execute(query, (id, ))
                productos = ncursor.fetchall()
                query = """SELECT JSON_OBJECT('id', users.k_users, 'vendedor', CONCAT(n_nombre, ' ', n_apellido)) FROM vendedor_listaprecios_bodegas, users
                WHERE vendedor_listaprecios_bodegas.k_users = users.k_users AND k_listaprecios = %s"""
                ncursor.execute(query, (id, ))
                vendedor = ncursor.fetchall()
                if not lp:
                    return [[
                        'No se encontró la lista de precio',
                        productos if productos else "No se encontró productos en la lista de precios",
                        vendedor if vendedor else "No se encontró vendedor asociado a la lista de precios"
                        ], False]
                return [[
                    lp,
                    productos if productos else "No se encontró productos en la lista de precios",
                    vendedor if vendedor else "No se encontró vendedor asociado a la lista de precios"
                    ], True]
            else:
                # Información general
                query = "SELECT JSON_OBJECT('id', k_listaprecios, 'name', n_nombre, 'brand', n_marca, 'link', n_link) FROM namelp WHERE k_listaprecios = %s"
                ncursor.execute(query, (id, ))
                lp = ncursor.fetchone()
                query = "SELECT k_productos, FORMAT(q_valorunit, 0, 'de_DE'), FORMAT(q_cantkilos, 1, 'de_DE') FROM listaprecios WHERE k_listaprecios = %s"
                ncursor.execute(query, (id, ))
                productos = ncursor.fetchall()
                query = """SELECT JSON_OBJECT('id', users.k_users, 'vendedor', CONCAT(n_nombre, ' ', n_apellido)) FROM vendedor_listaprecios, users
                WHERE vendedor_listaprecios.k_users = users.k_users AND k_listaprecios = %s"""
                ncursor.execute(query, (id, ))
                vendedor = ncursor.fetchall()
                if not lp:
                    return [[
                        'No se encontró la lista de precio',
                        productos if productos else "No se encontró productos en la lista de precios",
                        vendedor if vendedor else "No se encontró vendedor asociado a la lista de precios"
                        ], False]
                return [[
                    lp,
                    productos if productos else "No se encontró productos en la lista de precios",
                    vendedor if vendedor else "No se encontró vendedor asociado a la lista de precios"
                    ], True]
        except mysql.connector.Error as error:
            print('Consultar lista de precio Error: '+str(error))
            return ['Falló la consulta de lista de precio', False]

    def consultar_data_zona(self, id_zona, mes):
        '''
        Consulta la zona
        Args
            id: int
        '''
        try:
            print('consultar_data_zona')
            # Declaramos las variables que pueden o no mutar
            año = datetime.datetime.now().strftime('%Y')
            presupuesto_obj = {
                "mes": 0,
                "bimestre": 0,
            }
            alcanzado_obj = {
                "mes": {
                    "pesos": 0,
                    "kg": 0,    
                },
                "bimestre": {
                    "pesos": 0,
                    "kg": 0,
                },
            }
            ncursor = self.login_database()
            query = """SELECT k_zona, n_zona FROM zona WHERE k_zona = %s AND b_active = 1"""
            ncursor.execute(query, (id_zona, ))
            zona = ncursor.fetchone()
            # Departamentos
            query = """SELECT departamento.k_departamento, n_departamento FROM zona_departamento, departamento WHERE k_zona = %s
            AND zona_departamento.k_departamento = departamento.k_departamento"""
            ncursor.execute(query, (id_zona, ))
            departamentos = ncursor.fetchall()
            # Vendedor
            query = """SELECT users.k_users, CONCAT(n_nombre, " ", n_apellido) FROM zona_vendedor, users WHERE k_zona = %s
            AND zona_vendedor.k_users = users.k_users"""
            ncursor.execute(query, (id_zona, ))
            vendedor = ncursor.fetchone()
            # Presupuesto
            mes_impar = False
            if mes % 2 == 0:
                mes = mes - 1
            else:
                mes_impar = True
                mes = mes
            query = """
            SELECT Q3.q_mes, q_presupuesto, totalpesos, totalkg FROM (SELECT MONTH(f_venta_facturado) AS mes, SUM(totalpesospedido) AS totalpesos, SUM(totalkgpedidos) AS totalkg FROM (
                SELECT pedidos.k_venta, pedidos.k_users, pedidos.k_cliente, f_venta_facturado,
                SUM(q_valortotal) AS totalpesospedido, SUM(q_totalkilos) AS totalkgpedidos,
                clients.k_zona
                FROM pedidos, venta, clients
                WHERE pedidos.k_venta = venta.k_venta
                AND pedidos.k_cliente = clients.k_cliente
                AND venta.k_cliente = clients.k_cliente
                AND pedidos.b_active = 1
                AND k_zona = %s
                AND MONTH(f_venta_facturado) IN (%s,%s)
                AND YEAR(f_venta_facturado) = %s
                GROUP BY pedidos.k_venta
                ) AS Q1
            GROUP BY mes) AS Q2
            RIGHT JOIN (
            SELECT q_mes, q_presupuesto FROM presupuesto_zonas WHERE k_zona = %s AND q_mes IN (%s,%s)) AS Q3 ON Q2.mes = Q3.q_mes;"""
            if mes % 2 == 0:
                ncursor.execute(query, (id_zona, int(mes) - 1, int(mes), año, id_zona, int(mes) - 1, int(mes),))
            else:
                ncursor.execute(query, (id_zona, int(mes), int(mes) + 1, año, id_zona, int(mes), int(mes) + 1,))
            presupuesto = ncursor.fetchall()

            if presupuesto:
                presupuesto_bimestre = reduce(lambda acum, data: acum + (int(data[1]) if data[1] else 0), presupuesto, 0)
                totalpesos_bimestre = reduce(lambda acum, data: acum + (int(data[2]) if data[2] else 0), presupuesto, 0)
                totalkg_bimestre = reduce(lambda acum, data: acum + (int(data[3]) if data[3] else 0), presupuesto, 0)

                presupuesto_obj["mes"] = presupuesto[0][1] if mes_impar else presupuesto[1][1]
                presupuesto_obj["bimestre"] = presupuesto_bimestre

                alcanzado_obj["mes"]["pesos"] = presupuesto[0][2] if mes_impar else presupuesto[1][2]
                alcanzado_obj["mes"]["kg"] = presupuesto[0][3] if mes_impar else presupuesto[1][3]
                alcanzado_obj["bimestre"]["pesos"] = totalpesos_bimestre
                alcanzado_obj["bimestre"]["kg"] = totalkg_bimestre
            # Rendimiento anual
            ncursor.execute("SET lc_time_names = 'es_ES'")
            query = """
            SELECT MONTHNAME(f_venta) AS mes, SUM(totalpedido) AS totalpesos, SUM(totalkgpedidos) AS totalkg FROM (
                SELECT pedidos.k_venta, pedidos.k_users, pedidos.k_cliente, f_venta, SUM(q_valortotal) AS totalpedido,
                SUM(q_totalkilos) AS totalkgpedidos, clients.k_zona
                FROM pedidos, venta, clients
                WHERE pedidos.k_venta = venta.k_venta
                AND pedidos.k_cliente = clients.k_cliente
                AND venta.k_cliente = clients.k_cliente
                AND k_zona = %s
                GROUP BY pedidos.k_venta) AS Q1
            WHERE YEAR(f_venta) = %s
            GROUP BY mes;
            """
            ncursor.execute(query, (id_zona, año, ))
            rendimiento = ncursor.fetchall()
            return [[zona, departamentos, vendedor, presupuesto_obj, alcanzado_obj, rendimiento], True] if zona else ['No se encontró la zona', False]
        except mysql.connector.Error as error:
            print('Consultar zona Error: ' +str(error))
            return ['Falló la consulta de zona', False]


    def consultar_pedidos_cliente(self, idCliente, limit, offset):
        '''
        Devuelve los pedidos de un cliente en el año
        Args:
            idCliente: ID int
            limit: int
            offset: int
        '''
        try:
            print('consultar_pedidos_cliente')
            ncursor = self.login_database()
            # Total pedidos
            query = "SELECT COUNT(k_venta) FROM pedidos WHERE k_cliente = %s"
            ncursor.execute(query, (idCliente, ))
            total_pedidos = ncursor.fetchone()[0]
            query = """
            SELECT pedidos.k_venta, pedidos.k_users, 
            DATE_FORMAT(f_venta,'%%e/%%m/%%Y'), FORMAT(SUM(q_valortotal), 0, 'de_DE') AS totalpesos
            FROM pedidos, venta
            WHERE pedidos.k_venta = venta.k_venta
            AND pedidos.k_cliente = %s
            AND pedidos.b_active = 1
            GROUP BY pedidos.k_venta ORDER BY pedidos.k_venta DESC LIMIT %s OFFSET %s;
            """
            ncursor.execute(query, (idCliente, limit, offset))
            result = ncursor.fetchall()
            return [[result, total_pedidos], True] if result else [[[], 0], False]
        except mysql.connector.Error as error:
            print('Consultar pedidos cliente Error: ' +str(error))
            return [[[], 0], False]

    def consultar_cliente(self, id):
        '''
        Devuelve la información de un cliente
        '''
        try:
            print('consultar_cliente')
            # Información del cliente
            año = datetime.datetime.now().strftime('%Y')
            ncursor = self.login_database()
            # Rendimiento anual
            ncursor.execute("SET lc_time_names = 'es_ES'")
            query = """
            SELECT JSON_OBJECT(
                'id', Q1.k_cliente, 
                'name', n_cliente, 
                'email', n_correo, 
                'address', n_direccion, 
                'department', Q1.k_departamento, 
                'nameDepartment', Q1.n_departamento, 
                'city', n_ciudad, 
                'phone', q_telefono, 
                'phone2', q_telefono2, 
                'zone', Q1.k_zona, 
                'nameZone', Q1.n_zona, 
                'favorite', b_favorite
            ) FROM (
                SELECT clients.k_cliente, n_cliente, n_correo, n_direccion, departamento.k_departamento, 
                departamento.n_departamento, n_ciudad, q_telefono, q_telefono2, zona.k_zona, zona.n_zona
                FROM clients, departamento, zona
                WHERE clients.k_departamento = departamento.k_departamento
                AND clients.k_zona = zona.k_zona
                AND clients.k_cliente = %s) 
            AS Q1 LEFT JOIN (
                SELECT k_cliente, IF(clientes_favoritos.k_cliente, 'true', 'false') AS 'b_favorite' FROM clientes_favoritos
            ) AS Q2 ON Q1.k_cliente = Q2.k_cliente
            """
            ncursor.execute(query, (id,))
            result = ncursor.fetchone()
            if result:
                result = result[0]
                # Pedidos por mes
                query = """
                SELECT MONTHNAME(f_venta) AS mes, CONVERT(SUM(q_valortotal), DECIMAL) AS totalfact FROM pedidos, venta
                WHERE pedidos.k_venta = venta.k_venta
                AND pedidos.k_cliente = %s 
                AND pedidos.b_active = 1
                AND YEAR(f_venta) = %s
                GROUP BY mes;
                """
                ncursor.execute(query, (id, año, ))
                pesosfact_anio = ncursor.fetchall()
                # Pedidos año
                return [[json.loads(result), pesosfact_anio], True]
            return [['No se encontró el cliente', []], False]
        except mysql.connector.Error as error:
            print('Consultar cliente Error: ' +str(error))
            return ['Falló la consulta de cliente.', False]

    def consultar_zona(self, id):
        '''
        Consulta una zona
        Args:
            id: str
        '''
        try:
            print('consultar_zona')
            ncursor = self.login_database()
            query = "SELECT JSON_OBJECT('id', k_zona, 'zone', n_zona) FROM zona WHERE k_zona = %s"
            ncursor.execute(query, (id, ))
            result = ncursor.fetchone()
            return [result, True] if result else ['No se encontró la zona', False]
        except mysql.connector.Error as error:
            print('Consultar zona Error: ' +str(error))
            return ['Falló la consulta de zona.', False]

    def consultar_zonas(self, context=None):
        '''
        Devuelve todas las zonas registradas en el sistema
        '''
        try:
            print('consultar_zonas')
            ncursor = self.login_database()
            if context:
                query = "SELECT k_zona, n_zona FROM zona"
            else:
                query = "SELECT JSON_OBJECT('id', k_zona, 'zone', n_zona) FROM zona"
            ncursor.execute(query)
            result = ncursor.fetchall()
            return [result, True] if result else ['No se encontró zonas registradas', False]
        except mysql.connector.Error as error:
            print('Consultar zonas Error: ' +str(error))
            return ['Falló la consulta de zonas.', False]

    def consultar_departamentos(self):
        '''
        Devuelve todos los departamentos registrados
        '''
        try:
            print('consultar_departamentos')
            ncursor = self.login_database()
            query = """SELECT JSON_OBJECT('id', k_departamento, 'department', n_departamento) FROM departamento"""
            ncursor.execute(query)
            result = ncursor.fetchall()
            return [result, True] if result else [[], False]
        except mysql.connector.Error as error:
            print('Consultar departamentos Error: ' +str(error))
            return ['Falló la consulta de departamentos.', False]

    def consultar_ciudades(self, id):
        '''
        Devuelve todas las ciudades
        Args: 
            id: string
        '''
        try:
            print('consultar_ciudades')
            ncursor = self.login_database()
            query = """SELECT JSON_OBJECT('id', departamento.k_departamento, 'department', n_departamento, 'city', n_ciudad)
            FROM departamento, ciudad WHERE departamento.k_departamento = ciudad.k_departamento
            AND departamento.k_departamento = %s"""
            ncursor.execute(query, (id,))
            result = ncursor.fetchall()
            return [result, True] if result else [[], False]
        except mysql.connector.Error as error:
            print('Consultar ciudades Error: ' +str(error))
            return ['Falló la consulta de ciudades.', False]

    def consultar_clientes(self, limit, offset, filter):
        '''
        Devuelve los clientes registrados
        Args:
            limit: Cantidad de registros a devolver
            offset: Registro inicial
            filter: Filtro de busqueda
        '''
        try:
            print('consultar_clientes')
            ncursor = self.login_database()
            if filter:
                filter = '%' + filter + '%'
                #Total clientes
                query = """
                SELECT COUNT(k_cliente) FROM clients, departamento, zona
                WHERE clients.k_departamento = departamento.k_departamento
                AND clients.k_zona = zona.k_zona AND (
                LOWER(REPLACE(k_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(n_correo, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(n_direccion, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(departamento.n_departamento, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(n_ciudad, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(q_telefono, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(q_telefono2, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(zona.n_zona, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')))"""
                ncursor.execute(query, (filter, filter, filter, filter, filter, filter, filter, filter, filter,))
                total_clientes = ncursor.fetchone()[0]
                query = """
                SELECT k_cliente, n_cliente, n_correo, n_direccion, departamento.n_departamento, 
                n_ciudad, q_telefono, q_telefono2, zona.n_zona FROM clients, departamento, zona
                WHERE clients.k_departamento = departamento.k_departamento
                AND clients.k_zona = zona.k_zona AND (
                LOWER(REPLACE(k_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(n_correo, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(n_direccion, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(departamento.n_departamento, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(n_ciudad, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(q_telefono, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(q_telefono2, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                OR LOWER(REPLACE(zona.n_zona, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))) LIMIT %s OFFSET %s"""
                ncursor.execute(query, (filter, filter, filter, filter, filter, filter, filter, filter, filter, limit, offset,))
                result = ncursor.fetchall()
                if result:
                    return [[total_clientes, result], True]
                return ['No se encontró clientes registrados', False]
            else:
                # Total clientes
                query = "SELECT COUNT(*) FROM clients"
                ncursor.execute(query)
                total_clientes = ncursor.fetchone()[0]
                query = """
                SELECT k_cliente, n_cliente, n_correo, n_direccion, departamento.n_departamento, 
                n_ciudad, q_telefono, q_telefono2, zona.n_zona FROM clients, departamento, zona
                WHERE clients.k_departamento = departamento.k_departamento
                AND clients.k_zona = zona.k_zona LIMIT %s OFFSET %s"""
                ncursor.execute(query, (limit, offset,))
                result = ncursor.fetchall()
                if result:
                    return [[total_clientes, result], True]
                return ['No se encontró clientes registrados', False]
        except mysql.connector.Error as error:
            print('Consultar clientes Error: ' +str(error))
            return ['Falló la consulta de clientes.', False]

    def consultar_listas_precios(self, category):
        '''
        Devuelve las listas de precios registradas
        Args:
            category: Categoria de la lista de precios str
        '''
        try:
            print('consultar_listas_precios')
            ncursor = self.login_database()
            if category == "Bodegas":
                query = "SELECT k_listaprecios, n_nombre, n_marca FROM namelp_bodegas"
                ncursor.execute(query)
                result = ncursor.fetchall()
                return [result, True] if result else ['No se encontró listas de precios registradas', False]
            query = "SELECT k_listaprecios, n_nombre, n_marca FROM namelp"
            ncursor.execute(query)
            result = ncursor.fetchall()
            return [result, True] if result else ['No se encontró listas registradas', False]
        except mysql.connector.Error as error:
            print('Consultar listas precios Error: ' +str(error))
            return ['Falló la consulta de listas de precios.', False]

    def ventas_pesos_kilos_mes(self, mes):
        '''
        Devuelve el total de pesos y kilos facturados desde el 1 de cada mes y hasta
        el dia actual del mes
        '''
        try:
            print('ventas_pesos_kilos_mes')
            # 1. mes
            dia = 1
            año = datetime.datetime.now().strftime('%Y')
            fecha0_ = datetime.datetime(int(año) - 1, 1, int(dia))
            fecha0_ = fecha0_.strftime('%Y-%m-%d')
            today = datetime.datetime.now()

            fecha0 = datetime.datetime(int(año), int(mes), int(dia))
            fecha0 = fecha0.strftime('%Y-%m-%d')
            dia2 = calendar.monthrange(int(año), int(mes))[1]
            fecha1 = datetime.datetime(int(año), int(mes), dia2)
            fecha1 = fecha1.strftime('%Y-%m-%d')

            ncursor = self.login_database()
            query = """SELECT 
            FORMAT(SUM(subtotaldesp), 0, 'de_DE') AS totalpesosdesp,
            FORMAT(SUM(totalkilosdesp), 0, 'de_DE') AS totalkilosdesp,
            FORMAT(SUM(subtotal), 0, 'de_DE') AS totalpesosfact,
            FORMAT(SUM(totalkilos), 0, 'de_DE') AS totalkilosfact,
            FORMAT(ROUND(SUM(subtotal)/SUM(totalkilos), 0), 0, 'de_DE') AS vkilo
            FROM(
                SELECT venta.k_venta,
                SUM(venta.q_cantidad_despachada*q_vunitario) AS subtotaldesp,
                SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad_despachada) AS totalkilosdesp,
                SUM(venta.q_cantidad*q_vunitario) AS subtotal,
                SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad) AS totalkilos
                FROM venta, pedidos WHERE n_estadop1 = 'Facturado'
                AND venta.k_venta = pedidos.k_venta
                AND venta.k_users = pedidos.k_users
                AND pedidos.f_venta_facturado BETWEEN %s AND %s GROUP BY k_venta
            ) AS tabla;"""
            ncursor.execute(query, (fecha0, fecha1,))
            ventas_resumen = ncursor.fetchone()
            query = """SELECT FORMAT(SUM(subtotal), 0, 'de_DE') AS totalpend, FORMAT(SUM(totalkgpend), 0, 'de_DE') AS totalkgpend FROM(
                SELECT venta.k_venta, pedidos.f_venta, SUM(venta.q_valortotal) AS subtotal, SUM(q_totalkilos) as totalkgpend 
                FROM venta, pedidos WHERE n_estadop0 = 'Autorizado' AND n_estadop1 = 'Por facturar' AND (
                    n_estadop2 = "Por despachar" OR
                    n_estadop2 = "Incompleto"
                )
                AND venta.k_cliente = pedidos.k_cliente AND venta.k_venta = pedidos.k_venta 
                AND pedidos.b_active = 1
                AND venta.k_users = pedidos.k_users AND f_venta BETWEEN %s AND %s GROUP BY k_venta ORDER BY f_venta DESC
            ) as tabla;"""
            ncursor.execute(query, (fecha0_, today,))
            ventas_resumen = ventas_resumen + ncursor.fetchone()
            query = '''
            SELECT Q1.k_zona, Q1.n_zona,
            FORMAT(pesosfact, 0, 'de_DE') as pesosfacturados,
            FORMAT(pesosdesp, 0, 'de_DE') as pesosdespachados,
            FORMAT(kilosfact, 0, 'de_DE') as kilosfacturados,
            FORMAT(kilosdesp, 0, 'de_DE') as kilosdespachados,
            FORMAT(kilospend, 0, 'de_DE') as kilospendientes,
            FORMAT(ROUND(pesosfact/kilosfact, 0), 0, 'de_DE') AS valorkg
            FROM (
                SELECT clients.k_zona, n_zona,
                SUM(venta.q_cantidad*q_vunitario) AS pesosfact,
                SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad) AS kilosfact,
                SUM(venta.q_cantidad_despachada*q_vunitario) AS pesosdesp,
                SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad_despachada) AS kilosdesp
                FROM venta, pedidos, clients, zona
                WHERE venta.k_venta = pedidos.k_venta
                AND venta.k_users = pedidos.k_users
                AND clients.k_cliente = pedidos.k_cliente
                AND clients.k_cliente = venta.k_cliente
                AND clients.k_zona = zona.k_zona
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Facturado"
                AND pedidos.b_active = 1
                AND pedidos.f_venta_facturado BETWEEN %s AND %s
                GROUP BY clients.k_zona
            ) AS Q1 LEFT JOIN
            (
                SELECT clients.k_zona, n_zona, SUM(q_valortotal) AS pesospend, SUM(q_totalkilos) AS kilospend
                FROM venta, pedidos, clients, zona
                WHERE venta.k_venta = pedidos.k_venta
                AND venta.k_users = pedidos.k_users
                AND clients.k_cliente = pedidos.k_cliente
                AND clients.k_cliente = venta.k_cliente
                AND clients.k_zona = zona.k_zona
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Por facturar"
                AND (
                    pedidos.n_estadop2 = "Por despachar" OR
                    pedidos.n_estadop2 = "Incompleto"
                )
                AND pedidos.f_venta_autorizado BETWEEN %s AND %s
                AND pedidos.b_active = 1
                GROUP BY clients.k_zona
            ) AS Q2 ON Q1.k_zona = Q2.k_zona ORDER BY pesosfacturados DESC;
            '''
            ncursor.execute(query, (fecha0, fecha1, fecha0_, fecha1))
            ventas_vendedor_resumen_mes = ncursor.fetchall()

            # 2. bimestre bimester
            dia = 1
            if mes % 2 == 0:
                mes2 = mes
                mes = mes - 1
            else:
                mes = mes
                mes2 = mes + 1

            año = datetime.datetime.now().strftime('%Y')
            fecha0 = datetime.datetime(int(año), int(mes), int(dia))
            fecha0 = fecha0.strftime('%Y-%m-%d')
            dia2 = calendar.monthrange(int(año), int(mes2))[1]
            fecha1 = datetime.datetime(int(año), int(mes2), dia2)
            fecha1 = fecha1.strftime('%Y-%m-%d')
            ncursor.execute(query, (fecha0, fecha1, fecha0_, today,))
            ventas_vendedor_resumen_bimester = ncursor.fetchall()

            query = """
            SELECT 
            FORMAT(SUM(subtotaldesp), 0, 'de_DE') AS totalpesosdesp, 
            FORMAT(SUM(totalkilosdesp), 0, 'de_DE') AS totalkilosdesp, 
            FORMAT(SUM(subtotal), 0, 'de_DE') AS totalpesosfact, 
            FORMAT(SUM(totalkilos), 0, 'de_DE') AS totalkilosfact, 
            FORMAT(ROUND(SUM(subtotal)/SUM(totalkilos), 0), 0, 'de_DE') AS vkilo
            FROM(
                SELECT venta.k_venta, 
                SUM(venta.q_cantidad*venta.q_vunitario) AS subtotal,
                SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad) AS totalkilos,
                SUM(venta.q_cantidad_despachada*venta.q_vunitario) AS subtotaldesp,
                SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad_despachada) AS totalkilosdesp
                FROM venta, pedidos WHERE n_estadop1 = 'Facturado' AND venta.k_venta = pedidos.k_venta
                AND venta.k_users = pedidos.k_users AND pedidos.f_venta_facturado BETWEEN %s AND %s GROUP BY k_venta
            ) AS tabla;"""
            ncursor.execute(query, (fecha0, fecha1,))
            ventas_resumen_bimester = ncursor.fetchone()
            query = """SELECT FORMAT(SUM(subtotal), 0, 'de_DE') AS totalpend, FORMAT(SUM(totalkgpend), 0, 'de_DE') AS totalkgpend 
            FROM(SELECT venta.k_venta, pedidos.f_venta, SUM(venta.q_valortotal) AS subtotal, SUM(q_totalkilos) as totalkgpend 
            FROM venta, pedidos WHERE n_estadop0 = 'Autorizado' AND n_estadop1 = 'Por Facturar' 
            AND venta.k_cliente = pedidos.k_cliente AND venta.k_venta = pedidos.k_venta AND venta.k_users = pedidos.k_users 
            AND f_venta BETWEEN %s AND %s GROUP BY k_venta ORDER BY f_venta DESC) as tabla;"""
            ncursor.execute(query, (fecha0_, today,))
            ventas_resumen_bimester = ventas_resumen_bimester + ncursor.fetchone()
            if ventas_resumen:
                return [[ventas_resumen, ventas_vendedor_resumen_mes, ventas_vendedor_resumen_bimester, ventas_resumen_bimester], True]
            return [['No se han registrado ventas'], False]
        except mysql.connector.Error as error:
            print('Consultar ventas pesos kilo x mes Error: ' + str(error))
            return ['Falló la consulta de ventas pesos kilo x mes', False]

    def ventas_pesos_kilos_anio(self):
        '''
        Devuelve el total de pesos y kilos facturados desde el 1 de Enero y hasta
        el dia actual
        '''
        try:
            print('ventas_pesos_kilos_anio')
            dia = 1
            mes = 1
            # Fecha actual
            año = datetime.datetime.now().strftime('%Y') 
            fecha0 = datetime.datetime(int(año), int(mes), int(dia))
            fecha0 = fecha0.strftime('%Y-%m-%d')
            fecha1 = datetime.datetime.now()
            fecha1 = fecha1.strftime('%Y-%m-%d')

            # Fecha inicio del programa
            año2 = 2021
            fecha2 = datetime.datetime(int(año2), int(mes), int(dia))
            ncursor = self.login_database()
            query = """
            SELECT JSON_OBJECT('totalpesosfact', totalpesosfact, 'totalkilosfact', totalkilosfact, 'totalpend', totalpend, 'totalkgpend', totalkgpend, 'valorkg', valorkg) FROM (
                SELECT FORMAT(SUM(subtotal), 0, 'de_DE') AS totalpesosfact, FORMAT(SUM(totalkilos), 0, 'de_DE') AS totalkilosfact, 
                FORMAT(SUM(subtotal)/SUM(totalkilos), 0, 'de_DE') as valorkg
                FROM(
                    SELECT venta.k_venta, SUM(venta.q_vunitario*venta.q_cantidad_despachada) AS subtotal, 
                    SUM((venta.q_totalkilos/venta.q_cantidad) * venta.q_cantidad_despachada) AS totalkilos 
                    FROM venta, pedidos WHERE n_estadop1 = 'Facturado' 
                    AND venta.k_venta = pedidos.k_venta AND venta.k_users = pedidos.k_users 
                    AND pedidos.f_venta_facturado BETWEEN %s AND %s GROUP BY k_venta
                    ) AS Q1
            ) AS Q3, (
                SELECT FORMAT(SUM(subtotal), 0, 'de_DE') AS totalpend, FORMAT(SUM(totalkgpend), 0, 'de_DE') AS totalkgpend FROM(
                    SELECT venta.k_venta, pedidos.f_venta, SUM(venta.q_valortotal) AS subtotal, 
                    SUM(q_totalkilos) as totalkgpend 
                    FROM venta, pedidos
                    WHERE n_estadop0 = 'Autorizado' AND n_estadop1 = 'Por Facturar' 
                    AND venta.k_cliente = pedidos.k_cliente AND venta.k_venta = pedidos.k_venta 
                    AND venta.k_users = pedidos.k_users AND f_venta BETWEEN %s AND %s 
                    AND pedidos.b_active = 1
                    GROUP BY k_venta ORDER BY f_venta DESC
                    ) AS Q2
            ) AS Q4;
            """
            ncursor.execute(query, (fecha0, fecha1, fecha2, fecha1,))
            resumen_anio = ncursor.fetchone()
            query = """
            SELECT Q2.k_zona, Q2.n_zona, FORMAT(kilospend, 0, 'de_DE'), FORMAT(pesospend, 0, 'de_DE') FROM (
                SELECT clients.k_zona, n_zona, SUM(venta.q_vunitario*venta.q_cantidad_despachada) AS pesosfact, 
                SUM((venta.q_totalkilos/q_cantidad) * venta.q_cantidad_despachada) AS kilosfact FROM venta, pedidos, clients, zona
                WHERE venta.k_venta = pedidos.k_venta
                AND venta.k_users = pedidos.k_users
                AND clients.k_cliente = pedidos.k_cliente
                AND clients.k_cliente = venta.k_cliente
                AND clients.k_zona = zona.k_zona
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Facturado"
                AND pedidos.f_venta_facturado BETWEEN %s AND %s
                AND pedidos.b_active = 1
                GROUP BY clients.k_zona
            ) AS Q1 RIGHT JOIN
            (
                SELECT clients.k_zona, n_zona, SUM(q_valortotal) AS pesospend, SUM(q_totalkilos) AS kilospend FROM venta, pedidos, clients, zona
                WHERE venta.k_venta = pedidos.k_venta
                AND venta.k_users = pedidos.k_users
                AND clients.k_cliente = pedidos.k_cliente
                AND clients.k_cliente = venta.k_cliente
                AND clients.k_zona = zona.k_zona
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Por facturar"
                AND pedidos.f_venta BETWEEN %s AND %s
                AND pedidos.b_active = 1
                GROUP BY clients.k_zona
            ) AS Q2 ON Q1.k_zona = Q2.k_zona
            """
            ncursor.execute(query, (fecha0, fecha1, fecha2, fecha1,))
            zonas_pendientes_anio = ncursor.fetchall()
            query = """
            SELECT Q1.k_zona, Q1.n_zona, FORMAT(kilosfact, 0, 'de_DE'), FORMAT(pesosfact, 0, 'de_DE'),
            FORMAT(ROUND(pesosfact/kilosfact, 0), 0, 'de_DE') AS valorkg FROM (
                SELECT clients.k_zona, n_zona, SUM(venta.q_vunitario*venta.q_cantidad_despachada) AS pesosfact, 
                SUM((venta.q_totalkilos/q_cantidad) * venta.q_cantidad_despachada) AS kilosfact FROM venta, pedidos, clients, zona
                WHERE venta.k_venta = pedidos.k_venta
                AND venta.k_users = pedidos.k_users
                AND clients.k_cliente = pedidos.k_cliente
                AND clients.k_cliente = venta.k_cliente
                AND clients.k_zona = zona.k_zona
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Facturado"
                AND pedidos.f_venta_facturado BETWEEN %s AND %s
                AND pedidos.b_active = 1
                GROUP BY clients.k_zona
            ) AS Q1 LEFT JOIN
            (
                SELECT clients.k_zona, n_zona, SUM(q_valortotal) AS pesospend, SUM(q_totalkilos) AS kilospend FROM venta, pedidos, clients, zona
                WHERE venta.k_venta = pedidos.k_venta
                AND venta.k_users = pedidos.k_users
                AND clients.k_cliente = pedidos.k_cliente
                AND clients.k_cliente = venta.k_cliente
                AND clients.k_zona = zona.k_zona
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Por facturar"
                AND pedidos.f_venta BETWEEN %s AND %s
                AND pedidos.b_active = 1
                GROUP BY clients.k_zona
            ) AS Q2 ON Q1.k_zona = Q2.k_zona
            """
            ncursor.execute(query, (fecha0, fecha1, fecha0, fecha1,))
            zonas_resumen_anio = ncursor.fetchall()
            ncursor.execute("SET lc_time_names = 'es_ES';")
            query = """
            SELECT MONTHNAME(STR_TO_DATE(mes,'%%m')), FORMAT(SUM(totalkgfact), 0, 'de_DE') AS totalkgfactmes,
            FORMAT(SUM(totalkgbnf), 0, 'de_DE') AS totalkgbnfmes, FORMAT(SUM(subtotal), 0, 'de_DE') AS totalmes, totalpresupuesto FROM(
                SELECT venta.k_venta,clients.k_zona, venta.k_cliente, MONTH(pedidos.f_venta_facturado) AS mes, SUM(venta.q_vunitario*venta.q_cantidad_despachada) AS subtotal, 
                SUM(q_valortotalb) AS subtotaliva, SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad_despachada) AS totalkgfact, SUM(q_totalkilosb) AS totalkgbnf, pedidos.n_estadop1 
                FROM venta, pedidos, clients 
                WHERE n_estadop1 = 'Facturado' AND venta.k_cliente = pedidos.k_cliente AND venta.k_venta = pedidos.k_venta AND venta.k_users = pedidos.k_users AND pedidos.k_cliente = clients.k_cliente 
                AND venta.k_cliente = clients.k_cliente AND pedidos.f_venta_facturado BETWEEN %s AND %s GROUP BY venta.k_venta
                AND pedidos.b_active = 1
            ) AS tabla, clients, (
                SELECT q_mes, FORMAT(SUM(q_presupuesto), 0, 'de_DE') AS totalpresupuesto FROM presupuesto_zonas GROUP BY q_mes
            ) AS tabla2 WHERE tabla.k_cliente = clients.k_cliente AND mes = tabla2.q_mes GROUP BY mes ORDER BY mes DESC
            """
            ncursor.execute(query, (fecha0, fecha1,))
            mes_resumen_anio = ncursor.fetchall()
            return [[resumen_anio, zonas_resumen_anio, mes_resumen_anio, zonas_pendientes_anio], True]
        except mysql.connector.Error as error:
            print('Consultar ventas pesos kilo x año Error: ' +str(error))
            return ['Falló la consulta de ventas pesos kilo x año', False]
    
    def consultar_resumen_ventas_mes(self):
        '''
        Consulta  el resumen de ventas por mes
        ''' 
        try:
            print('consultar_resumen_ventas_mes')
            dia = 1
            mes = 1
            año = datetime.datetime.now().strftime('%Y')
            fecha0 = datetime.datetime(int(año), int(mes), int(dia))
            fecha0 = fecha0.strftime('%Y-%m-%d')
            dia2 = 31
            mes2 = 12
            fecha1 = datetime.datetime(int(año), int(mes2), int(dia2))
            fecha1 = fecha1.strftime('%Y-%m-%d')
            ncursor = self.login_database()
            query = '''
            SELECT mes, SUM(totalkgfact) AS totalkgfactmes, SUM(totalkgbnf) AS totalkgbnfmes, SUM(subtotal) AS totalmes, totalpresupuesto FROM(
                SELECT venta.k_venta,clients.k_zona, venta.k_cliente, MONTH(pedidos.f_venta_facturado) AS mes, SUM(venta.q_valortotal) AS subtotal, 
                SUM(q_valortotalb) AS subtotaliva, SUM(q_totalkilos) AS totalkgfact, SUM(q_totalkilosb) AS totalkgbnf, pedidos.n_estadop1 
                FROM venta, pedidos, clients 
                WHERE n_estadop1 = 'Facturado' AND venta.k_cliente = pedidos.k_cliente AND venta.k_venta = pedidos.k_venta AND venta.k_users = pedidos.k_users AND pedidos.k_cliente = clients.k_cliente 
                AND venta.k_cliente = clients.k_cliente AND pedidos.f_venta_facturado BETWEEN %s AND %s GROUP BY venta.k_venta)
            AS tabla, clients, (SELECT q_mes, SUM(q_presupuesto) AS totalpresupuesto FROM presupuesto_zonas GROUP BY q_mes) AS tabla2 
            WHERE tabla.k_cliente = clients.k_cliente AND mes = tabla2.q_mes GROUP BY mes ORDER BY mes DESC;
            '''
            ncursor.execute(query, (fecha0, fecha1,))
            resumen_ventas = ncursor.fetchall()
            if resumen_ventas:
                result = []
                for data in resumen_ventas:
                    result.append((data[0],float(data[1]),float(data[2]),float(data[3]),float(data[4])))
                return [result, True]
            return ['No registra resumén de ventas.', False]
        except mysql.connector.Error as error:
            print('Consultar resumen ventas mes Error: ' +str(error))
            return ['Falló la consulta de ventas resumen mes', False]

    def consultar_rendimiento_zonas(self, id_vendedor, mes):
        '''
        Consulta el presupuesto bimestral del vendedor
        Si el mes es par devuelve la meta del mes anterior
        Args
            id_vendedor: ID INT Cédula del vendedor
            mes: INT mes indica el mes
        '''
        try:
            print('consultar_rendimiento_zonas')
            dia = 1
            año = datetime.datetime.now().strftime('%Y')
            if mes % 2 == 0:
                fecha0 = datetime.datetime(int(año), int(mes - 1), int(dia))
                fecha0 = fecha0.strftime('%Y-%m-%d')
                dia2 = calendar.monthrange(int(año), int(mes))[1]
                fecha1 = datetime.datetime(int(año), int(mes), dia2)
                fecha1 = fecha1.strftime('%Y-%m-%d')
            else:
                fecha0 = datetime.datetime(int(año), int(mes), int(dia))
                fecha0 = fecha0.strftime('%Y-%m-%d')
                dia2 = calendar.monthrange(int(año), int(mes + 1))[1]
                fecha1 = datetime.datetime(int(año), int(mes + 1), dia2)
                fecha1 = fecha1.strftime('%Y-%m-%d')
            # 1. Bimestre
            ncursor = self.login_database()
            query = """
            SELECT JSON_OBJECT('nombreZona', Q4.n_zona,'ventas',ventas,'meta',Q4.meta) FROM (SELECT Q1.k_zona, n_zona, ventas, meta FROM (SELECT tabla.k_zona, n_zona, SUM(total1) AS ventas FROM (
                SELECT venta.k_venta, clients.k_zona, pedidos.k_cliente, SUM(venta.q_valortotal) AS total1
                FROM pedidos, venta, clients
                WHERE pedidos.k_venta = venta.k_venta
                AND pedidos.k_cliente = clients.k_cliente
                AND  pedidos.k_users = %s 
                AND pedidos.b_active = 1
                AND pedidos.f_venta_facturado BETWEEN %s AND %s
                GROUP BY venta.k_venta
            ) AS tabla, zona
            WHERE tabla.k_zona = zona.k_zona
            GROUP BY tabla.k_zona) AS Q1,
            (SELECT zona_vendedor.k_zona, SUM(q_presupuesto) AS meta FROM presupuesto_zonas, zona_vendedor 
            WHERE presupuesto_zonas.k_zona = zona_vendedor.k_zona
            AND zona_vendedor.k_users = %s 
            AND q_mes IN (%s, %s) GROUP BY zona_vendedor.k_zona) AS Q2
            WHERE Q1.k_zona = Q2.k_zona) AS Q3 RIGHT JOIN (SELECT zona.k_zona, n_zona, SUM(q_presupuesto) as meta  FROM zona_vendedor, zona, presupuesto_zonas
            WHERE k_users = %s
            AND presupuesto_zonas.k_zona = zona.k_zona
            AND zona.k_zona = zona_vendedor.k_zona
            AND presupuesto_zonas.q_mes IN (%s, %s) GROUP BY zona.k_zona) AS Q4 ON Q3.k_zona = Q4.k_zona
            """
            if mes % 2 == 0:
                ncursor.execute(query, (id_vendedor, fecha0, fecha1, id_vendedor, int(mes) - 1, int(mes), id_vendedor, int(mes) - 1, int(mes) ))
            else:
                ncursor.execute(query, (id_vendedor, fecha0, fecha1, id_vendedor, int(mes), int(mes) + 1, id_vendedor, int(mes), int(mes) + 1 ))
            bimestre = ncursor.fetchall()
            # 2. Mes
            año = datetime.datetime.now().strftime('%Y')
            fecha0 = datetime.datetime(int(año), int(mes), int(dia))
            fecha0 = fecha0.strftime('%Y-%m-%d')
            query = """
            SELECT JSON_OBJECT('nombreZona',Q4.n_zona,'ventas',ventas,'meta', Q4.meta) FROM (SELECT Q1.k_zona, n_zona, ventas, meta FROM (SELECT tabla.k_zona, n_zona, SUM(total1) AS ventas FROM (
                SELECT venta.k_venta, clients.k_zona, pedidos.k_cliente, SUM(venta.q_vunitario*q_cantidad) AS total1
                FROM pedidos, venta, clients
                WHERE pedidos.k_venta = venta.k_venta
                AND pedidos.k_cliente = clients.k_cliente
                AND  pedidos.k_users = %s
                AND pedidos.b_active = 1
                AND MONTH(pedidos.f_venta_facturado) = %s
                AND YEAR(pedidos.f_venta_facturado) = %s
                GROUP BY venta.k_venta
            ) AS tabla, zona
            WHERE tabla.k_zona = zona.k_zona
            GROUP BY tabla.k_zona) AS Q1,
            (SELECT zona_vendedor.k_zona, SUM(q_presupuesto) AS meta FROM presupuesto_zonas, zona_vendedor 
            WHERE presupuesto_zonas.k_zona = zona_vendedor.k_zona
            AND zona_vendedor.k_users = %s
            AND q_mes = %s GROUP BY zona_vendedor.k_zona) AS Q2
            WHERE Q1.k_zona = Q2.k_zona) AS Q3 RIGHT JOIN (SELECT zona.k_zona, n_zona, q_presupuesto as meta  FROM zona_vendedor, zona, presupuesto_zonas
            WHERE k_users = %s
            AND presupuesto_zonas.k_zona = zona.k_zona
            AND zona.k_zona = zona_vendedor.k_zona
            AND presupuesto_zonas.q_mes = %s) AS Q4 ON Q3.k_zona = Q4.k_zona
            """
            ncursor.execute(query, (id_vendedor, mes, año, id_vendedor, int(mes), id_vendedor, int(mes),))
            resumen_mes = ncursor.fetchall()
            mes = 1
            año = datetime.datetime.now().strftime('%Y')
            fecha0 = datetime.datetime(int(año), int(mes), int(dia))
            fecha0 = fecha0.strftime('%Y-%m-%d')
            fecha0_ = datetime.datetime(int(año) - 1, int(mes), int(dia))
            fecha0_ = fecha0_.strftime('%Y-%m-%d')
            dia2 = 31
            mes2 = 12
            fecha1 = datetime.datetime(int(año), int(mes2), int(dia2))
            fecha1 = fecha1.strftime('%Y-%m-%d')
            query = """
            SELECT JSON_OBJECT('pesosfact', tfacturado, 'tkilos', tkilos, 'pesospend', tpesospend, 'kilospend', tkilospend) FROM (
                SELECT SUM(venta.q_vunitario*q_cantidad) tfacturado, SUM((venta.q_totalkilos/venta.q_cantidad)*venta.q_cantidad) tkilos FROM venta, pedidos 
                WHERE pedidos.k_users = %s
                AND pedidos.k_venta = venta.k_venta
                AND pedidos.n_estadop1 = "Facturado"
                AND pedidos.b_active = 1
                AND pedidos.f_venta_facturado BETWEEN %s AND %s
            ) AS Q1,
            (
                SELECT SUM(q_valortotal) tpesospend, SUM(q_totalkilos) tkilospend FROM venta, pedidos 
                WHERE pedidos.k_users = %s
                AND pedidos.k_venta = venta.k_venta
                AND pedidos.n_estadop0 = "Autorizado"
                AND pedidos.n_estadop1 = "Por facturar"
                AND pedidos.b_active = 1
                AND pedidos.f_venta BETWEEN %s AND %s
            ) AS Q2
            """
            ncursor.execute(query, (id_vendedor, fecha0, fecha1, id_vendedor, fecha0_, fecha1, ))
            summary_seller = ncursor.fetchall()
            result = {
                'bimestre': bimestre,
                'mes': resumen_mes,
                'summarySeller': summary_seller
            }
            return [result, True]
        except mysql.connector.Error as error:
            print('Consultar presupuesto vendedor Error: ' +str(error))
            return ['Falló la consulta de presupuesto vendedor', False]

    def consultar_password(self, id_user):
        '''
        Consulta la contraseña del usuario
        '''
        try:
            print('consultar_password')
            ncursor = self.login_database()
            query = """SELECT o_password FROM users WHERE k_users = %s"""
            ncursor.execute(query, (id_user, ))
            password = ncursor.fetchone()[0]
            return [password, True]
        except mysql.connector.Error as error:
            print('Consultar password Error: ' +str(error))
            return ['Falló la consulta de password', False]

    def consultar_lp_seller(self, id_vendedor):
        '''
        Devuelve las listas de precios de un 
        vendedor
        Args:
            id_vendedor: CÉDULA
        '''
        try:
            print('consultar_lp_seller')
            ncursor = self.login_database()
            lps = []
            # Cargar L. Precios - Pedidos
            query = "SELECT k_users, k_listaprecios FROM vendedor_listaprecios WHERE k_users = %s"
            ncursor.execute(query, (id_vendedor,))
            result = ncursor.fetchall()
            if result:
                lps_array = []
                query = "SELECT k_listaprecios, n_nombre, n_marca FROM namelp WHERE k_listaprecios = %s"
                for lista_precios in result:
                    ncursor.execute(query, (lista_precios[1],))
                    product = ncursor.fetchone()
                    if product:
                        lps_array.append(product)
                lps.append(lps_array)
            # Cargar L. Precios - Bodegas
            query = "SELECT k_users, k_listaprecios FROM vendedor_listaprecios_bodegas WHERE k_users = %s"
            ncursor.execute(query, (id_vendedor,))
            result2 = ncursor.fetchall()
            if result2:
                lps_array2 = []
                query = "SELECT k_listaprecios, n_nombre, n_marca, n_link FROM namelp_bodegas WHERE k_listaprecios = %s"
                for lista_precios in result2:
                    ncursor.execute(query, (lista_precios[1],))
                    product = ncursor.fetchone()
                    if product:
                        lps_array2.append(product)
                lps.append(lps_array2)
            return [lps, True]
        except mysql.connector.Error as error:
            print('Consultar LP Seller Error: ' +str(error))
            return ['Falló la consulta de listas de precios de un vendedor.', False]

    def consultar_usuario(self, id):
        '''
        Consulta la información específica de un usuario
        Args:
            id: int
        '''
        try:
            print('consultar_usuario')
            ncursor = self.login_database()
            query = "SELECT JSON_OBJECT('id', k_users, 'name', n_nombre, 'lastname', n_apellido, 'email', n_correo, 'hierarchy', n_categoria) FROM users WHERE k_users = %s"
            ncursor.execute(query, (id, ))
            result = json.loads(ncursor.fetchone()[0])
            if result:
                return [result,True]
            return ['Usuario no encontrado', False]
        except mysql.connector.Error as error:
            print('Consultar usuario Error: ' + str(error))
            return ['Consultar usuario Error: ', False]
    
    def consultar_usuarios(self, category):
        '''
        Consulta todos los usuarios
        '''
        try:
            print('consultar_usuarios')
            ncursor = self.login_database()
            query = "SELECT COUNT(k_users) FROM users WHERE b_active = 1"
            if category == 'Vendedor':
                query = "SELECT COUNT(k_users) FROM users WHERE n_categoria = 'Vendedor' AND b_active = 1"
            ncursor.execute(query)
            total_users = ncursor.fetchone()[0]
            query = "SELECT k_users, n_nombre, n_apellido, n_correo, n_categoria FROM users WHERE b_active = 1"
            if category == 'Vendedor':
                query = "SELECT k_users, n_nombre, n_apellido, n_correo, n_categoria FROM users WHERE n_categoria = 'Vendedor' AND b_active = 1"
            ncursor.execute(query)
            users = ncursor.fetchall()
            return [[total_users, users], True]
        except mysql.connector.Error as error:
            print('Consultar usuarios Error: '+str(error))
            return ['Falló la consula general de usuarios', False]

    def consultar_vendedores(self, limit, offset):
        '''
        Devuelve todos los vendedores registrados en el sistema
        '''
        try:
            print('consultar_vendedores')
            #Calcular total de vendedores
            ncursor = self.login_database()
            query = "SELECT COUNT(k_users) FROM users WHERE n_categoria = 'Vendedor' AND b_active = 1;"
            ncursor.execute(query)
            total_vendedores = ncursor.fetchone()[0]
            if total_vendedores is None:
                total_vendedores = 0
            query = """
            SELECT JSON_OBJECT('id', k_users, 'name', n_nombre, 'lastname', n_apellido, 'email', n_correo, 'hierarchy', n_categoria) 
            FROM users 
            WHERE n_categoria = 'Vendedor' AND b_active = 1 ORDER BY n_nombre ASC LIMIT %s OFFSET %s
            """
            ncursor.execute(query, (limit, offset,))
            result = ncursor.fetchall()
            return [[result, total_vendedores],True]
        except mysql.connector.Error as error:
            print('Consultar vendedores Error: ' + str(error))
            return ['Falló la consulta de vendedores', False]  

    def consultar_token_blocklist(self, jti):
        '''
        Consulta la información específica de un token block_list
        Args:
            jti:jti 
        '''
        print('JTI db.py: ' + str(jti))
        try:
            ncursor = self.login_database()
            query = "SELECT * FROM token_blocklist WHERE n_jti = %s"
            ncursor.execute(query, (jti, ))
            result = ncursor.fetchone()
            print('Token block list buscado: ' + str(result))
            if result != None:
                return [result,True]
            return [None, False]
        except mysql.connector.Error as error:
            print('Consultar token blocklist Error: '+str(error))
            return ['Falló la consulta de block token', False]
    
    def consultar_block_tokens(self):
        '''
        Devuelve todos los block tokens
        '''
        try:
            print('consultar_block_tokens')
            ncursor = self.login_database()
            query = "SELECT * FROM token_blocklist"
            ncursor.execute(query)
            result = ncursor.fetchall()
            if result:
                return [result,True]
            return ['No hay blocktokens', False]
        except mysql.connector.Error as error:
            print('Consultar block tokens Error: '+str(error))
            return ['Falló la consulta de block token', False]

    def consultar_pedidos_vendedor_stat(self,id_vendedor, limit, offset, filter, category, date):
        '''
        Devuelve un resumen de ventas del vendedor en el año para
        observar rendimientos
        Args:
            -id_vendedor: int
            -limit: int
            -offset: int
            -filter: str
            -category: str
            -date: int
        '''
        try:
            print('consultar_pedidos_vendedor_stat')
            #Verificar si existe el vendedor
            ncursor = self.login_database()
            query = "SELECT k_users, n_nombre, n_apellido, n_correo, n_categoria, o_password FROM users WHERE k_users = %s AND b_active = 1"
            ncursor.execute(query, (id_vendedor,))
            vendedor = ncursor.fetchone()
            if vendedor:
                #Calcular fecha
                if date and date != 13:
                    dia = 1
                    mes = date
                    año = datetime.datetime.now().strftime('%Y')
                    fecha0 = datetime.datetime(int(año) - 1, int(mes), int(dia))
                    fecha0 = fecha0.strftime('%Y-%m-%d')
                    
                    fecha0_ = datetime.datetime(int(año), int(mes), int(dia))
                    fecha0_ = fecha0_.strftime('%Y-%m-%d')

                    dia2 = calendar.monthrange(int(año), int(mes))[1]
                    fecha1 = datetime.datetime(int(año), int(mes), int(dia2))
                    fecha1 = fecha1.strftime('%Y-%m-%d')
                else:
                    dia = 1
                    mes = 1
                    año = datetime.datetime.now().strftime('%Y')
                    fecha0 = datetime.datetime(int(año) - 1, int(mes), int(dia))
                    fecha0 = fecha0.strftime('%Y-%m-%d')

                    fecha0_ = datetime.datetime(int(año), int(mes), int(dia))
                    fecha0_ = fecha0_.strftime('%Y-%m-%d')

                    fecha1 = datetime.datetime.now()
                    fecha1 = fecha1.strftime('%Y-%m-%d')

                if category == 'Eliminados':
                    # Calculamos total de pedidos
                    if filter:
                        query_complement = """
                        AND (
                            LOWER(REPLACE(summary.k_venta,' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                            LOWER(REPLACE(clients.n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                        )
                        """
                    else:
                        query_complement = ""
                    query = """
                    SELECT COUNT(summary.k_venta) FROM (
                        SELECT pedidos.k_venta, pedidos.k_cliente, pedidos.k_users, pedidos.f_venta, SUM(venta.q_valortotal) as v_total,
                        pedidos.n_estadop0, pedidos.n_estadop1, pedidos.n_estadop2
                        FROM pedidos, venta 
                        WHERE pedidos.k_venta = venta.k_venta 
                        AND pedidos.k_cliente = venta.k_cliente 
                        AND pedidos.k_users = venta.k_users 
                        AND pedidos.b_active = 0
                        AND pedidos.f_venta BETWEEN %s AND %s GROUP BY pedidos.k_venta
                    ) AS summary, clients
                    WHERE k_users = %s
                    """ + query_complement + """
                    AND clients.k_cliente = summary.k_cliente ORDER BY summary.k_venta DESC
                    """
                    ncursor.execute(query, (fecha0, fecha1, id_vendedor) if not filter else (fecha0, fecha1, id_vendedor, '%'+filter+'%', '%'+filter+'%'))
                    total_pedidos = ncursor.fetchone()[0]
                    if total_pedidos is None:
                        total_pedidos = 0
                    query = """
                    SELECT summary.k_venta, clients.n_cliente, DATE_FORMAT(summary.f_venta,'%%e/%%m/%%Y') AS fecha,
                    n_estadop0, n_estadop1, n_estadop2, FORMAT(summary.v_total, 0, 'de_DE') FROM (
                        SELECT pedidos.k_venta, pedidos.k_cliente, pedidos.k_users, pedidos.f_venta, SUM(venta.q_valortotal) as v_total,
                        pedidos.n_estadop0, pedidos.n_estadop1, pedidos.n_estadop2
                        FROM pedidos, venta 
                        WHERE pedidos.k_venta = venta.k_venta 
                        AND pedidos.k_cliente = venta.k_cliente 
                        AND pedidos.k_users = venta.k_users 
                        AND pedidos.b_active = 0
                        AND pedidos.f_venta BETWEEN %s AND %s GROUP BY pedidos.k_venta
                    ) AS summary, clients
                    WHERE k_users = %s
                    """ + query_complement + """
                    AND clients.k_cliente = summary.k_cliente ORDER BY summary.k_venta DESC
                    LIMIT %s OFFSET %s
                    """
                    ncursor.execute(query, (fecha0, fecha1, id_vendedor, limit, offset,) if not filter else (fecha0, fecha1, id_vendedor, '%'+filter+'%', '%'+filter+'%', limit, offset,))
                    result = ncursor.fetchall()
                else:
                    if category == 'No autorizado':
                        query_complement = " AND n_estadop0 = 'No autorizado' AND n_estadop1 = 'Por facturar'"
                    elif category == 'Autorizado':
                        query_complement = " AND n_estadop0 = 'Autorizado' AND n_estadop1 = 'Por facturar'"
                    elif category == 'Por despachar':
                        query_complement = " AND n_estadop1 = 'Facturado' AND n_estadop2 = 'Por despachar'"
                    elif category == 'Incompletos':
                        query_complement = " AND n_estadop2 = 'Incompleto'"
                    elif category == 'Despachados':
                        query_complement = " AND n_estadop2 = 'Despachado'"
                    else:
                        query_complement = ""
                    # Calculamos total de pedidos
                    if filter:
                        query_complement += """
                         AND (
                            LOWER(REPLACE(summary.k_venta,' ', '')) LIKE LOWER(REPLACE(%s, ' ', '')) OR
                            LOWER(REPLACE(clients.n_cliente, ' ', '')) LIKE LOWER(REPLACE(%s, ' ', ''))
                        )
                        """
                    query = """
                    SELECT COUNT(summary.k_venta) FROM (
                        SELECT pedidos.k_venta, pedidos.k_cliente, pedidos.k_users, pedidos.f_venta, SUM(venta.q_valortotal) as v_total,
                        pedidos.n_estadop0, pedidos.n_estadop1, pedidos.n_estadop2
                        FROM pedidos, venta 
                        WHERE pedidos.k_venta = venta.k_venta 
                        AND pedidos.k_cliente = venta.k_cliente 
                        AND pedidos.k_users = venta.k_users 
                        AND pedidos.b_active = 1
                        AND pedidos.f_venta BETWEEN %s AND %s GROUP BY pedidos.k_venta
                    ) AS summary, clients
                    WHERE k_users = %s
                    """ + query_complement + """
                    AND clients.k_cliente = summary.k_cliente ORDER BY summary.k_venta DESC
                    """
                    ncursor.execute(query, (fecha0, fecha1, id_vendedor) if not filter else (fecha0, fecha1, id_vendedor, '%'+filter+'%', '%'+filter+'%'))
                    total_pedidos = ncursor.fetchone()[0]
                    if total_pedidos is None:
                        total_pedidos = 0
                    query = """
                    SELECT summary.k_venta, clients.n_cliente, DATE_FORMAT(summary.f_venta,'%%e/%%m/%%Y') AS fecha, 
                    n_estadop0, n_estadop1, n_estadop2, FORMAT(summary.v_total, 0, 'de_DE') FROM ( 
                        SELECT pedidos.k_venta, pedidos.k_cliente, pedidos.k_users, pedidos.f_venta, SUM(venta.q_valortotal) as v_total, 
                        pedidos.n_estadop0, pedidos.n_estadop1, pedidos.n_estadop2 
                        FROM pedidos, venta 
                        WHERE pedidos.k_venta = venta.k_venta 
                        AND pedidos.k_cliente = venta.k_cliente 
                        AND pedidos.k_users = venta.k_users 
                        AND pedidos.b_active = 1 
                        AND pedidos.f_venta BETWEEN %s AND %s GROUP BY pedidos.k_venta 
                    ) AS summary, clients 
                    WHERE k_users = %s 
                    """ + query_complement + """
                    AND clients.k_cliente = summary.k_cliente ORDER BY summary.k_venta DESC 
                    LIMIT %s OFFSET %s
                    """
                    ncursor.execute(query, (fecha0, fecha1, id_vendedor,limit, offset) if not filter else (fecha0, fecha1, id_vendedor, '%'+filter+'%', '%'+filter+'%',limit, offset,))
                    result = ncursor.fetchall()
                ncursor.execute("SET lc_time_names = 'es_ES';")
                query = """
                SELECT DATE_FORMAT(summary.f_venta_facturado, '%%M') AS Mes, CONVERT(SUM(summary.v_total), DECIMAL) FROM (
                    SELECT pedidos.k_venta, pedidos.k_cliente, pedidos.k_users, pedidos.f_venta_facturado, SUM(venta.q_vunitario*q_cantidad_despachada) AS v_total 
                    FROM pedidos, venta 
                    WHERE pedidos.k_venta = venta.k_venta
                    AND pedidos.n_estadop0 = 'Autorizado'
                    AND pedidos.n_estadop1 = 'Facturado'
                    AND pedidos.k_cliente = venta.k_cliente 
                    AND pedidos.k_users = venta.k_users 
                    AND pedidos.k_users = %s
                    AND pedidos.f_venta_facturado BETWEEN %s AND %s GROUP BY pedidos.k_venta
                ) AS summary
                GROUP BY Mes ORDER BY summary.f_venta_facturado ASC
                """
                ncursor.execute(query, (id_vendedor, fecha0_, fecha1,))
                rendimiento = ncursor.fetchall()
                if result:
                    return [[result, total_pedidos, rendimiento], True]
                return [[[], 0, []], False]
            return [['El vendedor no existe o ha sido eliminado.', 0, []], False]
        except mysql.connector.Error as error:
            print('Consultar pedidos resumen vendedor Error: '+str(error))
            return [['Falló la consulta de pedidos resumen para vendedor.', 0, []], False]

    def consultar_pedidos_vendedor(self,id_vendedor, limit, offset):
        '''
        Devuelve todos los pedidos registrados por
        un vendedor (2 AÑOS)
        '''
        try:
            print('consultar_pedidos_vendedor')
            dia = 1
            mes = 1
            año = datetime.datetime.now().strftime('%Y')
            fecha0 = datetime.datetime(int(año) - 1, int(mes), int(dia))
            fecha0 = fecha0.strftime('%Y-%m-%d')
            fecha1 = datetime.datetime.now()
            fecha1 = fecha1.strftime('%Y-%m-%d')
            ncursor = self.login_database()
            query = "SELECT COUNT(k_venta) FROM pedidos WHERE k_users = %s AND f_venta BETWEEN %s AND %s;"
            ncursor.execute(query, (id_vendedor,fecha0, fecha1 ))
            total_pedidos = ncursor.fetchone()[0]
            if total_pedidos is None:
                total_pedidos = 0
            query = "SELECT k_venta, k_cliente, k_users, f_venta, n_estadop0, n_estadop1, n_estadop2, n_observaciones FROM pedidos WHERE k_users = %s AND f_venta BETWEEN %s AND %s ORDER BY f_venta DESC LIMIT %s OFFSET %s"
            ncursor.execute(query, (id_vendedor,fecha0, fecha1,limit, offset ))
            result = ncursor.fetchall()
            if result:
                return [[result, total_pedidos], True]
            return [['No se encuentra pedidos registrados',0], False]
        except mysql.connector.Error as error:
            print('Consultar pedidos vendedor Error: '+str(error))
            return ['Falló la consulta de pedidos para vendedor.', False]

    def insertar_token_blocklist(self, jti, date):
        '''
        Registramos un token blocklist
        Args:
            jti: jti
            date: created at
        '''
        try:
            print('insertar_token_blocklist')
            ncursor = self.login_database()
            query = "INSERT INTO token_blocklist VALUES (NULL, %s, %s, DEFAULT, DEFAULT)"
            ncursor.execute(query, (jti, date))
            self.mysql.connection.commit()
            return ['Añadido', True]
        except mysql.connector.Error as error:
            print('Insertar token blocklist Error: '+str(error))
            return ['Falló el registro del token', False]
 
    def clean_block_tokens(self):
        '''
        Borra los tokens vencidos de la lista de block tokens
        '''
        try:
            print('clean_block_tokens')
            block_tokens = self.consultar_block_tokens()
            if block_tokens[1] == True:
                ncursor = self.login_database()
                ncursor.execute("SET SQL_SAFE_UPDATES = 0")
                for data_block_tokens in block_tokens[0]:
                    if data_block_tokens[2] < datetime.datetime.now(): #Fecha SQL < Fecha Now
                        query = "DELETE FROM token_blocklist WHERE k_token = %s"
                        ncursor.execute(query, (data_block_tokens[0], ))
                        self.mysql.connection.commit()
            return ['Block Tokens Cleaned', True]
        except mysql.connector.Error as error:
            print('clean_block_tokens Error: '+ str(error))
            return ['Falló el proceso: Clean Block Tokens', False]
    
    # INSERTS
    def registrar_reclamacion(self, reclamacion):
        '''
        Registra una reclamación
        Args:
            reclamacion: DICT
                userId: INT
                relevance: INT
                title: STRING
                claim: STRING
        '''
        try: 
            print('registrar_reclamacion')
            ncursor = self.login_database()
            # Calcular id
            query = "SELECT k_claim FROM claims ORDER BY k_claim DESC LIMIT 1"
            ncursor.execute(query)
            id = ncursor.fetchone()[0]
            id = 1 if not id else id + 1
            query = "INSERT INTO claims VALUES (%s, %s, %s, %s, %s, 'No revisado', 1, DEFAULT, DEFAULT)"
            ncursor.execute(query, (id, reclamacion['userId'], reclamacion['title'], reclamacion['relevance'], reclamacion['claim']))
            self.mysql.connection.commit()
            return ['Reclamación registrada', True]
        except mysql.connector.Error as error:
            print('Registrar reclamación Error: '+str(error))
            return ['Falló el registro de reclamación', False]

    def asignar_zona_vendedor(self, id_zona, id_vendedor):
        '''
        Asigna una zona a un vendedor
        Args:
            - id_zona: INT
            - id_vendedor: INT
        '''
        try:
            print('asignar_zona_vendedor')
            ncursor = self.login_database()
            query = "INSERT INTO zona_vendedor VALUES (%s, %s, DEFAULT, DEFAULT)"
            ncursor.execute(query, (id_zona, id_vendedor))
            self.mysql.connection.commit()
            return ['Zona asignada', True]
        except mysql.connector.Error as error:
            print('Asignar zona vendedor Error: '+str(error))
            return ['Falló la asignación de zona', False]

    def registrar_solicitud_cambio_password(self, id, code, fecha):
        '''
        Registramos un una id, un token y un codigo
        Este procedimiento extrae la fecha de expiración del token y si esta fecha ya expira borra la solicitud anterior
        y registra una nueva
        Args:
            info: Dicc
                data_user = id INT
                final_token = token STR
                code STR
        '''
        try:
            ncursor = self.login_database()
            self.mysql.connection.begin()
            query = "SELECT k_users, n_code, f_exp FROM update_password WHERE k_users = %s"
            ncursor.execute(query, (id, ))
            result = ncursor.fetchone()
            if result:
                if result[2] < datetime.datetime.now():
                    ncursor = self.login_database()
                    query = "DELETE FROM update_password WHERE k_users = %s"
                    ncursor.execute(query, (id, ))
                    query = "INSERT INTO update_password VALUES (%s, %s, %s, DEFAULT, DEFAULT)"
                    ncursor.execute(query, (id, code, fecha))
                    self.mysql.connection.commit()
                    return ['Success', True]
                else:
                    return ['Token activo', False]
            else:
                ncursor = self.login_database()
                query = "INSERT INTO update_password VALUES (%s, %s, %s, DEFAULT, DEFAULT)"
                ncursor.execute(query, (id, code, fecha))
                self.mysql.connection.commit()
                return ['Success', True]
        except mysql.connector.Error as error:
            print('Registrar solicitud cambio password Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el registro de cambio de contraseña', False]

    def registrar_agenda(self, id_vendedor, id_cliente):
        '''
        Registra un nuevo cliente en la agenda del vendedor
        '''
        try:
            print('registrar_agenda')
            ncursor = self.login_database()
            # Verificar si el cliente ya está en la agenda
            query = "SELECT k_cliente FROM agenda WHERE k_users = %s AND k_cliente = %s"
            ncursor.execute(query, (id_vendedor, id_cliente))
            result = ncursor.fetchone()
            if result:
                return ['El cliente ya está en la agenda', False]
            # Verificar que el cliente exista
            query = "SELECT k_cliente, n_cliente FROM clients WHERE k_cliente = %s"
            ncursor.execute(query, (id_cliente, ))
            cliente = ncursor.fetchone()
            if cliente is None:
                return ['El cliente no existe', False]
            # Registrar cliente en la agenda
            query = "INSERT INTO agenda VALUES (%s, %s, %s, NULL, DEFAULT, DEFAULT)"
            ncursor.execute(query, (id_vendedor, id_cliente, cliente[1]))
            self.mysql.connection.commit()
            return ['Cliente añadido satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Registrar agenda Error: '+str(error))
            return ['Falló el registro del cliente en la agenda', False]

    def registrar_cotizacion(self, id_vendedor, id_cliente, pedido, obs="S/O"):
        '''
        Registra una cotización
        Args:
            id_vendedor: id del vendedor
            id_cliente: id del cliente
            pedido: pedido
            obs: observaciones
        '''
        try:
            print('registrar_cotizacion')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Calculamos ID
            query = "SELECT k_venta_cotizacion FROM pedidos_cotizaciones ORDER BY k_venta_cotizacion DESC LIMIT 1"
            ncursor.execute(query)
            id = ncursor.fetchone()
            if id is None:
                id = 0
            else:
                id = id[0]
            id += 1
            # Calculamos fecha
            fecha = datetime.datetime.now()
            # Pedidos cotizaciones
            query = "INSERT INTO pedidos_cotizaciones VALUES (%s, %s, %s, %s, %s, 1, DEFAULT, DEFAULT)"
            ncursor.execute(query, (id, id_cliente, id_vendedor, fecha, obs))
            # Venta cotizaciones
            query = "INSERT INTO venta_cotizaciones VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, DEFAULT, DEFAULT)"
            for producto in pedido:
                ncursor.execute(query, (
                    id, 
                    int(producto[8]),
                    id_cliente, 
                    id_vendedor, 
                    producto[0], 
                    int(producto[1]), # q_cantidad
                    int(producto[2]), # q_bonificacion
                    float(producto[3].replace(".", "").replace(",", ".")), # q_totalkilos
                    float(producto[4].replace(".", "").replace(",", ".")), # q_totalkilosb
                    float(producto[5].replace(".", "")), # q_vunitario
                    float(producto[6].replace(".", "")), # q_valortotal
                    float(producto[7].replace(".", "")), # q_valortotalb
                    ))
            self.mysql.connection.commit()
            return [f'Cotización registrada con #{id}', True, id]
        except mysql.connector.Error as error:
            print('Registrar cotizacion Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el registro de la cotización', False, 0]

    def registrar_pedido_bodega(self, id_vendedor, pedido, obs="S/O"):
        '''
        Registramos un nuevo pedido: PROCESO CORE
        Args:
            -id_vendedor: int
            -pedido: list
            -obs: str
        '''
        try:
            print('registrar_pedido')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Consultar bodega vendedor
            query = "SELECT k_bodega FROM bodegas WHERE k_users = %s"
            ncursor.execute(query, (id_vendedor, ))
            id_bodega = ncursor.fetchone()[0]
            # Consultar ID
            query = "SELECT k_venta_bodegas FROM pedidos_bodegas ORDER BY k_venta_bodegas DESC LIMIT 1"
            ncursor.execute(query)
            id = ncursor.fetchone()
            if id is None:
                id = 1
            else:
                id = id[0] + 1
            # Registro en tabla PEDIDOS:
            fecha = datetime.datetime.now().strftime('%Y-%m-%d')
            query = "INSERT INTO pedidos_bodegas VALUES (%s, %s, %s, %s, NULL, 'Por despachar', %s, 1, DEFAULT, DEFAULT)"
            ncursor.execute(query, (id, id_bodega, id_vendedor, fecha, obs, ))
            # Registro en tabla VENTA:
            query = """INSERT INTO venta_bodegas VALUES (%s, %s, %s, %s, %s, %s, 'Por despachar', 0, DEFAULT, DEFAULT)"""
            for producto in pedido:
                ncursor.execute(query, (
                    id,
                    id_bodega, # k_bodega
                    id_vendedor, # k_users
                    producto[0], # k_productos
                    int(producto[1]), # q_cantidad
                    float(producto[2].replace(".", "").replace(",", ".")), # q_totalkilos
                ))
            self.mysql.connection.commit()
            return ['Pedido para bodega registrado', id, True]
        except mysql.connector.Error as error:
            print('Registrar pedido Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el registro del nuevo pedido para bodega', 0, False]

    def registrar_pedido(self, id_vendedor, id_cliente, pedido, obs="S/O"):
        '''
        Registramos un nuevo pedido: PROCESO CORE
        Args:
            -id_vendedor: int
            -id_cliente: int
            -pedido: list
            -obs: str
        '''
        try:
            print('registrar_pedido')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Consultar ID
            query = "SELECT k_venta FROM pedidos ORDER BY k_venta DESC LIMIT 1"
            ncursor.execute(query)
            id = ncursor.fetchone()
            if id is None:
                id = 1
            else:
                id = id[0] + 1
            # Registro en tabla PEDIDOS:
            fecha = datetime.datetime.now().strftime('%Y-%m-%d')
            query = "INSERT INTO pedidos VALUES (%s, %s, %s, %s, NULL, NULL, NULL, 'No autorizado', 'Por facturar', 'Por despachar', %s, 1, DEFAULT, DEFAULT)"
            ncursor.execute(query, (id, id_cliente, id_vendedor, fecha, obs, ))
            # Registro en tabla VENTA:
            query = """INSERT INTO venta VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Por despachar', 0, DEFAULT, DEFAULT)"""
            for producto in pedido:
                ncursor.execute(query, (
                    id,
                    id_cliente,  # k_cliente
                    id_vendedor, # k_users
                    producto[0], # k_productos
                    int(producto[1]), # q_cantidad
                    int(producto[2]), # q_bonificacion
                    float(producto[3].replace(".", "").replace(",", ".")), # q_totalkilos
                    float(producto[4].replace(".", "").replace(",", ".")), # q_totalkilosb
                    float(producto[5].replace(".", "")), # q_vunitario
                    float(producto[6].replace(".", "")), # q_valortotal
                    float(producto[7].replace(".", "")), # q_valortotalb
                ))
            self.mysql.connection.commit()
            return ['Pedido registrado', id, True]
        except mysql.connector.Error as error:
            print('Registrar pedido Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el registro del nuevo pedido', 0, False]

    def registrar_cliente_favorito(self, id_cliente, id_user):
        '''
        Registra un cliente como favorito para un CEO
        Args:
            -id_cliente: int
            -id_user: int
        '''
        try:
            print('registrar_cliente_favorito')
            ncursor = self.login_database()
            # Verificamos que el cliente no este registrado
            query = "SELECT k_cliente FROM clientes_favoritos WHERE k_cliente = %s AND k_users = %s"
            ncursor.execute(query, (id_cliente, id_user))
            result = ncursor.fetchone()
            if result is None:
                query = "INSERT INTO clientes_favoritos VALUES (%s, %s, DEFAULT, DEFAULT)"
                ncursor.execute(query, (id_cliente, id_user))
                self.mysql.connection.commit()
                return ['Cliente registrado como favorito', True]
            return ['El cliente ya se encuentra registrado como favorito', False]
        except mysql.connector.Error as error:
            print('Registrar cliente favorito Error: '+str(error))
            return ['Falló el registro del cliente favorito', False]

    def registrar_bodega(self, nombre, vendedor):
        '''
        Registra una nueva bodega
        Args:
            -   nombre: str
            - vendedor: str
        '''
        try:
            print('registrar_bodega')
            ncursor = self.login_database()
            query = "INSERT INTO bodegas VALUES (NULL, %s, %s, %s, DEFAULT, DEFAULT)"
            ncursor.execute(query, (nombre, vendedor, True))
            self.mysql.connection.commit()
            return ['Bodega registrada', True]
        except mysql.connector.Error as error:
            print('Registrar bodega Error: '+str(error))
            return ['Falló el registro de la bodega', False]

    def registrar_lista_precios(self, content, name, brand, category):
        '''
        Registramos una nueva lista de precios, como se manejan dos IDS necesitamos calcular la ID y no usar
        SQL AUTO INCREMENT
        Args:
            content: Arreglo que contiene arreglo
            ex: [[ID, Marca, n_PRODUCTO, q_VALORUNIT, q_KG], [1, Agrosal, Rentafos equinos x50g, 54512, 12,3]]
            category: Pedidos o Bodegas str
        '''
        try:
            print('registrar_lista_precios')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            if category == "Pedidos":
                query = 'SELECT k_listaprecios, n_nombre, n_marca, n_link FROM namelp ORDER BY k_listaprecios DESC'
                ncursor.execute(query)
                result = ncursor.fetchall()
                #Registro de NAMELP
                query = 'INSERT INTO namelp VALUES (%s, %s, %s, null, DEFAULT, DEFAULT)'
                ncursor.execute(query, (int(result[0][0]) + 1 if result else 1, name, brand))
                #Registro de LISTAPRECIOS
                query = 'INSERT INTO listaprecios VALUES (%s, %s, %s, %s, %s, DEFAULT, DEFAULT)'
                for data in content:
                    ncursor.execute(query, (int(result[0][0]) + 1 if result else 1, brand, data[0], data[1], data[2]))
            elif category == "Bodegas":
                query = 'SELECT k_listaprecios, n_nombre, n_marca, n_link FROM namelp_bodegas ORDER BY k_listaprecios DESC'
                ncursor.execute(query)
                result = ncursor.fetchall()
                # Registro de NAMELP
                query = 'INSERT INTO namelp_bodegas VALUES (%s, %s, %s, null, DEFAULT, DEFAULT)'
                ncursor.execute(query, (int(result[0][0]) + 1 if result else 1, name, brand))
                #Registro de LISTAPRECIOS
                query = 'INSERT INTO listaprecios_bodegas VALUES (%s, %s, %s, %s, DEFAULT, DEFAULT)'
                for data in content:
                    ncursor.execute(query, (int(result[0][0]) + 1 if result else 1, brand, data[0], data[1]))
            self.mysql.connection.commit()
            return ['Lista de precios registrada satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Calcular la ID //registrar_lp// Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el registro de la lista de precios', False]

    def registrar_zona(self, info_zone):
        '''
        Registrar una nueva zona
        '''
        try:
            print('registrar_zona')
            zona, success = self.consultar_zona(info_zone['id'])
            if not success:
                name = info_zone['name']
                ncursor = self.login_database()
                self.mysql.connection.begin()
                query = "INSERT zona VALUES (%s, %s, 1, DEFAULT, DEFAULT);"
                ncursor.execute(query, (int(info_zone['id']), info_zone['name'],))
                for department in info_zone['department']:
                    query = "INSERT zona_departamento VALUES (%s, %s, DEFAULT, DEFAULT);"
                    ncursor.execute(query, (int(info_zone['id']), department,))
                self.mysql.connection.commit()
                zona, success = self.consultar_zona(info_zone['id'])
                return [[f'Zona {name} registrada satisfactoriamente', zona], True]
            return [f'La zona con ID: {id} ya existe.', False]
        except mysql.connector.Error as error:
            print('Registrar zona Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el registro de la zona', False]

    def registrar_cliente(self, info_client):
        '''
        Registra un nuevo cliente en la base de datos
        Args:
            info_client
        '''
        try:
            print('registrar_cliente')
            # Verificar que el cliente no exista
            ncursor = self.login_database()
            query = "SELECT k_cliente FROM clients WHERE k_cliente = %s"
            ncursor.execute(query, (info_client['id'],))
            result = ncursor.fetchone()
            if result:
                return ['El cliente ya existe', False]
            # Registramos el cliente
            query = "INSERT INTO clients VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, DEFAULT, DEFAULT)"
            ncursor.execute(query, (
                int(info_client['id']),
                info_client['name'],
                info_client['email'],
                info_client['address'],
                info_client['department'],
                info_client['city'],
                int(info_client['phone']),
                info_client['phone2'],
                int(info_client['zone']), ))
            self.mysql.connection.commit()
            return ['Cliente registrado', True]
        except mysql.connector.Error as error:
            print('Registrar cliente Error: '+str(error))
            return ['Falló el registro del cliente', False]


    def asignar_lp(self, id_seller, id_lp, category):
        '''
        Asigna una lista de precios a un vendedor
        '''
        try:
            print('asignar_lp')
            #Verificar si la relacion ya existe
            ncursor = self.login_database()
            if category == "Bodegas":
                query = "SELECT k_users, k_listaprecios FROM vendedor_listaprecios_bodegas WHERE k_users = %s and k_listaprecios = %s"
                ncursor.execute(query, (int(id_seller), int(id_lp),))
                result = ncursor.fetchone()
                if result:
                    return ['Lista de precios ya está asignada a este vendedor', False]
                query = "INSERT INTO vendedor_listaprecios_bodegas VALUES (%s, %s, DEFAULT, DEFAULT)"
                ncursor.execute(query, (int(id_seller), int(id_lp)))
                self.mysql.connection.commit()
                return ['Lista de precios asignada satisfactoriamente', True]
            else:
                query = "SELECT k_users, k_listaprecios FROM vendedor_listaprecios WHERE k_users = %s and k_listaprecios = %s"
                ncursor.execute(query, (int(id_seller), int(id_lp),))
                result = ncursor.fetchone()
                if result:
                    return ['Lista de precios ya está asignada a este vendedor', False]
                query = "INSERT INTO vendedor_listaprecios VALUES (%s, %s, DEFAULT, DEFAULT)"
                ncursor.execute(query, (int(id_seller), int(id_lp)))
                self.mysql.connection.commit()
                return ['Lista de precios asignada satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Registrar lista de precios a vendedor Error: '+str(error))
            return ['Falló el registro de lista de precios a vendedor', False]

    def registrar_usuario(self, info):
        '''
        Insertamos un nuevo usuarios en la base de datos
        Args:
            id: int
            name: str
            lastname: str
            email: str
            hierarchy: str
            password: str
        '''
        try:
            print('registrar_usuario')
            #Verificamos que el usuario no este registrado ya
            id_user = info['id']
            ncursor = self.login_database()
            query = "SELECT * FROM users WHERE k_users = %s"
            ncursor.execute(query, (id_user,))
            user = ncursor.fetchone()
            if not user:
                query = "INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, 1, DEFAULT, DEFAULT)"
                ncursor.execute(query, (info['id'], info['name'], info['apellido'], info['correo'], info['categoria'], info['password']))
                self.mysql.connection.commit()
                user, success = self.consultar_usuario(id_user)
                return [user, success]    
            elif user[6] == 0:
                ncursor.execute("SET SQL_SAFE_UPDATES = 0")
                query = "UPDATE users SET n_nombre = %s, n_apellido = %s, n_correo = %s, n_categoria = %s, o_password = %s, b_active = 1 WHERE k_users = %s"
                ncursor.execute(query, (info['name'], info['apellido'], info['correo'], info['categoria'], info['password'], id_user))
                self.mysql.connection.commit()
                user, success = self.consultar_usuario(id_user)
                return [user, success]
            return [f'El usuario con C.C. {id_user} ya se encuentra registrado.',False]
        except mysql.connector.Error as error:
            print('Registrar usuario Error: '+str(error))
            return ['Falló el registro del usuario', False]
    
    # DELETES
    def eliminar_reclamacion(self, id_reclamacion):
        '''
        Elimina una reclamación de la base de datos
        Args:
            - id_reclamacion: int
        '''
        try:
            print('eliminar_reclamacion')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE claims SET b_active = 0 WHERE k_claim = %s;"
            ncursor.execute(query, (id_reclamacion,))
            self.mysql.connection.commit()
            return ['Reclamación eliminada satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Eliminar reclamación Error: '+str(error))
            return ['Falló la eliminación de la reclamación', False]

    def desasignar_zona_vendedor(self, id_zona, id_vendedor):
        '''
        Desasigna una zona a un vendedor
        '''
        try:
            print('desasignar_zona_vendedor')
            ncursor = self.login_database()
            query = "DELETE FROM zona_vendedor WHERE k_users = %s and k_zona = %s"
            ncursor.execute(query, (id_vendedor, id_zona))
            self.mysql.connection.commit()
            return ['Zona desasignada satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Desasignar zona a vendedor Error: '+str(error))
            return ['Falló el desasignar zona a vendedor', False]

    def eliminar_cotizaciones_viejas(self, id_vendedor):
        '''
        Borra las cotizaciones que tengan mas de 15 dias
        '''
        try:
            print('eliminar_cotizaciones_viejas')
            # 1. Consultar las cotizaciones del vendedor
            fecha = datetime.date.today()
            ncursor = self.login_database()
            query = "SELECT k_venta_cotizacion, f_venta FROM pedidos_cotizaciones WHERE k_users = %s"
            ncursor.execute(query, (id_vendedor,))
            cotizaciones = ncursor.fetchall()
            query = "DELETE FROM pedidos_cotizaciones WHERE k_venta_cotizacion = %s"
            for cotizacion in cotizaciones:
                if fecha - cotizacion[1] > datetime.timedelta(days=14):
                    ncursor.execute(query, (cotizacion[0],))
            self.mysql.connection.commit()
            return ['Cotizaciones limpiadas satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Eliminar cotización Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló la eliminación de la cotizaciones viejas', False]

    def eliminar_cotizacion(self, id_cotizacion):
        '''
        Elimina una cotización de la base de datos
        Args:
            id_cotizacion: int
        '''
        try:
            print('eliminar_cotizacion')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "DELETE FROM pedidos_cotizaciones WHERE k_venta_cotizacion = %s"
            ncursor.execute(query, (id_cotizacion,))
            query = "DELETE FROM venta_cotizaciones WHERE k_venta_cotizacion = %s"
            ncursor.execute(query, (id_cotizacion,))
            self.mysql.connection.commit()
            return ['Cotización eliminada', True]
        except mysql.connector.Error as error:
            print('Eliminar cotización Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló la eliminación de la cotización', False]

    def eliminar_cliente_favorito(self, id_cliente, id_user):
        '''
        Elimina un cliente de favoritos dado un usuario
        Args:
            id_cliente: int
            id_user: int
        '''
        try:
            print('eliminar_cliente_favorito')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "DELETE FROM clientes_favoritos WHERE k_cliente = %s and k_users = %s"
            ncursor.execute(query, (id_cliente, id_user))
            self.mysql.connection.commit()
            return ['Cliente eliminado de favoritos', True]
        except mysql.connector.Error as error:
            print('Eliminar cliente favorito Error: '+str(error))
            return ['Falló la eliminación del cliente de favoritos', False]
    
    def eliminar_pedido_bodega(self, id):
        '''
        Elimina el pedido de una bodega
        '''
        try:
            print('eliminar_pedido_bodega')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE pedidos_bodegas SET b_active = 0 WHERE k_venta_bodegas = %s"
            ncursor.execute(query, (id,))
            self.mysql.connection.commit()
            return ['Pedido eliminado', True]
        except mysql.connector.Error as error:
            print('Eliminar pedido bodega Error: '+str(error))
            return ['Falló la eliminación del pedido', False]

    def eliminar_bodega(self, id):
        '''
        Elimina una bodega de la base de datos
        '''
        try:
            print('eliminar_bodega')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE bodegas SET b_active = 0 WHERE k_bodega = %s"
            ncursor.execute(query, (int(id,),))
            self.mysql.connection.commit()
            return ['Bodega eliminada', True]
        except mysql.connector.Error as error:
            print('Eliminar bodega Error: '+str(error))
            return ['Falló la eliminación de la bodega', False]

    def eliminar_pedido(self, id, reason, id_user):
        '''
        Eliminar un pedido de la db
        (actualiza el estado a inactive e inserta en la tabla de historial)
        Args:
            -id: int ID PEDIDO
            -reason: str motivo 
            -id_user: ID deleting
        '''
        try:
            print('eliminar_pedido')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE pedidos SET b_active = False WHERE k_venta = %s"
            ncursor.execute(query, (id,))
            query = "SELECT * FROM pedidos WHERE k_venta = %s"
            ncursor.execute(query, (id,))
            pedido = ncursor.fetchone()
            query = "INSERT INTO pedidos_borrados VALUES (%s, %s, %s, %s, %s, %s, DEFAULT, DEFAULT)"
            ncursor.execute(query, (
                pedido[0], # k_venta
                pedido[1], # k_cliente
                pedido[2], # k_users
                datetime.datetime.now(), # f_venta_borrado
                reason,
                id_user,
            ))
            self.mysql.connection.commit()
            return ['Pedido eliminado satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Eliminar pedido Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló la eliminación del pedido', False]

    def desasignar_lp(self, id_seller, id_lp, category):
        '''
        Desasigna una lista de precios a un vendedor
        '''
        try:
            print('desasignar_lp')
            ncursor = self.login_database()
            if category == "Bodegas":
                query = "DELETE FROM vendedor_listaprecios_bodegas WHERE k_users = %s and k_listaprecios = %s"
                ncursor.execute(query, (int(id_seller), int(id_lp)))
                self.mysql.connection.commit()
                return ['Lista de precios desasignada satisfactoriamente', True]
            query = "DELETE FROM vendedor_listaprecios WHERE k_users = %s and k_listaprecios = %s"
            ncursor.execute(query, (int(id_seller), int(id_lp),))
            self.mysql.connection.commit()
            return ['Lista de precios desasignada satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Desasignar lista de precios a vendedor Error: '+str(error))
            return ['Falló el desasignar lista de precios a vendedor', False]

    def eliminar_lista_precios(self, id_lp, category):
        '''
        Eliminar una lista de precios y todas sus 
        asociaciones
        Args:
            - id_lp: int
            - category: str
        '''
        try:
            print('eliminar_lista_precios')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            if category == "Bodegas":
                query = "DELETE FROM namelp_bodegas WHERE k_listaprecios = %s"
                ncursor.execute(query, (id_lp,))
                query = "DELETE FROM listaprecios_bodegas WHERE k_listaprecios = %s"
                ncursor.execute(query, (id_lp,))
                query = "DELETE FROM vendedor_listaprecios_bodegas WHERE k_listaprecios = %s"
                ncursor.execute(query, (id_lp,))
            else:
                query = "DELETE FROM namelp WHERE k_listaprecios = %s"
                ncursor.execute(query, (id_lp,))
                query = "DELETE FROM listaprecios WHERE k_listaprecios = %s"
                ncursor.execute(query, (id_lp,))
                query = "DELETE FROM vendedor_listaprecios WHERE k_listaprecios = %s"
                ncursor.execute(query, (id_lp,))
            self.mysql.connection.commit()
            return ['Lista de precios eliminada satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Eliminar lista de precios Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló la eliminación de la lista de precios', False]

    def eliminar_zona(self, id_zone):
        '''
        Elimina una zona
        '''
        try:
            print('eliminar_zona')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            query = "DELETE FROM zona WHERE k_zona = %s"
            ncursor.execute(query, (id_zone,))
            query = "DELETE FROM zona_departamento WHERE k_zona = %s"
            ncursor.execute(query, (id_zone,))
            query = "DELETE FROM zona_vendedor WHERE k_zona = %s"
            ncursor.execute(query, (id_zone,))
            query = "DELETE FROM presupuesto_zonas WHERE k_zona = %s"
            ncursor.execute(query, (id_zone,))
            self.mysql.connection.commit()
            return ['Zona eliminada', True]
        except mysql.connector.Error as error:
            print('Eliminar zona Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló la eliminación de la zona', False]

    def eliminar_cliente(self, id_client):
        '''
        Eliminamos un cliente de la base de datos
        Args:
            id_user: int
        '''
        try:
            print('eliminar_cliente')
            ncursor = self.login_database()
            query = "DELETE FROM clients WHERE k_cliente = %s"
            ncursor.execute(query, (id_client,))
            self.mysql.connection.commit()
            return ['Cliente eliminado', True]
        except mysql.connector.Error as error:
            print('Eliminar cliente Error: '+str(error))
            return ['Falló la eliminación del cliente', False]

    def eliminar_usuario(self, id_user):
        '''
        Eliminamos un usuario de la base de datos
        Args:
            id_user: int
        '''
        try:
            print('eliminar_usuario')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE users SET b_active = 0 WHERE k_users = %s"
            ncursor.execute(query, (id_user,))
            self.mysql.connection.commit()
            return ['Usuario eliminado', True]
        except mysql.connector.Error as error:
            print('Eliminar usuario Error: '+str(error))
            return ['Falló el proceso: Eliminar usuario', False]
    
    def eliminar_vendedor(self, id_vendedor):
        '''
        Eliminamos un vendedor de la base de datos
        Args:
            id_vendedor: int
        '''
        try:
            print('eliminar_vendedor')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "DELETE FROM vendedor_listaprecios WHERE k_users = %s"
            ncursor.execute(query, (id_vendedor,))
            query = "DELETE FROM zona_vendedor WHERE k_users = %s"
            ncursor.execute(query, (id_vendedor,))
            query = "UPDATE users SET b_active = 0 WHERE k_users = %s"
            ncursor.execute(query, (id_vendedor,))
            self.mysql.connection.commit()
            return ['Vendedor eliminado', True]
        except mysql.connector.Error as error:
            print('Eliminar vendedor Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el proceso: Eliminar vendedor', False]
    
    # UPDATES
    def completar_pedido_bodega(self, id_pedido):
        '''
        Actualizamos el estado de un pedido de bodega
        Args:
            id_pedido: int
        '''
        try:
            print('completar_pedido_bodega')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Traer el pedido
            query = "SELECT k_productos, q_cantidad, q_cantidad_despachada FROM venta_bodegas WHERE k_venta_bodegas = %s;"
            ncursor.execute(query, (id_pedido,))
            ventas = ncursor.fetchall()
            query = "UPDATE venta_bodegas SET n_categoria = 'Despachado' WHERE k_venta_bodegas = %s and k_productos = %s;"
            for venta in ventas:
                ncursor.execute(query, (id_pedido, venta[0]))
            # Actualizar el estado del pedido
            query = "UPDATE pedidos_bodegas SET n_estadop0 = 'Despachado' WHERE k_venta_bodegas = %s"
            ncursor.execute(query, (id_pedido,))
            self.mysql.connection.commit()
            return ['Pedido bodega completado', True]
        except mysql.connector.Error as error:
            print('Completar pedido bodega Error: '+str(error))
            return ['Falló el proceso: Completar pedido bodega', False]
        
    def eliminar_link_lp(self, category, id_lp):
        '''
        Borra el link de una lista de precios
        Args:
            - category: str
            - id_lp: int
        '''
        try:
            # Verifica que la lista de precios exista
            ncursor = self.login_database()
            lp, exists = self.consultar_lista_precio(id_lp, category)
            if exists:
                if category == 'Pedidos':
                    query = "UPDATE namelp SET n_link = NULL WHERE k_listaprecios = %s"
                else:
                    query = "UPDATE namelp_bodegas SET n_link = NULL WHERE k_listaprecios = %s"
                ncursor.execute(query, (id_lp,))
                self.mysql.connection.commit()
                return ['Link eliminado', True]
            else:
                return ['La lista de precios no existe', False]
        except mysql.connector.Error as error:
            print('Borrar link de lista de precios Error: '+str(error))
            return ['Falló el proceso: Borrar link de lista de precios', False]

    def registrar_link_lp(self, category, id_lp, link):
        '''
        Actualiza el link de una lista de precios, este link
        es una ruta al bucket S3 de Company.
        Args:
            - category: str
            - id_lp: int
            - link: str
        '''
        try:
            # Verifica que la lista de precios exista
            ncursor = self.login_database()
            lp, exists = self.consultar_lista_precio(id_lp, category)
            if exists:
                if category == 'Pedidos':
                    query = "UPDATE namelp SET n_link = %s WHERE k_listaprecios = %s"
                else:
                    query = "UPDATE namelp_bodegas SET n_link = %s WHERE k_listaprecios = %s"
                ncursor.execute(query, (link, id_lp))
                self.mysql.connection.commit()
                return ['Link registrado', True]
            else:
                return ['La lista de precios no existe', False]
        except mysql.connector.Error as error:
            print('registrar_link_lp Error: '+str(error))
            return ['Falló el proceso: Registrar link', False]

    def revisar_reclamacion(self, id_reclamacion):
        '''
        Actualiza el estado de una reclamación a "Revisado"
        Args:
            - id_reclamacion: int
        '''
        try:
            print('revisar_reclamacion')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE claims SET n_status = 'Revisado' WHERE k_claim = %s"
            ncursor.execute(query, (id_reclamacion,))
            self.mysql.connection.commit()
            return ['Reclamación revisada satisfactoriamente.', True]
        except mysql.connector.Error as error:
            print('revisar_reclamacion Error: '+str(error))
            return ['No se puedo revisar la reclamación', False]

    def actualizar_contraseña(self, id_usuario, password):
        '''
        Actualizamos la contraseña de un usuario
        Args:
            id_usuario: int
        '''
        try:
            print('actualizar_contraseña')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE users SET o_password = %s WHERE k_users = %s"
            ncursor.execute(query, (password, id_usuario,))
            self.mysql.connection.commit()
            return ['Contraseña actualizada', True]
        except mysql.connector.Error as error:
            print('Actualizar contraseña Error: '+str(error))
            return ['Falló el proceso: Actualizar contraseña', False]

    def actualizar_obs_cotizacion(self, id_cotizacion, obs):
        '''
        Actualizamos las observaciones de una cotización
        Args:
            id_cotizacion: int
            obs: str
        '''
        try:
            print('actualizar_obs_cotizacion')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE pedidos_cotizaciones SET n_observaciones = %s WHERE k_venta_cotizacion = %s"
            ncursor.execute(query, (obs, id_cotizacion,))
            self.mysql.connection.commit()
            return ['Observaciones actualizadas', True]
        except mysql.connector.Error as error:
            print('Actualizar observaciones cotización Error: '+str(error))
            return ['Falló la actualización de las observaciones', False]

    def actualizar_nota_cliente_agenda(self, id_cliente, id_vendedor, nota):
        '''
        Actualizamos la nota de un cliente en la agenda
        Args:
            id_cliente: int
            id_vendedor: int
            nota: str
        '''
        try:
            print('actualizar_nota_cliente_agenda')
            ncursor = self.login_database()
            query = "UPDATE agenda SET n_notas = %s WHERE k_cliente = %s AND k_users = %s"
            ncursor.execute(query, (nota, id_cliente, id_vendedor,))
            self.mysql.connection.commit()
            return ['Nota actualizada', True]
        except mysql.connector.Error as error:
            print('Actualizar nota cliente agenda Error: '+str(error))
            return ['Falló la actualización de la nota', False]

    def actualizar_bodega(self, bodega):
        '''
        Actualiza una bodega
        Args:
            bodega: dict
        '''
        try:
            print('actualizar_bodega')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "UPDATE bodegas SET n_nombre = %s, k_users = %s WHERE k_bodega = %s"
            ncursor.execute(query, (bodega['nameBodega'], bodega['idSeller'], bodega['id'],))
            self.mysql.connection.commit()
            return ['Bodega actualizada', True]
        except mysql.connector.Error as error:
            print('Actualizar bodega Error: '+str(error))
            return ['Falló la actualización de la bodega', False]

    def completar_pedido(self, id_pedido):
        '''
        Actualizamos el estado de un pedido
        Args:
            id_pedido: int
        '''
        try:
            print('completar_pedido')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Traer el pedido
            query = "SELECT k_productos, q_cantidad, q_cantidad_despachada FROM venta WHERE k_venta = %s"
            ncursor.execute(query, (id_pedido,))
            ventas = ncursor.fetchall()
            query = "UPDATE venta SET n_categoria = 'Despachado' WHERE k_venta = %s and k_productos = %s"
            for venta in ventas:
                ncursor.execute(query, (id_pedido, venta[0]))
            # Actualizar el estado del pedido
            query = "UPDATE pedidos SET n_estadop2 = 'Despachado' WHERE k_venta = %s"
            ncursor.execute(query, (id_pedido,))
            self.mysql.connection.commit()
            return ['Pedido completado', True]
        except mysql.connector.Error as error:
            print('Completar pedido Error: '+str(error))
            return ['Falló el proceso: Completar pedido', False]

    def despachar_pedido_bodega(self, id_pedido, pedido):
        '''
        Despachar un pedido de una bodega
        Args:
            - id_pedido: int
        '''
        try:
            print('despachar_pedido_bodega')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Fecha de hoy
            today = datetime.datetime.now()
            # Verificar que el pedido este por despachar
            query = "SELECT n_estadop0 FROM pedidos_bodegas WHERE k_venta_bodegas = %s"
            ncursor.execute(query, (id_pedido,))
            pedido_data = ncursor.fetchone()
            if pedido_data and (pedido_data[0] == 'Por despachar' or pedido_data[0] == 'Incompleto'):
                # 1. Actualizar venta
                # 1.1 Traer los productos del pedido
                query = "SELECT k_productos, q_cantidad FROM venta_bodegas WHERE k_venta_bodegas = %s"
                ncursor.execute(query, (id_pedido,))
                ventas = ncursor.fetchall()
                ncursor.execute("SET SQL_SAFE_UPDATES = 0")

                incompleto_status = False
                no_products = 0

                for venta in ventas:
                    for data in pedido:
                        if data[2] == 0:
                            no_products += 1
                        if venta[0] == data[0]:
                            if int(venta[1]) == int(data[2]): #Cantidad pedida = Cantidad despachada
                                query = "UPDATE venta_bodegas SET q_cantidad_despachada = %s, n_categoria = 'Despachado' WHERE k_venta_bodegas = %s AND k_productos = %s"
                            else:
                                incompleto_status = True
                                query = "UPDATE venta_bodegas SET q_cantidad_despachada = %s, n_categoria = 'Incompleto' WHERE k_venta_bodegas = %s AND k_productos = %s"
                            ncursor.execute(query, (int(data[2]), id_pedido, venta[0], ))
                # 2. Actualizar estado pedido
                if incompleto_status:
                    query = "UPDATE pedidos_bodegas SET n_estadop0 = 'Incompleto', f_venta_despachado = %s WHERE k_venta_bodegas = %s"
                else:
                    query = "UPDATE pedidos_bodegas SET n_estadop0 = 'Despachado', f_venta_despachado = %s WHERE k_venta_bodegas = %s"
                ncursor.execute(query, (today, id_pedido, ))
                self.mysql.connection.commit()
                return ['Pedido despachado', True]
            return ['El pedido no esta autorizado o no esta facturado', False]
        except mysql.connector.Error as error:
            print('Despachar pedido Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el proceso: Despachar pedido', False]

    def despachar_pedido(self, id_pedido, pedido):
        '''
        Despachar un pedido
        Args:
            - id_pedido: int
        '''
        try:
            print('despachar_pedido')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Fecha de hoy
            today = datetime.datetime.now()
            # Verificar que el pedido este autorizado y este facturado
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "SELECT n_estadop0, n_estadop1 FROM pedidos WHERE k_venta = %s"
            ncursor.execute(query, (id_pedido,))
            pedido_data = ncursor.fetchone()
            if pedido_data and pedido_data[0] == 'Autorizado' and pedido_data[1] == 'Facturado':
                # 1. Actualizar venta
                # 1.1 Traer los productos del pedido
                query = "SELECT k_productos, q_cantidad FROM venta WHERE k_venta = %s"
                ncursor.execute(query, (id_pedido,))
                ventas = ncursor.fetchall()

                incompleto_status = False
                no_products = 0

                for venta in ventas:
                    for data in pedido:
                        if data[2] == 0:
                            no_products += 1
                        if venta[0] == data[0]:
                            if int(venta[1]) == int(data[2]): #Cantidad pedida = Cantidad despachada
                                query = "UPDATE venta SET q_cantidad_despachada = %s, n_categoria = 'Despachado' WHERE k_venta = %s AND k_productos = %s"
                            else:
                                incompleto_status = True
                                query = "UPDATE venta SET q_cantidad_despachada = %s, n_categoria = 'Incompleto' WHERE k_venta = %s AND k_productos = %s"
                            ncursor.execute(query, (int(data[2]), id_pedido, venta[0], ))
                # 2. Actualizar estado pedido
                if incompleto_status:
                    query = "UPDATE pedidos SET n_estadop2 = 'Incompleto', f_venta_despachado = %s WHERE k_venta = %s"
                else:
                    query = "UPDATE pedidos SET n_estadop2 = 'Despachado', f_venta_despachado = %s WHERE k_venta = %s"
                ncursor.execute(query, (today, id_pedido, ))
                self.mysql.connection.commit()
                return ['Pedido despachado', True]
            return ['El pedido no esta autorizado o no esta facturado', False]
        except mysql.connector.Error as error:
            print('Despachar pedido Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el proceso: Despachar pedido', False]

    def facturar_pedido(self, id_pedido):
        '''
        Actualiza el estado de un pedido a facturado
        Args:
            - id_pedido: int
        '''
        try:
            print('facturar_pedido')
            ncursor = self.login_database()
            # Calcular fecha
            fecha = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Verificar que el pedido este autorizadoy no este ya facturado
            query = "SELECT n_estadop0, n_estadop1 FROM pedidos WHERE k_venta = %s"
            ncursor.execute(query, (id_pedido,))
            pedido = ncursor.fetchone()
            if pedido and pedido[0] == 'Autorizado' and pedido[1] == 'Por facturar':
                query = "UPDATE pedidos SET n_estadop1 = 'Facturado', f_venta_facturado = %s WHERE k_venta = %s"
                ncursor.execute(query, (fecha, id_pedido, ))
                self.mysql.connection.commit()
                return ['Pedido facturado', True]
            return ['El pedido no se encuentra autorizado', False]
        except mysql.connector.Error as error:
            print('Facturar pedido Error: '+str(error))
            return ['Falló el proceso: Facturar pedido', False]

    def desautorizar_pedido(self, id_pedido):
        '''
        Desautoriza un pedido
        Args:
            - id_pedido: int
        '''
        try:
            print('desautorizar_pedido')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Verificar que el pedido no este facturado
            query = "SELECT n_estadop0, n_estadop1 FROM pedidos WHERE k_venta = %s"
            ncursor.execute(query, (id_pedido,))
            pedido = ncursor.fetchone()
            if pedido and pedido[0] == 'Autorizado' and pedido[1] == 'Por facturar':
                query = "UPDATE pedidos SET n_estadop0 = 'No autorizado' WHERE k_venta = %s"
                ncursor.execute(query, (id_pedido,))
                self.mysql.connection.commit()
                return ['Pedido desautorizado', True]
            return ['El pedido no cumple las condiciones para su facturación', False]
        except mysql.connector.Error as error:
            print('Desautorizar pedido Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el proceso: Desautorizar pedido', False]

    def autorizar_pedido(self, id_pedido):
        '''
        Autoriza un pedido
        Args:
            id_pedido: int
        '''
        try:
            print('autorizar_pedido')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            # Verificar que no este autorizado
            query = "SELECT n_estadop0 FROM pedidos WHERE k_venta = %s"
            ncursor.execute(query, (id_pedido,))
            pedido = ncursor.fetchone()
            if pedido and pedido[0] == 'No autorizado':
                f_autorizacion = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                query = "UPDATE pedidos SET n_estadop0 = 'Autorizado', f_venta_autorizado = %s WHERE k_venta = %s"
                ncursor.execute(query, (f_autorizacion, id_pedido,))
                self.mysql.connection.commit()
                return ['Pedido autorizado', True]
            return ['El pedido ya esta autorizado', False]
        except mysql.connector.Error as error:
            print('Autorizar pedido Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló el proceso: Autorizar pedido', False]

    def actualizar_obs_bodega(self, k_venta, obs):
        '''
        Actualiza la observación de un pedido
        Args:
            k_venta: ID de la venta
            obs: STRING obs
        '''
        try:
            print('actualizar_obs_bodega')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0;")
            query = "UPDATE pedidos_bodegas SET n_observaciones = %s WHERE k_venta_bodegas = %s"
            ncursor.execute(query, (obs, k_venta,))
            self.mysql.connection.commit()
            return ['Observación actualizada satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Actualizar observación Error: '+str(error))
            return [f'Falló la actualización de la observación', False]

    def actualizar_obs(self, k_venta, obs):
        '''
        Actualiza la observación de un pedido
        Args:
            k_venta: ID de la venta
            obs: STRING obs
        '''
        try:
            print('actualizar_obs')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0;")
            query = "UPDATE pedidos SET n_observaciones = %s WHERE k_venta = %s"
            ncursor.execute(query,  (obs, k_venta, ))
            self.mysql.connection.commit()
            return ['Observación actualizada satisfactoriamente', True]
        except mysql.connector.Error as error:
            print('Actualizar observación Error: '+str(error))
            return [f'Falló la actualización de la observación', False]

    def actualizar_lista_precios(self, lista_precios, productos, category):
        '''
        Actualiza la información de una lista de precios
        incluido sus productos
        '''
        try:
            print('actualizar_lista_precios')
            ncursor = self.login_database()
            self.mysql.connection.begin()
            if category == "Bodegas":
                query = "UPDATE namelp_bodegas SET n_nombre = %s, n_marca = %s, n_link = %s WHERE k_listaprecios = %s"
                ncursor.execute(query, (lista_precios['name'], lista_precios['brand'], lista_precios['link'], lista_precios['id']))
                query = "DELETE FROM listaprecios_bodegas WHERE k_listaprecios = %s"
                ncursor.execute(query, (lista_precios['id'],))
                for producto in productos:
                    query = "INSERT INTO listaprecios_bodegas VALUES (%s, %s, %s, %s, DEFAULT, DEFAULT)"
                    ncursor.execute(query, (lista_precios['id'], lista_precios['brand'], producto[0], str(producto[1]).replace(',', '.')))
                self.mysql.connection.commit()
                return ['Lista de precios actualizada', True]
            else:
                query = "UPDATE namelp SET n_nombre = %s, n_marca = %s, n_link = %s WHERE k_listaprecios = %s"
                ncursor.execute(query, (lista_precios['name'], lista_precios['brand'], lista_precios['link'], lista_precios['id']))
                query = "DELETE FROM listaprecios WHERE k_listaprecios = %s"
                ncursor.execute(query, (lista_precios['id'],))
                for producto in productos:
                    query = "INSERT INTO listaprecios VALUES (%s, %s, %s, %s, %s, DEFAULT, DEFAULT)"
                    ncursor.execute(query, (lista_precios['id'], lista_precios['brand'], producto[0], producto[1], str(producto[2]).replace(',', '.')))
                self.mysql.connection.commit()
                return ['Lista de precios actualizada', True]
        except mysql.connector.Error as error:
            print('Actualizar lista de precios Error: '+str(error))
            self.mysql.connection.rollback()
            return ['Falló la actualización de la lista de precios', False]

    def actualizar_zona(self, info_zone):
        '''
        Actualizamos la información de la zona
        '''
        try:
            print('actualizar_zona')
            ncursor = self.login_database()
            self.mysql.connection.begin()

            zone = info_zone['zone']
            presupuestos = info_zone['presupuestos']

            query = "UPDATE zona SET n_zona = %s WHERE k_zona = %s"
            ncursor.execute(query, (zone['name'], zone['id'],))

            query = "DELETE FROM zona_departamento WHERE k_zona = %s"
            ncursor.execute(query, (zone['id'],))
            for department in zone['department']:
                query = "INSERT INTO zona_departamento VALUES (%s, %s, DEFAULT, DEFAULT)"
                ncursor.execute(query, (zone['id'], department,))

            # Presupuestos
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = "SELECT q_mes, q_presupuesto FROM presupuesto_zonas WHERE k_zona = %s"
            ncursor.execute(query, (zone['id'],))
            exists = ncursor.fetchall()
            if exists:
                query = "UPDATE presupuesto_zonas SET q_presupuesto = %s WHERE k_zona = %s AND q_mes = %s"
                for presupuesto in presupuestos:
                    ncursor.execute(query, (presupuesto[1], zone['id'], presupuesto[0],))
            else:
                query = "INSERT INTO presupuesto_zonas VALUES (%s, %s, %s, DEFAULT, DEFAULT)"
                for presupuesto in presupuestos:
                    ncursor.execute(query, (zone['id'], presupuesto[0], presupuesto[1],))
            self.mysql.connection.commit()

            query = "SELECT k_zona, n_zona FROM zona WHERE k_zona = %s AND b_active = 1"
            ncursor.execute(query, (zone['id'],))
            _zone = ncursor.fetchone()
            return [['Zona actualizada', _zone], True]
        except mysql.connector.Error as error:
            print('Actualizar zona Error: '+ str(error))
            return ['Falló la actualización de la zona', False]

    def actualizar_cliente(self, info):
        '''
        Actualiza la información del cliente
        Args
            id: int
            n_cliente: str
            n_correo?: str
            n_direccion: str
            n_departamento: str
            n_ciudad: str
            q_telefono: int
            q_telefono2: int
            zona: int
        '''
        try:
            print('actualizar_cliente')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = """
            UPDATE clients SET n_cliente = %s, n_correo = %s, n_direccion = %s, k_departamento = %s, 
            n_ciudad = %s, q_telefono = %s, q_telefono2 = %s, k_zona = %s WHERE k_cliente = %s
            """
            ncursor.execute(query, (
                info['name'], 
                info['email'], 
                info['address'], 
                info['department'], 
                info['city'], 
                info['phone'], 
                info['phone2'], 
                info['zone'], 
                info['id']))
            self.mysql.connection.commit()
            return ['Cliente actualizado', True]
        except mysql.connector.Error as error:
            print('Actualizar cliente Error: '+str(error))
            return ['Falló el proceso: Actualizar cliente', False]

    def actualizar_usuario(self, info):
        '''
        Actualizamos la información del usuario
        Args:
            id: number,
            email: str
            name: str
            lastname: str
            hierarchy: str
        '''
        try:
            print('actualizar_usuario')
            ncursor = self.login_database()
            ncursor.execute("SET SQL_SAFE_UPDATES = 0")
            query = """
            UPDATE users SET n_nombre = %s, n_apellido = %s, n_correo = %s, n_categoria = %s WHERE k_users = %s
            """
            ncursor.execute(query, (
                info['name'], 
                info['lastname'], 
                info['email'], 
                info['hierarchy'], 
                info['id']))
            self.mysql.connection.commit()
            return ['Usuario actualizado', True]
        except mysql.connector.Error as error:
            print('Actualizar usuario Error: '+str(error))
            return ['Falló el proceso de actualizar usuario', False]