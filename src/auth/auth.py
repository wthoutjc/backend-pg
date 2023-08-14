from flask import Blueprint, request, jsonify, make_response

# Auth
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, create_refresh_token, get_jwt_identity

# Tools
import json                     # Estructura json
import datetime                 # Manejo de fechas
from uuid import uuid4          # Asignación de códigos para update_password

# DB
from mysql.connector.errors import Error

# Emails
from emails.correos2 import EmailSupport_AWS

mail = EmailSupport_AWS()

class AuthAPI:
    def __init__(self, controller):
        self.controller = controller
        self.db = self.controller.get_db()
        
        self.auth = Blueprint('auth', __name__)

        @self.auth.route("/is-auth")
        @jwt_required()
        def is_auth():
            print('is_auth')
            return make_response(jsonify({"ok": True}), 200)

        @self.auth.route("/refresh-token", methods=["POST"])
        @jwt_required(refresh=True)
        def refresh_token():
            print('refresh_token')
            current_user = get_jwt_identity()

            new_token = create_access_token(identity=current_user, expires_delta=datetime.timedelta(hours=10), fresh=True)
            new_refresh_token = create_refresh_token(identity=current_user, expires_delta=datetime.timedelta(days=30))

            expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=10)).timestamp()
            current_user['expires'] = expires_at

            return make_response(jsonify({
                'accessToken': new_token, 
                'refreshToken': new_refresh_token,
                'expiresAt': expires_at,
                'user': current_user,
                "ok": True
                }, 200))

        @self.auth.route("/reset-password", methods=["POST"])
        def reset_password():
            print('reset_password')
            if request.data:
                data_raw = request.data.decode("utf-8")
                request_data = json.loads(data_raw)

                id_usuario = request_data['id']
                password = request_data['password']

                password_hash = generate_password_hash(password)

                message, success = self.db.actualizar_contraseña(id_usuario, password_hash)
                return make_response(jsonify({"message": message, "ok": success}), 200 if success else 500)

            return make_response(jsonify({"message": 'Falló el procesamiento de la solicitud', "ok": False}), 500)

        @self.auth.route("/confirm-code", methods=["POST"])
        def confirm_code():
            print('confirm_code')
            res_verify = 'No autorizado'

            if request.data:
                data_raw = request.data.decode("utf-8")
                request_data = json.loads(data_raw)

                request_id = request_data['id']
                request_code = request_data['code']

                db_info, success = self.db.consultar_solicitud_contraseña(request_id)

                #db_info[0]: Cedula del solicitante
                #db_info[1]: Token 
                #db_info[2]: Codigo

                if success:
                    if db_info[1] == request_code:
                        res_verify = 'Autorizado'
                        return make_response(jsonify({"message": res_verify, "ok": True}), 200)
                    return make_response(jsonify({"message": res_verify, "ok": False}), 500)
            return make_response(jsonify({"message": 'Falló el procesamiento de la solicitud', "ok": False}), 500)

        @self.auth.route("/forgot-password/<id>", methods=["POST"])
        def forgot_password(id):
            print('forgot-forgot_password')
            user, success = self.db.consultar_usuario(id)
            if success: 
                payload = {
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
                    'iat': datetime.datetime.utcnow(),
                    'sub': user['id'],
                    'auth': True
                }
                CODE = str(uuid4())
                access_token = create_access_token(identity=payload, expires_delta=datetime.timedelta(minutes=30))
                success_info = self.db.registrar_solicitud_cambio_password(user['id'], CODE, datetime.datetime.now() + datetime.timedelta(minutes=30))

                if success_info[1]:
                    # Ejecutamos todo el proceso de envio de correo
                    #   1. Setear el destino del correo
                    '''mail_op.set_addressee(data_user[0][3])'''
                    mail.set_recipient(user['email'])
                    URL = f'https://localhost:3000/auth/update-password?key={access_token}'
                    #   2. Creamos la primera estructura del mensaje: ASUNTO - CATEGORIA - NOMBRE - APELLIDO - LINK CON JWT
                    #       La categoria para forgotPassword -> update_password
                    '''mail_op.set_estructure_message('Company: Cambio Contraseña', 'update_password', data_user[0][1], data_user[0][2], CODE, URL)'''
                    mail.set_estructure_message('Company: Cambio Contraseña', 'update_password', user['name'], user['lastname'], CODE, URL)
                    #   3. Enviamos el mail
                    '''email_operation = mail_op.send_simple_message()'''
                    email_operation = mail.send_message()
                    if email_operation:
                        return make_response(jsonify({"message": 'Email enviado', "ok": True}), 200)
                else:
                    return make_response(jsonify({"message": 'Ya se esta procesando una solicitud para esa cédula. Intente más tarde', "ok": False}), 500)
            return make_response(jsonify({"message": 'Usuario no registrado', "ok": False}), 500)

        @self.auth.route("/revoke-token", methods=["DELETE"])
        @jwt_required()
        def modify_token():
            print('modify_token')
            jti = get_jwt()["jti"]
            print('revoke-token JTI: ' + str(jti))
            try:
                message, success = self.db.insertar_token_blocklist(
                    jti, datetime.datetime.now(datetime.timezone.utc))
                if success:
                    return make_response(jsonify({"results": "JWT revoked", "ok": True}), 200)
                return make_response(jsonify({"error": message, "ok": False}), 500)
            except Error as error:
                print('Revoke Token Error:' + str(error))
                return make_response(jsonify({"error": 'SQL Operation Failed', "ok": False}), 500)

        @self.auth.route("/log-in", methods=["POST"])
        def log_in():
            print('log_in')
            # Borrar tokens vencidos de la lista block tokens en la DB
            message, success = self.db.clean_block_tokens()
            if request.data and success:
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                username = json_data['username'] if 'username' in json_data else None
                password = json_data['password'] if 'password' in json_data else None

                if username and password:
                    user, success = self.db.consultar_usuario(username)
                    password_, success = self.db.consultar_password(user['id'])

                    if success and check_password_hash(password_, password):
                        accessToken = create_access_token(identity=user, expires_delta=datetime.timedelta(hours=10), fresh=True)
                        refreshToken = create_refresh_token(identity=user, expires_delta=datetime.timedelta(days=30))

                        accessTokenExpires = (datetime.datetime.utcnow() + datetime.timedelta(hours=10)).timestamp()

                        user['expires'] = accessTokenExpires

                        return make_response(jsonify({
                            "accessToken": accessToken, 
                            "refreshToken": refreshToken, 
                            "accessTokenExpires": accessTokenExpires,
                            "user": user,
                        }), 200)

                    return make_response(jsonify({"error": 'Usuario o contraseña incorrectas'}), 404)
                return make_response(jsonify({"error": 'Usuario/Contraseña no ingresado.'}), 404)
            return make_response(jsonify({"error": 'Falló el procesamiento de la solicitud.'}), 405)