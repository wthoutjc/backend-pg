from flask import Blueprint, request, jsonify, make_response, Response

# Auth
from flask_jwt_extended import jwt_required

class HelpCenterAPI:
    def __init__(self, controller, bucket):
        self.controller = controller
        self.db = self.controller.get_db()

        self.bucket = bucket

        self.help_center = Blueprint('help_center', __name__)

        @self.help_center.route("/help-center/verify-email")
        @jwt_required()
        def route_help_center_verify_email():
            return Response(
                self.bucket.get_object('video/help-center/Verificar correo.mp4'),
                mimetype='video/mp4',
                headers={
                    "Content-Disposition": "attachment; filename=Verificar correo.mp4"
                }
            )
        
        @self.help_center.route("/help-center/restore-password")
        @jwt_required()
        def route_help_center_restore_password():
            return Response(
                self.bucket.get_object('video/help-center/Cambiar contrasena.mp4'),
                mimetype='video/mp4',
                headers={
                    "Content-Disposition": "attachment; filename=Cambiar contrasena.mp4"
                }
            )

        @self.help_center.route("/help-center/register-lp")
        @jwt_required()
        def route_help_center_register_lp():
            return Response(
                self.bucket.get_object('video/help-center/Registrar lista de precios.mp4'),
                mimetype='video/mp4',
                headers={
                    "Content-Disposition": "attachment; filename=Registrar lista de precios.mp4"
                }
            )

        @self.help_center.route("/help-center/register-presupuesto")
        @jwt_required()
        def route_help_center_register_presupuesto():
            return Response(
                self.bucket.get_object('video/help-center/Registrar presupuesto.mp4'),
                mimetype='video/mp4',
                headers={
                    "Content-Disposition": "attachment; filename=Registrar presupuesto.mp4"
                }
            )

        @self.help_center.route("/help-center/register-pedido")
        @jwt_required()
        def route_help_center_register_pedido():
            return Response(
                self.bucket.get_object('video/help-center/Registrar pedido.mp4'),
                mimetype='video/mp4',
                headers={
                    "Content-Disposition": "attachment; filename=Registrar pedido.mp4"
                }
            )