import os 
from decouple import config

from flask import Flask, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# JSON Web Tokens
from flask_jwt_extended import JWTManager

# Componentes
from emails.correos import EmailSupport
from emails.correos2 import EmailSupport_AWS

# Routes
from src.agenda.agenda import AgendaAPI
from src.auth.auth import AuthAPI
from src.bodegas.bodegas import BodegaAPI
from src.clients.clients import ClientsAPI
from src.listas_precios.listas_precios import ListasPreciosAPI
from src.pedidos.pedidos import PedidosAPI
from src.summaries.summaries import SummariesAPI
from src.users.users import UsersAPI
from src.zone.zone import ZoneAPI
from src.help_center.help_center import HelpCenterAPI
from src.claims.claims import ClaimsAPI

# Db
from db.db import  Database
from mysql.connector.errors import Error

# Controller
from controller.Controller import Controller

# Bucket S3
from s3.Bucket import BucketCompany

time_zone = config('TZ')
os.environ['TZ'] = time_zone
#  time.tzset() only for linux

# Operaciones SQL
mail_op = EmailSupport()
mail_op_aws = EmailSupport_AWS()

application = Flask(__name__)
app = application

SECRET_KEY = config('SECRET_KEY')
CORS(app)

app.config['SECRET_KEY'] = SECRET_KEY
app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']

# Config del entorno
jwt = JWTManager(app)

controller = Controller()
db = Database(app)

db.set_controller(controller)

controller.set_db(db)

BUCKET_COMPANY = BucketCompany()

app.register_blueprint(AgendaAPI(controller).agenda)
app.register_blueprint(AuthAPI(controller).auth)
app.register_blueprint(BodegaAPI(controller).bodegas)
app.register_blueprint(ClientsAPI(controller).clients)
app.register_blueprint(ListasPreciosAPI(controller).listas_precios)
app.register_blueprint(PedidosAPI(controller).pedidos)
app.register_blueprint(SummariesAPI(controller).summaries)
app.register_blueprint(UsersAPI(controller).users)
app.register_blueprint(ZoneAPI(controller).zone)
app.register_blueprint(HelpCenterAPI(controller, BUCKET_COMPANY).help_center)
app.register_blueprint(ClaimsAPI(controller).claims)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    try:
        token, success = db.consultar_token_blocklist(jti)
        if success == True:
            return token is not None
    except Error as error:
        print('Check token revoked Error: ' + str(error))
        return False

# Ruta raiz
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)