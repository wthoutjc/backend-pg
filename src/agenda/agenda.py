from flask import Blueprint, request, jsonify, make_response

# Auth
from flask_jwt_extended import jwt_required

# Tools
import json                     # Estructura json

class AgendaAPI:
    def __init__(self, controller):
        self.controller = controller
        self.db = self.controller.get_db()

        self.agenda = Blueprint('agenda', __name__)

        @self.agenda.route("/nota-agenda/<int:id_cliente>", methods=["GET", "PUT", "DELETE"])
        @jwt_required()
        def route_note_agenda(id_cliente):
            print('route_note_agenda')
            if id_cliente:
                if request.method == "GET":
                    id_vendedor = request.args.get('idSeller', None)

                    nota, success = self.db.consultar_nota_agenda(id_cliente, id_vendedor)
                    return make_response(jsonify({"message": nota, "ok": success}), 200 if success else 500)
                if request.method == "PUT":
                    id_vendedor = request.args.get('idSeller', None)

                    data_raw = request.data.decode("utf-8")
                    json_data = json.loads(data_raw)

                    try:
                        nota = json_data['note']
                    except KeyError:
                        nota = None

                    if nota and id_vendedor:
                        message, success = self.db.actualizar_nota_cliente_agenda(
                            id_cliente, id_vendedor, nota)
                        return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                    return make_response(jsonify({"message": "Los datos enviados no son válidos", "ok": False}), 500)
            return make_response(jsonify({"message": "No se ha especificado la cédula del vendedor.", "ok": False}), 500)

        @self.agenda.route('/agenda', defaults={'id': None}, methods=["GET", "POST"])
        @self.agenda.route("/agenda/<int:id>", methods=["GET", "PUT", "DELETE", "POST"])
        @jwt_required()
        def route_agenda(id):
            print('route_agenda')
            if request.method == "GET":
                if id:
                    id_cliente = request.args.get('idClient', None)

                    if id_cliente:
                        agenda, cliente, success = self.db.consultar_agenda_cliente(
                            id, id_cliente)
                        return make_response(jsonify({"message": agenda, "client": cliente, "ok": success}), 200 if success else 500)

                    limit = int(request.args.get('limit', 20))
                    offset = int(request.args.get('offset', 0))
                    filter = request.args.get('filter', None)

                    total_agenda, agenda, success = self.db.consultar_agenda(
                        id, limit, offset, filter)
                    return make_response(jsonify({"message": "Resultados agenda" if success else "No hay clientes registrados", "agenda": agenda, "totalAgenda": total_agenda, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "No se ha especificado la cédula del vendedor.", "ok": False}), 500)
            if request.method == "POST":
                if id:
                    data_raw = request.data.decode("utf-8")
                    json_data = json.loads(data_raw)

                    try:
                        id_cliente = json_data['idClient']
                    except KeyError:
                        id_cliente = None
                    if id_cliente:
                        message, success = self.db.registrar_agenda(id, id_cliente)
                        return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                    return make_response(jsonify({"message": "No se ha especificado la cédula del cliente.", "ok": False}), 500)
                return make_response(jsonify({"message": "No se ha especificado la cédula del vendedor.", "ok": False}), 500)
            return make_response(jsonify({"message": "ok", "ok": True}), 200)