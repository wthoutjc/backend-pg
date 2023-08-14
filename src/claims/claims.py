from flask import Blueprint, request, jsonify, make_response

# Auth
from flask_jwt_extended import jwt_required

# Tools
import json                    # Estructura json

class ClaimsAPI:
    def __init__(self, controller):
        self.controller = controller
        self.db = self.controller.get_db()

        self.claims = Blueprint('claims', __name__)

        @self.claims.route("/claim/<int:id>", methods=['GET', 'PUT', 'DELETE'])
        @jwt_required()
        def claim_route(id):
            print('claim_route')
            if id:
                if request.method == 'GET':
                    claim, success = self.db.consultar_reclamacion(id)
                    return make_response(jsonify({"claim": claim, "ok":success}), 200 if success else 500)
                elif request.method == 'PUT':
                    message, success = self.db.revisar_reclamacion(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                elif request.method == 'DELETE':
                    message, success = self.db.eliminar_reclamacion(id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"error": "Método no permitido", "ok": False}), 405)
            return make_response(jsonify({"error": "No se ha especificado el id de la reclamación", "ok": False}), 400)

        @self.claims.route("/claims", defaults={'id': None}, methods=['GET', 'POST'])
        @self.claims.route("/claims/<int:id>")
        @jwt_required()
        def claims_route(id):
            print('claims_route')
            if request.method == 'GET':
                filter = request.args.get('filter', None)
                category = request.args.get('category', 'No revisado')
                limit = int(request.args.get('limit', 20))
                offset = int(request.args.get('offset', 0))

                if id:
                    total_claims, claims, success = self.db.consultar_reclamaciones_vendedor(id, filter, category, limit, offset)
                    return make_response(jsonify({"totalClaims": total_claims, "claims": claims, "ok": success}), 200 if success else 500)
                total_claims, claims, success = self.db.consultar_reclamaciones(category, filter, limit, offset)
                return make_response(jsonify({"totalClaims": total_claims, "claims": claims, "ok": success}), 200 if success else 500)
            elif request.method == 'POST':
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                message, success = self.db.registrar_reclamacion(json_data)
                return make_response(jsonify({"message": message, "ok": success }), 200 if success else 500)
            return make_response(jsonify({"error": "Método no permitido", "ok": False}), 405)