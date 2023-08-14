import boto3

class VerifyEmail():
    def __init__(self, address):
        self.AWS_REGION = 'sa-east-1'
        self.ses = boto3.client('ses', region_name=self.AWS_REGION)
        self.response = self.ses.get_identity_notification_attributes(
            Identities=[
                address,
            ]
        )

    def verify(self):
        if self.response['NotificationAttributes']:
            return True
        return False
    
    def send_verification_email(self, address):
        try:
            self.ses.verify_email_address(
                EmailAddress = address
            )
            return True
        except:
            return False