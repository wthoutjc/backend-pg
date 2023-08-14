from flask import Blueprint, request, jsonify, make_response, Response

# Auth
from flask_jwt_extended import jwt_required

# Tools
import json                     # Estructura json
from decimal import Decimal
from io import BytesIO

# Manejo de .xlsx
import pandas as pd                 # Manejo de DataFrames
from src.listas_precios.LP import LP     # Manipular listas de precios

# Bucket S3
from s3.Bucket import BucketCompany

# Listas de precios
lp = LP()
bucket = BucketCompany()

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class ListasPreciosAPI:
    def __init__(self, controller):
        self.controller = controller
        self.db = self.controller.get_db()

        self.listas_precios = Blueprint('listas_precios', __name__)

        @self.listas_precios.route("/listas-precios/upload", defaults={'id': None})
        @self.listas_precios.route("/listas-precios/upload/<int:id>", methods=["POST", "DELETE"])
        @jwt_required()
        def route_upload_lp(id):
            if request.method == "GET":
                link = request.args.get('link', None)
                if link:
                    return Response(
                    bucket.get_object(link),
                    mimetype='application/pdf',
                    headers={
                        "Content-Disposition": "attachment; filename=" + link.split('/')[1]
                    }
                )
                return make_response(jsonify({"message": "No se especificó el link", "ok": False}), 500)
            elif request.method == "POST":
                if request.files and id:
                    category = request.args.get('category', None)

                    if category:
                        file = request.files['file']
                        link, success = bucket.upload_file(file, 'listas_precios/' + file.filename)        
                        if success:
                            message, success = self.db.registrar_link_lp(category, id, link)
                            return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                        return make_response(jsonify({"message": link, "ok": success}), 200 if success else 500)
                    return make_response(jsonify({"message": "No se especificó la categoría", "ok": False}), 500)
                return make_response(jsonify({"message": "No se especificó el archivo", "ok": False}), 500)
            elif request.method == "DELETE":
                category = request.args.get('category', None)
                if category and id:
                    lp, exists = self.db.consultar_lista_precio(id, category)
                    file_name = json.loads(lp[0][0])['link']
                    message_, success_ = bucket.delete_file(file_name)
                    if success_:
                        message, success = self.db.eliminar_link_lp(category, id)
                        return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                    return make_response(jsonify({"message": message_, "ok": success_}), 200 if success_ else 500)
                return make_response(jsonify({"message": "No se especificó la categoría ó id.", "ok": False}), 500)
            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)

        @self.listas_precios.route("/listas-precios/bodegas", defaults={'id': None})
        @self.listas_precios.route("/listas-precios/bodegas/<int:id>")
        @jwt_required()
        def route_listas_precios_bodegas1(id):
            print('route_listas_precios_bodegas1')
            if id:
                products, success = self.db.consultar_productos_lp_bodegas(id)
                return make_response(jsonify({"products": products, "ok": success}), 200 if success else 500)
            lp_bodegas, success = self.db.consultar_listas_precios_bodegas()
            return make_response(jsonify({"lps": lp_bodegas, "ok": success}), 200 if success else 500)

        @self.listas_precios.route('/listas-precios', defaults={'id': None}, methods=["POST", "GET"])
        @self.listas_precios.route("/listas-precios/<int:id>", methods=['GET', 'POST', 'PUT', 'DELETE'])
        @jwt_required()
        def route_listas_precios(id):
            print('route_listas_precios')
            if request.method == 'GET':
                if not id:
                    category = request.args.get('category', 'Pedidos')
                    listas_precios, success = self.db.consultar_listas_precios(category)
                    if success == True:
                        return make_response(jsonify({"listasPrecios": listas_precios, "ok": True}), 200)
                    return make_response(jsonify({"message": listas_precios, "ok": False}), 404)
                category = request.args.get('category', 'Pedidos')

                [lprecios, productos, vendedor], success = self.db.consultar_lista_precio(
                    id, category)
                return make_response(jsonify({"lp": lprecios, "productos": productos, "vendedor": vendedor, "ok": success}), 200 if success else 404)
            if request.method == "POST":
                # Asignar lista de precios
                assign = request.args.get('assign', None)
                unassign = request.args.get('unassign', None)
                excel_way = request.args.get('excelWay', None)

                if assign:
                    category = request.args.get('category', 'Pedidos')

                    assign = int(assign)
                    data_raw = request.data.decode("utf-8")
                    json_data = json.loads(data_raw)

                    id_user = json_data["idUser"]
                    id_lista = json_data["idLP"]

                    message, success = self.db.asignar_lp(id_user, id_lista, category)
                    if success:
                        return make_response(jsonify({"message": message, "ok": True}), 200)
                    return make_response(jsonify({"error": message, "ok": False}), 500)
                elif unassign:
                    category = request.args.get('category', 'Pedidos')

                    data_raw = request.data.decode("utf-8")
                    json_data = json.loads(data_raw)

                    id_seller = json_data["idSeller"]
                    id_lista = json_data["idLP"]

                    message, success = self.db.desasignar_lp(id_seller, id_lista, category)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                elif excel_way:
                    category = request.args.get('category', 'Pedidos')

                    to_read = BytesIO()
                    to_read.write(request.data)
                    to_read.seek(0)

                    df = pd.read_excel(to_read, index_col=None)
                    lp.set_lp(df)
                    lp.set_context(category)

                    message, success = lp.verify_lp_excel()
                    if success:
                        result = []
                        _data = lp.get_lp()
                        for index, info in enumerate(_data):
                            result.append([])
                            for index_1, x_info in enumerate(info):
                                if type(x_info) == Decimal:
                                    result[index].append(json.dumps(
                                        Decimal(x_info), cls=DecimalEncoder))
                                else:
                                    result[index].append(info[index_1])
                        return make_response(jsonify({"message": message, "ok": success, "lp": result}), 200)
                    return make_response(jsonify({"message": message, "ok": success}), 500)
                # Registrar una nueva lista de precios
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                category = request.args.get('category', 'Pedidos')

                if json_data and category:
                    if category == 'Pedidos':
                        lp.set_lp(pd.DataFrame(json_data['lp'], columns=[
                                "nombre", "precio", "kg"]))
                        lp.set_context(category)
                    else:
                        lp.set_lp(pd.DataFrame(
                            json_data['lp'], columns=["nombre", "kg"]))
                        lp.set_context(category)
                    message, verify = lp.verify_lp_excel()
                    if verify:
                        _message, success = self.db.registrar_lista_precios(
                            json_data['lp'], json_data['name'], json_data['marca'], category)
                        return make_response(jsonify({"message": _message, "ok": success}), 200 if success else 500)
                    return make_response(jsonify({"message": message, "ok": verify}), 500)
                return make_response(jsonify({"message": "No hay ninguna lista de precios cargada", "ok": False}), 500)
            if request.method == "DELETE":
                category = request.args.get('category', 'Pedidos')

                message, success = self.db.eliminar_lista_precios(id, category)
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
            if request.method == "PUT":
                category = request.args.get('category', 'Pedidos')

                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                lista_precios = json_data['lp']
                productos = json_data['products']

                if category == 'Bodegas':
                    lp.set_lp(pd.DataFrame(productos, columns=["nombre", "kg"]))
                    lp.set_context('Bodegas')
                else:
                    lp.set_lp(pd.DataFrame(productos, columns=[
                            "nombre", "precio", "kg"]))
                    lp.set_context('Pedidos')
                message_, verify = lp.verify_lp_excel()
                if verify:

                    message, success = self.db.actualizar_lista_precios(
                        lista_precios, productos, category)
                    return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                return make_response(jsonify({"message": message_, "ok": verify}), 500)
            return make_response(jsonify({"message": "Método no permitido", "ok": False}), 405)