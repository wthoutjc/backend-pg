import boto3

# Env
from decouple import config

class BucketCompany():
    def __init__(self):
        self.s3 = boto3.resource('s3')
        self.client_s3 = boto3.client('s3')
        self.bucket_name = config('BUCKET_COMPANY')

    def get_object(self, key):
        obj = self.s3.Object(self.bucket_name, key)
        return obj.get()['Body']
    
    def upload_file(self, file, key):
        try:
            self.client_s3.upload_fileobj(file, self.bucket_name, key)
            return [f'{key}', True]
        except Exception as e:
            print(e)
            return [f'upload_file Error: {e}' ,False]
    
    def delete_file(self, file_name):
        try:
            self.client_s3.delete_object(Bucket=self.bucket_name, Key=file_name)
            return [f'{file_name} eliminado', True]
        except Exception as e:
            print(e)
            return [f'delete_file Error: {e}' ,False]