from flask import abort, current_app
from flask_socketio import emit
from flask_security import current_user

from classes.shared import db, socketio
from classes import Channel

from functions import cachedDbCalls


@socketio.on("newRestream")
def newRestream(message):
    restreamChannel = message["restreamChannelID"]
    channelQuery = cachedDbCalls.getChannel(int(restreamChannel))
    if channelQuery is not None:
        if channelQuery.owningUser == current_user.id:
            restreamName = message["name"]
            restreamURL = message["restreamURL"]
            newRestreamObject = Channel.restreamDestinations(
                channelQuery.id, restreamName, restreamURL
            )

            db.session.add(newRestreamObject)
            db.session.commit()

            restreamQuery = Channel.restreamDestinations.query.filter_by(
                name=restreamName,
                url=restreamURL,
                channel=int(restreamChannel),
                enabled=False,
            ).with_entities(Channel.restreamDestinations.id).first()
            restreamID = restreamQuery.id

            emit(
                "newRestreamAck",
                {
                    "restreamName": restreamName,
                    "restreamURL": restreamURL,
                    "restreamID": str(restreamID),
                    "channelID": str(restreamChannel),
                },
                broadcast=False,
            )
        else:
            db.session.commit()
            db.session.close()
            return abort(401)
    else:
        db.session.commit()
        db.session.close()
        return abort(500)
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("toggleRestream")
def toggleRestream(message):
    restreamID = message["id"]
    restreamQuery = (
        Channel.restreamDestinations.query
        .filter_by(id=int(restreamID))
        .with_entities(
            Channel.restreamDestinations.id,
            Channel.restreamDestinations.channel,
            Channel.restreamDestinations.enabled
            )
        .first()
    )
    if restreamQuery is not None:
        channelQuery = cachedDbCalls.getChannel(restreamQuery.channel)
        if channelQuery is not None:
            if channelQuery.owningUser == current_user.id:
                restreamUpdate = Channel.restreamDestinations.query.filter_by(id=int(restreamID)).update(dict(enabled=not restreamQuery.enabled))
                db.session.commit()
            else:
                db.session.commit()
                db.session.close()
                return abort(401)
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(500)
    db.session.commit()
    db.session.close()
    return "OK"


@socketio.on("deleteRestream")
def deleteRestream(message):
    restreamID = message["id"]
    restreamQuery = (
        Channel.restreamDestinations.query
        .filter_by(id=int(restreamID))
        .with_entities(
            Channel.restreamDestinations.id,
            Channel.restreamDestinations.channel,
            Channel.restreamDestinations.enabled
            )
        .first()
    )
    if restreamQuery is not None:
        channelQuery = cachedDbCalls.getChannel(restreamQuery.channel)
        if channelQuery is not None:
            if channelQuery.owningUser == current_user.id:
                restreamUpdate = Channel.restreamDestinations.query.filter_by(id=int(restreamID)).delete()
                db.session.commit()
            else:
                db.session.commit()
                db.session.close()
                return abort(401)
        else:
            db.session.commit()
            db.session.close()
            return abort(500)
    else:
        db.session.commit()
        db.session.close()
        return abort(500)
    db.session.commit()
    db.session.close()
    return "OK"
