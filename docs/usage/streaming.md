# Streaming

## Stream URL
In order to stream to OSP, a channel with a valid stream key is needed. After creating a channel, the streaming program must be set to the corresponding URL: ```rtmp://$IPorFQDN/stream``` 

## Stream Keys
You will find your stream key at the bottom of the Channel configuration page as follows:
![/_images/user_channels_page.png](/_images/user_channels_page.png)

Note that only registered users with the streamer role are able to stream to OSP.

## OSP Nginx-RTMP Default Configuration

OSP is configured by default with the following settings:

- **hls_framents**: 1 second
- **hls_playlist_length**: 10 seconds

Due to these settings, the key to creating low delay streams is to ensure your Keyframe Interval for your RTMP Source is set to 1 second.

Alterations to the the Nginx-RTMP configuration can be made by editing the osp-rtmp.conf file in /usr/local/nginx/conf. More information on the Nginx-RTMP directives can be found at https://github.com/arut/nginx-rtmp-module/wiki/Directives

## Latency

OSP uses HLS to serve RTMP streams to clients. This brings a certain latency by design. The default configuration of nginx is fine-tuned to reduce the latency as far as possible while providing stable HLS streams. For this configuration it is imporant that the encoder sends a keyframe every second! The latency should be 4.5 to 5 seconds.

If streams are buffering, it's most likely because of a suboptimal network connection. In this case, increase the ```hls_playlist_length``` in the ```osp-rtmp.conf```. The latency will increase with a longer playlist length. 

RTMP capable players (e.g. VLC) can access the RTMP stream directly. The URL is available in the share dialog below the stream. The latency of the RTMP stream should be 1 to 2 seconds. 

## Transcoding

Transcoding or adaptive streaming is possible with OSP. It can be enabled globally in the admin settings. However, this feature uses the CPU of the server to re-encode the streams and requires a lot of CPU power. It's possible to utilize GPUs instead by changing the encoder used by ffmpeg in the osp-rtmp.conf. Enabling transcoding will increase the stream latency. It may be necessary to increase the playlist length.

By default, nginx has been configured to transcode 1080p, 720p, 480p, & 360p. You can optimize how streams are transcoded by editing the osp-rtmp.conf file and following the instructions here.

## RTMP Streamer Software Configurations

Below is a listing of tested configurations for RTMP Source Configurations which produce the lowest delay (around 5s delay)

### Open Broadcaster Software

#### Medium Quality (720p) / Low Delay Setup
![/_images/obs_lowlatency.jpg](/_images/obs_lowlatency.jpg)

### ffMPEG

ffmpeg can be used to stream directly to OSP in various situations which can add additional flexibility that is not available using another client software:

#### Stream from a local camera without a UI

```
ffmpeg -re -f video4linux2 -i $VideoDeviceLocation -vcodec libx264 -vprofile baseline -acodec aac -strict -2 -f flv rtmp://$OSPIP/stream/$StreamKey
```

#### Stream from a video file

```
ffmpeg -re -i "$file" -acodec copy -vcodec copy -f flv rtmp://$OSPIP/stream/$key
```

#### Restream from another RTMP Stream

```
ffmpeg -i $sourceStream -vcodec libx264 -vprofile baseline -acodec aac -strict -2 -f flv rtmp://$OSPIP/stream/$StreamKey
```

#### Testing OSP server

We can use ffmpg to test the streaming ability of an OSP server. Log into OSP with an account that has permission to stream, go to a channel (creating one if necessary), and get the stream key as described above.

Next we need some media to play. We suggest [Big Buck Bunny](http://bbb3d.renderfarming.net/download.html) as a wonderful test file.

In a terminal, set environment variables for your filename, server, and key. Then ffmpeg can be used to stream your video to the OSP server. The RTMP format can not handle a sample rate of 48000, so we will use options in ffmpeg to downconvert it to 44100). For example:

```
file=bbb_sunflower_1080p_30fps_normal.mp4
fqdn=<OSP-RTMP FQDN/IP>
key=REDACTED

ffmpeg -re -i "$file" -acodec libmp3lame -ar 44100 -vcodec copy -f flv rtmp://$fqdn/stream/$key
```

This should start streaming the video to the server. In order to verify everything is working as expected, use your browser to tune into the channel.