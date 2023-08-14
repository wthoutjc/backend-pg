from flask import Blueprint, request, jsonify, make_response

# Auth
from flask_jwt_extended import jwt_required

# Tools
import json                    # Estructura json

class ClientsAPI:
    def __init__(self, controller):
        self.controller = controller
        self.db = self.controller.get_db()

        self.clients = Blueprint('clients', __name__)

        @self.clients.route("/clients", defaults={'id': None}, methods=['GET', 'POST'])
        @self.clients.route("/clients/<int:id>", methods=['GET', 'PUT', 'DELETE'])
        @jwt_required()
        def clients_route(id):
            print('clients_route')
            if request.method == 'GET':
                if not id:
                    limit = int(request.args.get('limit', 20))
                    offset = int(request.args.get('offset', 0))

                    filter = request.args.get('filter')

                    if filter is not None:
                        filter = str(filter)

                    clients, success = self.db.consultar_clientes(limit, offset, filter)
                    if success:
                        return make_response(jsonify({"totalClients": clients[0], "clients": clients[1], "ok": True}), 200)
                    else:
                        return make_response(jsonify({"error": clients, "ok": False}), 500)
                else:
                    [client, pesosfact_anio], success = self.db.consultar_cliente(id)
                    return make_response(jsonify({"client": client, "pesosFactYear": pesosfact_anio, "ok": success}), 200 if success else 500)
            elif request.method == 'POST':
                # Registrar cliente
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                message, success = self.db.registrar_cliente(json_data)
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
            elif request.method == 'PUT':
                # Actualizar cliente
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                message, success = self.db.actualizar_cliente(json_data)
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
            elif request.method == 'DELETE':
                # Eliminar cliente
                message, success = self.db.eliminar_cliente(id)
                return make_response(jsonify({"message": message, "ok": success}), 200)
            return make_response(jsonify({"error": "Método no permitido", "ok": False}), 405)

        @self.clients.route("/clients/favorites", defaults={'id': None}, methods=['POST', 'DELETE'])
        @self.clients.route("/clients/favorites/<int:id>", methods=['GET'])
        @jwt_required()
        def clients_favorites(id):
            print('clients_favorites')
            if request.method == 'GET':
                if id:
                    # Consultar favoritos de un cliente
                    month = request.args.get('month')

                    limit = int(request.args.get('limit', 20))
                    offset = int(request.args.get('offset', 0))

                    filter = request.args.get('filter')

                    [favorites, total_favorites], success = self.db.consultar_favoritos_cliente(
                        id, int(month), limit, offset, filter)
                    return make_response(jsonify({"favorites": favorites, "totalFavorites": total_favorites, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "No se ha especificado la cédula y/o mes del usuario", "ok": False}), 400)
            if request.method == 'POST':
                # Registrar cliente
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                message, success = self.db.registrar_cliente_favorito(
                    json_data['idClient'], json_data['idUser'])
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 400)
            if request.method == 'DELETE':
                # Eliminar cliente
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                message, success = self.db.eliminar_cliente_favorito(
                    json_data['idClient'], json_data['idUser'])
                return make_response(jsonify({"message": message, "ok": success}), 200)
            return make_response(jsonify({"error": "Método no permitido", "ok": False}), 405)