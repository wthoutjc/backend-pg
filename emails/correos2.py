#AWS Service to send simple messages
import boto3
from botocore.exceptions import ClientError

#Estrucutras HTML
from emails.estructuras_html import EstructurasHTML

class EmailSupport_AWS():
    def __init__(self):
        # Congif. Enviroment -> Constants
        self.AWS_REGION = 'sa-east-1'
        self.SENDER = 'kmilokali@gmail.com'
        self.CHARSET = 'UTF-8'
        self.body_text  =('COMPANY')

        #Message configuration -> variable
        self.recipient = None #To:
        self.body_html = None #Depends on category
        self.subject = None
        self.text_message = None

        #SES Service
        self.ses = boto3.client('ses', region_name=self.AWS_REGION)

        #Verify message
        self.verify_message = None

    def set_recipient(self, recipient):
        '''
        Set the address to send the message
        '''
        if not (isinstance(recipient, str)):
            self.recipient = None
        else:
            self.recipient = recipient

    def set_estructure_message(self, subject, category_message, name, apellido, code, linkJWT):
        #Verify structure
        self.verify_message = True
        if not isinstance(subject, str):
            self.verify_message = False
        if not self.recipient:
            self.verify_message = False
        elif category_message != 'update_password':
            self.verify_message = False
        
        if self.verify_message:
            self.subject = subject
            if category_message == 'update_password':
                estructurasHTML = EstructurasHTML()
                self.ses.update_template(
                    Template={
                        'TemplateName': 'update_password',
                        'SubjectPart': 'Company: Cambio Contraseña',
                        'TextPart': 'Company',
                        'HtmlPart': estructurasHTML.get_estructura_html_update_password(name, apellido, code, linkJWT)
                    }
                )
        else:
            print('Error setting message')

    def send_message(self):
        if self.verify_message:
            try:
                self.ses.get_template(TemplateName='update_password')
                self.ses.send_templated_email(
                    Source=self.SENDER,
                    Destination = {
                        'ToAddresses': [
                            self.recipient,   
                        ],
                    },
                    Template='update_password',
                    TemplateData = '{"replace tag name": "with value"}'
                )
                return True
            except ClientError as e:
                print(e.response['Error']['Message'])
                return False
        else:
            print('No cumple las condiciones para envio de Email')