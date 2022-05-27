# Webhooks
OSP can send HTTP requests (GET,POST,PUT,DELETE) to notify other services about various triggers. Webhooks can be set globally in the admin settings and per channel by users. The HTTP requests are entirely definable by the by JSON.
Currently supported triggers:
- At the Start of a Live Stream
- At the End of a Live Stream
- On a New Viewer Joining a Live Stream
- On a Stream Upvote
- On a Stream Metadata Change (Name/Topic)
- On a Stream Chat Message
- On Posting of a New Video to a Channel
- On a New Video Comment
- On a Video Upvote
- On a Video Metadata Change (Name/Topic)
## Webhook Variables
When defining a webhook payload, various variables can be set which will be replaced with live data at the time the webhook is run. Webhook variables are defined as the following:
- ```%channelname%```
- ```%channelurl%```
- ```%channeltopic%```
- ```%channelimage%```
- ```%streamer%```
- ```%channeldescription%```
- ```%streamname%```
- ```%streamurl%```
- ```%streamtopic%```
- ```%streamimage%```
- ```%user%```
- ```%userpicture%```
- ```%videoname%```
- ```%videodate%```
- ```%videodescription%```
- ```%videotopic%```
- ```%videourl%```
- ```%videothumbnail%```
- ```%comment%```
## Examples
### Discord
**Type:** POST

**Trigger event:** Stream start
#### Header
```json
{"Content-Type": "application/json"}
```
#### Payload
```json
{
"content": "%channelname% went live on the OSP Demo Server",
"username": "OSP Bot",
"embeds": [
{
"title": "%streamurl%",
"url": "%streamurl%",
"color": 6570404,
"image": {
"url": "%channelimage%"
},
"author": {
"name": "%streamer% is now streaming"
},
"fields": [
{
"name": "Channel",
"value": "%channelname%",
"inline": true
},
{
"name": "Topic",
"value": "%streamtopic%",
"inline": true
},
{
"name": "Stream Name",
"value": "%streamname%",
"inline": true
},
{
"name": "Description",
"value": "%channeldescription%",
"inline": true
}
]
}
]
}
```
### Mastadon

**Type:** POST

**Trigger event:** Stream start
#### URL
```
https://$FQDN/api/v1/statuses?access_token=$TOKEN
```
#### Header
```json
{"Content-Type": "application/json"}
```
#### Payload
```json
{
"status": "New Live Stream on OSP.\n\nURL: %streamurl%\nChannel: %channelname%\nTopic: %streamtopic%\nDescription: %channeldescription%"
}
```