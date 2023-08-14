from flask import Blueprint, request, jsonify, make_response

# Auth
from flask_jwt_extended import jwt_required

# Tools
import json                     # Estructura json

class PedidosAPI:
    def __init__(self, controller):
        self.controller = controller
        self.db = self.controller.get_db()

        self.pedidos = Blueprint('pedidos', __name__)

        @self.pedidos.route('/analyze-pedido/<int:id>', methods=["POST"])
        @jwt_required()
        def route_analyze_pedido(id):
            print('route_analyze_pedido')
            data_raw = request.data.decode("utf-8")
            json_data = json.loads(data_raw)

            complete, products, message, pedido_anterior = self.db.analizar_pedido(id, json_data['pedido'])
            return make_response(jsonify({"message": message, "products": products, "ok": complete, "idPedidoAnterior": pedido_anterior}), 200 if complete else 500)

        @self.pedidos.route("/pedidos-recientes")
        @jwt_required()
        def route_pedidos_recientes():
            print('route_pedidos_recientes')

            category = request.args.get('category', None)
            if category:
                pedidos, success = self.db.consultar_pedidos_recientes(category)
                return make_response(jsonify({"pedidos": pedidos, "ok": success}), 200 if success else 500)
            return make_response(jsonify({"message": "No se envió los parámetros correspondientes", "ok": False}), 500)

        @self.pedidos.route("/cotizacion-info/<int:id>", methods=["GET", "DELETE", "PUT"])
        @jwt_required()
        def route_cotizacion_info(id):
            print('route_cotizacion_info')
            if not id:
                return make_response(jsonify({"message": "No se envió los parámetros correspondientes", "ok": False}), 500)
            elif request.method == "GET":
                obs = request.args.get('obs', None)
                if obs:
                    message, success = self.db.consultar_obs_cotizacion(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                info_cotizacion, cotizacion, success = self.db.consultar_cotizacion(id)
                return make_response(jsonify({"cotizacion": cotizacion, "infoCotizacion": info_cotizacion, "ok": success}), 200 if success else 500)
            elif request.method == "DELETE":
                message, success = self.db.eliminar_cotizacion(id)
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
            elif request.method == "PUT":
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                obs_update = request.args.get('obs_update', None)

                try:
                    obs = json_data['obs']
                except KeyError:
                    obs = None
                if obs_update and obs:
                    message, success = self.db.actualizar_obs_cotizacion(id, obs)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "Los datos enviados no son válidos", "ok": False}), 500)
            return make_response(jsonify({"message": "Método no permitido", "ok": True}), 200)

        @self.pedidos.route('/cotizacion', defaults={'id': None}, methods=["POST"])
        @self.pedidos.route("/cotizacion/<int:id>", methods=["GET"])
        @jwt_required()
        def route_cotizacion(id):
            print('route_cotizacion')
            if request.method == "GET":
                if id:
                    filter = request.args.get('filter', None)
                    month = request.args.get('month', None)
                    limit = int(request.args.get('limit', None))
                    offset = int(request.args.get('offset', None))

                    self.db.eliminar_cotizaciones_viejas(id)

                    cotizaciones, total_cotizaciones, success = self.db.consultar_cotizaciones_vendedor(
                        id, limit, offset, month, filter)
                    return make_response(jsonify({"cotizaciones": cotizaciones, "totalCotizaciones": total_cotizaciones, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "No se envió los parámetros correspondientes", "ok": False}), 500)
            elif request.method == "POST":
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                try:
                    id_vendedor = json_data['sellerId']
                    id_cliente = json_data['clientId']
                    obs = json_data['obs']
                    pedido = json_data['pedido']
                except KeyError:
                    pedido = None
                    id_vendedor = None
                    id_cliente = None
                    obs = None
                if pedido and id_vendedor and id_cliente:
                    message, success, id_nuevo_pedido = self.db.registrar_cotizacion(
                        id_vendedor, id_cliente, pedido, obs)
                    return make_response(jsonify({"message": message, "ok": success, "idNewPedido": id_nuevo_pedido}), 200 if success else 500)
                return make_response(jsonify({"message": "Los datos enviados no son válidos", "ok": False}), 500)

            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)

        @self.pedidos.route('/fase1-pedido', methods=["POST"])
        @jwt_required()
        def route_fase1_pedido():
            print('route_fase1_pedido')
            data_raw = request.data.decode("utf-8")
            json_data = json.loads(data_raw)

            try:
                pedido = json_data['order']
            except KeyError:
                pedido = None

            if pedido:
                order, success = self.db.pedido_fase1(pedido)
                return make_response(jsonify({"order": order, "ok": success}), 200 if success else 500)
            return make_response(jsonify({"message": "Datos no válidos", "ok": False}), 500)


        @self.pedidos.route('/fase1-pedido-bodega', methods=["POST"])
        @jwt_required()
        def route_fase1_pedido_bodega():
            print('route_fase1_pedido_bodega')
            data_raw = request.data.decode("utf-8")
            json_data = json.loads(data_raw)

            try:
                pedido = json_data['order']
            except KeyError:
                pedido = None

            if pedido:
                order, success = self.db.pedido_fase1_bodega(pedido)
                return make_response(jsonify({"order": order, "ok": success}), 200 if success else 500)
            return make_response(jsonify({"message": "Datos no válidos", "ok": False}), 500)

        @self.pedidos.route('/registrar-pedido', methods=["POST"])
        @jwt_required()
        def route_registrar_pedido():
            print('route_registrar_pedido')
            data_raw = request.data.decode("utf-8")
            json_data = json.loads(data_raw)

            try:
                id_vendedor = json_data['sellerId']
                id_cliente = json_data['clientId']
                obs = json_data['obs']
                pedido = json_data['pedido']
            except KeyError:
                pedido = None
                id_vendedor = None
                id_cliente = None
                obs = None

            if pedido and id_vendedor and id_cliente:
                message, id_pedido, success = self.db.registrar_pedido(
                    id_vendedor, id_cliente, pedido, obs)
                return make_response(jsonify({"message": message, "idNewPedido": id_pedido, "ok": success}), 200 if success else 500)
            return make_response(jsonify({"message": "¡Algo no salió bien!", "idNewPedido": 0, "ok": False}), 500)

        @self.pedidos.route('/registrar-pedido-bodega', methods=["POST"])
        @jwt_required()
        def route_registrar_pedido_bodega():
            print('route_registrar_pedido_bodega')
            data_raw = request.data.decode("utf-8")
            json_data = json.loads(data_raw)

            try:
                id_vendedor = json_data['sellerId']
                obs = json_data['obs']
                pedido = json_data['pedido']
            except KeyError as e:
                print(f'Error registrar-pedido-bodega: {e}')
                pedido = None
                id_vendedor = None
                obs = None

            if pedido and id_vendedor:
                message, id_pedido, success = self.db.registrar_pedido_bodega(
                    id_vendedor, pedido, obs)
                return make_response(jsonify({"message": message, "idNewPedido": id_pedido, "ok": success}), 200 if success else 500)
            return make_response(jsonify({"message": "¡Algo no salió bien!", "idNewPedido": 0, "ok": False}), 500)

        @self.pedidos.route('/pedidos-vendedor/<id>')
        @jwt_required()
        def get_pedido_seller_stat(id):
            print('get_pedido_seller_stat')
            limit = int(request.args.get('limit', 20))
            offset = int(request.args.get('offset', 0))

            # Filtros
            filter = request.args.get('filter', None)
            category = request.args.get('category', 'Todos')
            date = request.args.get('date', 13)

            [pedido_data, total_pedidos,
                rendimiento], success = self.db.consultar_pedidos_vendedor_stat(id, limit, offset, filter, category, int(date))
            return make_response(jsonify({"pedidos": pedido_data, "total_pedidos": total_pedidos, "rendimiento": rendimiento, "ok": success}), 200 if success else 500)

        @self.pedidos.route('/pedidos-bodegas', defaults={'id': None})
        @self.pedidos.route("/pedidos-bodegas/<int:id>", methods=["GET", "PUT"])
        @jwt_required()
        def route_pedidos_bodegas(id):  # id: id del vendedor
            print('route_pedidos_bodegas')
            if request.method == "GET":
                # Limit & Offset
                limit = int(request.args.get('limit', 20))
                offset = int(request.args.get('offset', 0))

                obs = request.args.get('obs', None)

                if obs:
                    category = request.args.get('category', None)

                    observaciones, success = self.db.consultar_obs(obs, category)
                    return make_response(jsonify({"obs": observaciones[0], "ok": success}), 200 if success else 500)
                if id:
                    # Params
                    category = request.args.get('category', "Por despachar")
                    filter = request.args.get('filter', None)

                    [pedidos, total_pedidos], success = self.db.consultar_pedidos_bodegas_por_vendedor(
                        id, limit, offset, filter, category)

                    return make_response(jsonify({"pedidosBodega": pedidos, "totalPedidosBodega": total_pedidos, "ok": success}), 200 if success else 500)
            elif request.method == "PUT" and id:
                message, success = self.db.completar_pedido_bodega(id)
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)

        @self.pedidos.route('/pedidos', defaults={'id': None}, methods=["GET"])
        @self.pedidos.route("/pedidos/<int:id>", methods=["GET", "PUT", "DELETE"])
        @jwt_required()
        def route_pedidos(id):
            print('route_pedidos')
            if request.method == "GET":
                # Limit & Offset
                limit = int(request.args.get('limit', 20))
                offset = int(request.args.get('offset', 0))

                client = request.args.get('client', None)
                obs = request.args.get('obs', None)

                if client:
                    [pedidos, total_pedidos], success = self.db.consultar_pedidos_cliente(
                        client, limit, offset)
                    return make_response(jsonify({"pedidos": pedidos, "total_pedidos": total_pedidos, "ok": success}), 200 if success else 500)
                elif obs:
                    category = request.args.get('category', None)

                    observaciones, success = self.db.consultar_obs(obs, category)
                    return make_response(jsonify({"obs": observaciones[0], "ok": success}), 200 if success else 500)
                elif id:
                    [pedido, info_pedido], success = self.db.consultar_pedido(id)
                    return make_response(jsonify({"pedido": pedido, "infoPedido": info_pedido, "ok": success}), 200 if success else 500)
                else:
                    # Params
                    category = request.args.get('category', "No autorizado")
                    filter = request.args.get('filter', None)

                    [pedidos, total_pedidos], success = self.db.consultar_pedidos(
                        limit, offset, filter, category)

                    return make_response(jsonify({"pedidos": pedidos, "total_pedidos": total_pedidos, "ok": success}), 200 if success else 500)
            if request.method == "PUT":
                # Descomponer json_data
                # Obs
                try:
                    data_raw = request.data.decode("utf-8")
                    json_data = json.loads(data_raw)
                    obs = json_data['obs']
                except KeyError:
                    obs = None
                except json.decoder.JSONDecodeError:
                    obs = None

                authorize = request.args.get('authorize', None)
                unauthorize = request.args.get('unauthorize', None)
                invoice = request.args.get('invoice', None)
                dispatch = request.args.get('dispatch', None)
                complete = request.args.get('complete', None)

                if complete:
                    message, success = self.db.completar_pedido(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                if dispatch:
                    try:
                        data_raw = request.data.decode("utf-8")
                        json_data = json.loads(data_raw)
                        pedido = json_data['pedido']
                    except KeyError:
                        pedido = None

                    if pedido:
                        message, success = self.db.despachar_pedido(id, pedido)
                        return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                    return make_response(jsonify({"message": "No se ha enviado ningún pedido", "ok": False}), 500)
                elif invoice:
                    message, success = self.db.facturar_pedido(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                elif unauthorize and id:
                    message, success = self.db.desautorizar_pedido(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                elif authorize and id:
                    message, success = self.db.autorizar_pedido(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                elif obs and id:
                    message, success = self.db.actualizar_obs(id, obs)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "Método ok", "ok": True}), 200 if True else 500)
            if request.method == "DELETE":
                if id:
                    data_raw = request.data.decode("utf-8")
                    json_data = json.loads(data_raw)

                    reason = json_data['reason']
                    id_user = json_data['idUser']

                    message, success = self.db.eliminar_pedido(id, reason, id_user)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "Algo salió mal", "ok": False}), 500)
            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)