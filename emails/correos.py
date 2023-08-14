#Libreria, usando el protocolo SMTP (Simple Mail Transfer Protocol)
from email.mime.base import MIMEBase
import smtplib
from smtplib import SMTPAuthenticationError

# Conexion segura
import ssl

#Manejo de contraseñas: Separating sensitive data
from decouple import config
config.encoding = 'cp1251'

#Enviar mensajes en formato HTML
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#Estrucutras HTML
from emails.estructuras_html import EstructurasHTML

#Para archivos adjuntos
from email import encoders

class EmailSupport():
    def __init__(self):
        '''
        Configuración de correo.
        '''
        self.username='kmilokali@gmail.com'
        self.password='9498322fF' #config('MAIL_PASSWORD')

        self.message_verified = False

        self.addressee = None
        self.message = None
        self.context = None

        # En este dicc van las diferentes estructuras de HTML para envio de correos.
        self.directorios = {
            'update_password' : './backend/Correos/update_password.html'
        }

    def set_addressee(self, addressee):
        '''
        Setea la dirección de correo electrónico (REMITENTE)
        Args:
            addressee: STRING
        '''
        self.addressee = addressee

    def verify_requirements(self):
        '''
        Verifica que las variables vitales no sean NULL
        '''
        if self.username != None and self.password != None and self.addressee != None:
            return True
        return False
    
    def set_estructure_message(self, subject, category, name, apellido, code, linkJWT):
        '''
        Configura la estructura del mensaje dada la categoría
        Args:
            subject: STRING
            category: STRING
            name: STRING
            apellido: STRING
            code: INT
            linkJWT: STRING
        '''
        # Estrucutra del mensaje
        self.message = MIMEMultipart('alternative') # Estándar
        self.message['Subject'] = subject #Asunto
        self.message['From']= self.username    #Username
        self.message['To']= self.addressee     #destinatario

        if category == 'update_password':
            estructurasHTML = EstructurasHTML()
            self.html = estructurasHTML.get_estructura_html_update_password(name, apellido, code, linkJWT)
            self.parte_html = MIMEText(self.html, "html")

        if self.parte_html:
            self.message.attach(self.parte_html) #Añadir el html al mensaje
            self.message =  self.message.as_string()
            self.message_verified = True
            return True
        return False

    def send_simple_message(self):
        '''
        Enviamos un mensaje con la estructura HTML predefinida.
        '''
        if self.message_verified:
            self.context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host='smtp.gmail.com', port=465, context=self.context) as server:
                server.login(self.username, self.password)
                try:
                    server.sendmail(self.username, self.addressee, self.message) #or final_message
                    server.quit()
                    server.close()
                    return True
                except SMTPAuthenticationError as error:
                    print(error)
                    return False
        return False

    def send_message_with_file(self, file):
        '''
        Falta: Terminar
        Envió de mensajes cuando se completa un pedido.
        Adjuntar PDF
        '''
        if self.message_verified:
            with open(file, "rb") as adjunto:
                contenido_adjunto = MIMEBase("application", "octet-stream")
                contenido_adjunto.set_payload(adjunto.read())
                encoders.encode_base64(contenido_adjunto)

                contenido_adjunto.add_header(
                    "Content-Disposition",
                    f"attachment; filename={file}"
                )

                self.message.attach(contenido_adjunto) #Añadir documento adjunto al mensaje
                self.context = ssl.create_default_context()
                with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=self.context) as server:
                    server.login(self.username, self.password)
                    server.sendmail(self.username, self.addressee, self.message) #or final_message
                    return True
        return False


    