# Swagger API

## Overview
![API Screenshot](/_images/api_example.png)
The API can be accessed at: ```http(s)://<fqdn>/apiv1```. 

For authenticated endpoints, an API key is needed, which can be created by users with the streamer role in the user menu to the top right. Requests to authenticated endpoints must have the 'X-API-KEY': header field set with a valid API key.

## Example

In this example a chat message is sent to a chat channel endpoint.

Username: botnameMessage: beep bobEndpoint: channels/chat/72223bf3-be79-4a2a-88d9-c7bdce271f0eAPI key: d26de1eb2d48a784e109b29025632fc1a0211a2ffbede09672c8cf6f4321fb0000c49cb243e2d07e
```
curl -X POST "http://localhost/apiv1/channels/chat/72223bf3-be79-4a2a-88d9-c7bdce271f0e?username=botname&message=beep%20bop" \    -H  "accept: application/json" -H  "X-API-KEY: d26de1eb2d48a784e109b29025632fc1a0211a2ffbede09672c8cf6f4321fb0000c49cb243e2d07e"
```