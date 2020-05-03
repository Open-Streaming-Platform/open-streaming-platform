from classes.Sec import OAuth2Token
from flask_security import current_user

def fetch_token(name):
    model = OAuth2Token

    token = model.find(
        name=name,
        user=current_user,
    )
    return token.to_token()