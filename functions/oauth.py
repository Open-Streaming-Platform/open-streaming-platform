import requests
import uuid

from classes.Sec import OAuth2Token
from classes.shared import db
from flask_security import current_user

from classes import Sec
from globals.globalvars import videoRoot


def fetch_token(name: str):
    model = OAuth2Token

    token = model.find(
        name=name,
        user=current_user,
    )
    return token.to_token()


def discord_processLogin(userDataDict: dict, UserObj: Sec.User) -> bool:
    # Handle Discord Avatar Download
    avatarHash = userDataDict["avatar"]
    userID = userDataDict["id"]

    image_url = (
        "https://cdn.discordapp.com/avatars/"
        + str(userID)
        + "/"
        + str(avatarHash)
        + ".png?size=512"
    )
    img_data = requests.get(image_url).content
    fileName = str(uuid.uuid4()) + ".png"
    with open(videoRoot + "images/" + fileName, "wb") as handler:
        handler.write(img_data)

    UserObj.pictureLocation = fileName
    db.session.commit()
    return True


def reddit_processLogin(userDataDict: dict, UserObj: Sec.User) -> bool:
    # Handle Reddit Avatar Download
    image_url = userDataDict["icon_img"]
    img_data = requests.get(image_url).content
    fileName = str(uuid.uuid4()) + ".png"
    with open(videoRoot + "images/" + fileName, "wb") as handler:
        handler.write(img_data)

    UserObj.pictureLocation = fileName
    db.session.commit()
    return True


def facebook_processLogin(apiLocation: str, userDataDict: dict, UserObj: Sec.User) -> bool:
    image_url = (
        apiLocation
        + str(userDataDict["id"])
        + "/picture?redirect=0&height=64&width=64&type=normal"
    )
    img_data = requests.get(image_url).content
    fileName = str(uuid.uuid4()) + ".png"
    with open(videoRoot + "images/" + fileName, "wb") as handler:
        handler.write(img_data)

    UserObj.pictureLocation = fileName
    db.session.commit()
    return True
