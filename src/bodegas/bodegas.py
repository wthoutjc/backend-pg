from flask import Blueprint, request, jsonify, make_response

# Auth
from flask_jwt_extended import jwt_required

# Tools
import json                     # Estructura json

class BodegaAPI:
    def __init__(self, controller):
        self.controller = controller
        self.db = self.controller.get_db()

        self.bodegas = Blueprint('bodegas', __name__)


        @self.bodegas.route('/gbodegas', defaults={'id': None}, methods=["GET", "POST"])
        @self.bodegas.route("/gbodegas/<int:id>", methods=["GET", "PUT", "DELETE"])
        @jwt_required()
        def route_gbodegas(id):
            print('route_gbodegas')
            if request.method == "GET":
                obs = request.args.get('obs', None)

                if id and obs:
                    observaciones, success = self.db.consultar_obs_bodega(id)
                    return make_response(jsonify({"obs": observaciones[0], "ok": success}), 200 if success else 500)
                elif id:
                    [pedido, info_pedido], success = self.db.consultar_pedido_bodega(id)
                    return make_response(jsonify({
                        "infoPedido": info_pedido,
                        "pedido": pedido,
                        "ok": success}), 200 if success else 500)
                else:
                    # Limit & Offset
                    limit = int(request.args.get('limit', 20))
                    offset = int(request.args.get('offset', 0))

                    # Params
                    category = request.args.get('category', "Por despachar")
                    filter = request.args.get('filter', None)

                    [total_pedidos, pedidos], success = self.db.consultar_pedidos_bodegas(
                        limit, offset, filter, category)
                    return make_response(jsonify({"totalPedidosBodega": total_pedidos, "pedidosBodega": pedidos, "ok": success}), 200 if success else 500)
            elif request.method == "PUT":
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

                dispatch = request.args.get('dispatch', None)

                if dispatch:
                    try:
                        data_raw = request.data.decode("utf-8")
                        json_data = json.loads(data_raw)
                        pedido = json_data['pedido']
                    except KeyError:
                        pedido = None

                    if pedido:
                        message, success = self.db.despachar_pedido_bodega(id, pedido)
                        return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                    return make_response(jsonify({"message": "No se ha enviado ningún pedido", "ok": False}), 500)
                elif obs and id:
                    message, success = self.db.actualizar_obs_bodega(id, obs)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
            elif request.method == "DELETE":
                if id:

                    message, success = self.db.eliminar_pedido_bodega(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "Algo salió mal", "ok": False}), 500)
            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)

        @self.bodegas.route('/bodegas', defaults={'id': None}, methods=["GET", "POST"])
        @self.bodegas.route("/bodegas/<int:id>", methods=["GET", "PUT", "DELETE"])
        @jwt_required()
        def route_bodegas(id):
            print('route_bodegas')
            if request.method == "GET":
                seller = request.args.get('seller', None)

                if seller:
                    bodega, success = self.db.consultar_bodegas_vendedor(seller)
                    return make_response(jsonify({"bodegas": bodega, "ok": success}), 200 if success else 500)
                elif id:
                    # Limit & Offset
                    limit = int(request.args.get('limit', 20))
                    offset = int(request.args.get('offset', 0))

                    # Pedidos
                    pedidos = request.args.get('pedidos', None)

                    if pedidos:
                        [total_pedidos_bodega, pedidos_bodega], success = self.db.consultar_pedidos_bodega(
                            id, limit, offset)
                        return make_response(jsonify({
                            "totalPedidosBodega": total_pedidos_bodega,
                            "pedidosBodega": pedidos_bodega,
                            "ok": success}), 200 if success else 500)

                    bodega, success = self.db.consultar_bodega(id)
                    return make_response(jsonify({
                        "bodega": bodega,
                        "ok": success}), 200 if success else 500)
                else:
                    bodegas, success = self.db.consultar_bodegas()

                    return make_response(jsonify({"bodegas": bodegas, "ok": success}), 200 if success else 500)
            elif request.method == "POST":
                if request.data:
                    data_raw = request.data.decode("utf-8")
                    json_data = json.loads(data_raw)

                    nombre = json_data['name']
                    vendedor = json_data['seller']

                    message, success = self.db.registrar_bodega(nombre, vendedor)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "No se ha enviado ningún dato", "ok": False}), 500)
            elif request.method == "PUT":
                if id:
                    data_raw = request.data.decode("utf-8")
                    json_data = json.loads(data_raw)

                    message, success = self.db.actualizar_bodega(json_data)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "No se ha enviado ningún dato", "ok": False}), 500)
            elif request.method == "DELETE":
                if id:
                    message, success = self.db.eliminar_bodega(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "Algo salió mal", "ok": False}), 500)
            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)