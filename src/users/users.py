from flask import Blueprint, request, jsonify, make_response

# Auth
from werkzeug.security import generate_password_hash
from flask_jwt_extended import jwt_required

# Tools
import json                     # Estructura json
import datetime                 # Manejo de fechas
from datetime import timedelta

# Email
from emails.verifyEmail import VerifyEmail

class UsersAPI:
    def __init__(self, controller) -> None:
        self.controller = controller
        self.db = self.controller.get_db()

        self.users = Blueprint('users', __name__)

        @self.users.route("/presupuestos-vendedor/<int:id>")
        @jwt_required()
        def presupuestos_vendedor(id):
            print('presupuestos_vendedor')
            if id:
                presupuestos_vendedor, success = self.db.consultar_presupuestos_vendedor(id)
                return make_response(jsonify({"presupuestosVendedor": presupuestos_vendedor, "ok": success}), 200 if success else 500)
            return make_response(jsonify({"message": 'No se ha ingresado el id', "ok": False}), 500)
        
        @self.users.route("/send-verification-email/<int:id>")
        @jwt_required()
        def send_verification_email(id):
            print('send_verification_email')
            if id:
                # Consultar email del usuario
                user, success = self.db.consultar_usuario(id)

                if success:
                    verify_email = VerifyEmail(user['email'])

                    if not verify_email.verify():
                        success = verify_email.send_verification_email(user['email'])
                        message = "Email enviado, por favor revise su bandeja de entrada o correo no deseado." if success else "Error al enviar el email"
                        return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
                    return make_response(jsonify({"message": "El email ya esta verificado", "ok": False}), 500)
                return make_response(jsonify({"message": user, "ok": False}), 500)
            return make_response(jsonify({"message": 'No se ha ingresado el id', "ok": False}), 500)

        @self.users.route("/verify-email/<int:id>")
        @jwt_required()
        def verify_email(id):
            print('verify_email')
            if id:
                # Consultar email del usuario
                user, success = self.db.consultar_usuario(id)

                if success:
                    verify_email = VerifyEmail(user['email'])
                    if verify_email.verify():
                        return make_response(jsonify({"message": 'Email verificado', "ok": True}), 200)
                    else:
                        return make_response(jsonify({"message": 'Email no verificado', "ok": False}), 200)
                return make_response(jsonify({"message": user, "ok": False}), 500)
            return make_response(jsonify({"message": 'No se ha ingresado el id', "ok": False}), 500)
            

        @self.users.route('/rendimiento-vendedores', defaults={'id': None})
        @self.users.route("/rendimiento-vendedores/<int:id>")
        @jwt_required()
        def rendimiento_vendedores(id):
            print('rendimiento_vendedores')
            
            mes = int(request.args.get(
                'mes', datetime.datetime.now().strftime('%m')))
            if id:
                if not mes:
                    return make_response(jsonify({"error": 'No se ha ingresado el mes', "ok": False}), 500)

                rendimiento, success = self.db.consultar_rendimiento_zonas(id, mes)

                if success:
                    return make_response(jsonify({"rendimientoZona": rendimiento, "ok": True}), 200)
                return make_response(jsonify({"error": rendimiento, "ok": False}), 500)

            # Consultar todos los vendedores
            [[result, total_vendedores], success] = self.db.consultar_vendedores(
                30, 0)  # Limit 30 offset 0

            rendimiento_vendedores = []
            if success:
                for vendedor in result:
                    rendimiento, success_ = self.db.consultar_rendimiento_zonas(
                        json.loads(vendedor[0])["id"], mes)
                    if success_:
                        rendimiento_vendedores.append(
                            {"vendedor": vendedor, "rendimiento": rendimiento})
                    else:
                        rendimiento_vendedores.append(
                            {"vendedor": vendedor, "rendimiento": []})
                return make_response(jsonify({"rendimientoVendedores": rendimiento_vendedores, "totalSellers": total_vendedores, "ok": True}), 200)
            return make_response(jsonify({"error": result, "ok": False}), 500)

        @self.users.route("/users", defaults={'id': None}, methods=['GET', 'POST'])
        @self.users.route("/users/<int:id>", methods=['GET', 'PUT', 'DELETE'])
        @jwt_required()
        def users_route(id):
            print('users_route')
            if request.method == 'GET':
                if not id:
                    category = request.args.get('category')
                    users, success = self.db.consultar_usuarios(category)
                    if success == True:
                        return make_response(jsonify({"total_users": users[0], "users": users[1], "ok": True}), 200)
                    else:
                        return make_response(jsonify({"error": users, "ok": False}), 400)
                else:
                    user, success = self.db.consultar_usuario(id)
                    if success:
                        if user['hierarchy'] == "Vendedor":
                            lps_seller, success_ = self.db.consultar_lp_seller(id)
                            if success_:
                                return make_response(jsonify({"user": user, "lps": lps_seller, "ok": True}), 200)
                            return make_response(jsonify({"user": user, "lps": lps_seller, "ok": True}), 200)
                        return make_response(jsonify({"user": user, "ok": True}), 200)
                    else:
                        return make_response(jsonify({"error": user, "ok": False}), 400)
            elif request.method == 'POST':
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                if json_data["password"] != json_data["confirmPassword"]:
                    return make_response(jsonify({"error": "Las contraseñas no coinciden", "ok": False}), 400)

                json_data_with_hash = {
                    "id": json_data['id'],
                    "name": json_data['name'],
                    "apellido": json_data['lastname'],
                    "correo": json_data['email'],
                    "categoria": json_data['hierarchy'],
                    "password": generate_password_hash(json_data['password']),
                }

                user, success = self.db.registrar_usuario(json_data_with_hash)
                if success:
                    return make_response(jsonify({"user": user, "ok": True}), 200)
                return make_response(jsonify({"error": user, "ok": False}), 400)
            elif request.method == 'PUT':
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                message, success = self.db.actualizar_usuario(json_data)
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)
            elif request.method == 'DELETE':
                user, exists = self.db.consultar_usuario(id)
                if exists and user['hierarchy'] == "Vendedor":
                    message, success = self.db.eliminar_vendedor(user['id'])
                    if success:
                        return make_response(jsonify({"message": message, "ok": True}), 200)
                    return make_response(jsonify({"message": message, "ok": False}), 500)
                message_, success_ = self.db.eliminar_usuario(user['id'])
                if success_:
                    return make_response(jsonify({"message": message_, "ok": True}), 200)
                return make_response(jsonify({"message": message_, "ok": False}), 500)
            return make_response(jsonify({"error": "Método no permitido", "ok": False}), 405)