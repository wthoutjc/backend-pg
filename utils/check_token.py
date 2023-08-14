from functools import wraps
import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token

def check_token(fn):
    @wraps(fn)
    @jwt_required(refresh=True)
    def wrapper(*args, **kwargs):
        token = get_jwt_identity()
        if 'exp' in token:
            expiration = datetime.datetime.fromtimestamp(token['exp'])
            if expiration < datetime.datetime.now():
                print('refresh_token')
                current_user = token['identity']

                new_token = create_access_token(identity=current_user, expires_delta=datetime.timedelta(minutes=0.5), fresh=True)
                new_refresh_token = create_refresh_token(identity=current_user, expires_delta=datetime.timedelta(days=30))

                expires_at = (datetime.datetime.utcnow() + datetime.timedelta(minutes=0.5)).timestamp()

                return {
                    'accessToken': new_token, 
                    'refreshToken': new_refresh_token,
                    'expiresAt': expires_at,
                    "ok": True
                    }
        return fn(*args, **kwargs)
    return wrapper