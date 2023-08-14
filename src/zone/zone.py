from flask import Blueprint, request, jsonify, make_response

# Auth
from flask_jwt_extended import jwt_required

# Tools
import json                     # Estructura json
import datetime                 # Manejo de fechas
from io import BytesIO

# Manejo de .xlsx
import pandas as pd                         # Manejo de DataFrames
from src.zone.Presupuesto import Presupuesto    # Manipular presupuestos
from decimal import Decimal

presupuesto = Presupuesto()

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class ZoneAPI:
    def __init__(self, controller) -> None:
        self.controller = controller
        self.db = self.controller.get_db()

        self.zone = Blueprint('zone', __name__)

        @self.zone.route('/zonas/vendedor/<string:id>', methods=['GET', 'POST', 'DELETE'])
        def zonas_vendedor(id):
            print('zonas_vendedor')
            if request.method == 'GET':
                if id:
                    zonas, success = self.db.consultar_zonas_vendedor(id)
                    return make_response(jsonify({"zones": zonas, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": "¡Algo salió mal!", "ok": False}), 405)
            elif request.method == 'POST':
                zone = request.args.get('zone', None)

                if zone and id:
                    message, success = self.db.asignar_zona_vendedor(zone, id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 400)
                return make_response(jsonify({"message": "¡Algo salió mal!", "ok": False}), 405)
            elif request.method == 'DELETE':
                zone = request.args.get('zone', None)

                if zone and id:
                    message, success = self.db.desasignar_zona_vendedor(zone, id)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 400)
                return make_response(jsonify({"message": "¡Algo salió mal!", "ok": False}), 405)
            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)

        @self.zone.route('/zonas/presupuesto/<string:id>', methods=['GET', 'POST'])
        def zonas_presupuesto(id):
            print('zonas_presupuesto')
            if request.method == 'GET':
                _presupuesto, success = self.db.consultar_presupuesto_zona(id)
                return make_response(jsonify({'presupuesto': _presupuesto, "ok": success}), 200 if success else 400)
            elif request.method == 'POST':
                excel_way = request.args.get('excelWay', None)

                if excel_way:
                    to_read = BytesIO()
                    to_read.write(request.data)
                    to_read.seek(0)

                    df = pd.read_excel(to_read, index_col=None)
                    presupuesto.set_presupuesto(df)
                    message, success = presupuesto.verify_presupuesto_excel()

                    result = []
                    _data = presupuesto.get_presupuesto()
                    for index, info in enumerate(_data):
                        result.append([])
                        for index_1, x_info in enumerate(info):
                            if type(x_info) == Decimal:
                                result[index].append(json.dumps(
                                    Decimal(x_info), cls=DecimalEncoder))
                            else:
                                result[index].append(info[index_1])
                    return make_response(jsonify({"message": message, "presupuestos": result, "ok": success}), 200 if success else 400)
            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)

        @self.zone.route('/departamentos', defaults={'id': None})
        @self.zone.route('/departamentos/<string:id>')
        @jwt_required()
        def get_departamento(id):
            print('get_departamento')
            if id:
                ciudades, success_ = self.db.consultar_ciudades(id)
                return make_response(jsonify({"cities": ciudades, "ok": success_}), 200 if success_ else 400)

            departamentos, success = self.db.consultar_departamentos()
            zones, success_ = self.db.consultar_zonas()

            cities = []

            for departamento in departamentos:
                info_departamento = json.loads(departamento[0])
                ciudades, success_ = self.db.consultar_ciudades(info_departamento['id'])
                cities.append(ciudades)
            return make_response(jsonify({'departments': departamentos, "zones": zones, "cities": cities, "ok": success}), 200 if success else 400)

        @self.zone.route('/zonas', defaults={'id': None}, methods=['GET', 'POST'])
        @self.zone.route('/zonas/<string:id>', methods=['GET', 'PUT', 'DELETE'])
        @jwt_required()
        def zonas(id):
            print('zonas')
            if request.method == 'GET':
                if not id:
                    context = request.args.get('context')
                    zonas, success = self.db.consultar_zonas(context)
                    return make_response(jsonify({"zones": zonas, "ok": success}), 200 if success else 400)
                else:
                    mes = int(request.args.get(
                        'month', datetime.datetime.now().month))

                    result, success = self.db.consultar_data_zona(id, mes)
                    if success:
                        [zona, departamentos, vendedor, presupuesto,
                            alcanzado, rendimiento] = result
                    return make_response(jsonify({
                        "zone": zona,
                        "departments": departamentos,
                        "seller": vendedor,
                        "budget": presupuesto,
                        "reached": alcanzado,
                        "rendimiento": rendimiento,
                        "ok": True}), 200 if True else 400)
            elif request.method == 'POST':
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                [message, zona], success = self.db.registrar_zona(json_data)
                return make_response(jsonify({"message": message, "zone": zona, "ok": success}), 200 if success else 400)
            elif request.method == "DELETE":
                message, success = self.db.eliminar_zona(id)
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 400)
            elif request.method == "PUT":
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                [message, zona], success = self.db.actualizar_zona(json_data)
                return make_response(jsonify({"message": message, "zone": zona, "ok": success}), 200 if success else 400)
            return make_response(jsonify({"message": "Método no permitido"}), 405)