
<div align="center">
<h1 align="center">Open Streaming Platform</h1>
<h4>Docker Build</h4>
  <a href="https://github.com/github_username/repo_name">
    <img src="https://i.imgur.com/WBA40Yc.png" alt="Logo" width="128">
  </a>
</div>
<br>
<div align="center">
    Open-Source Video Streaming for Everyone
    <br />
    <a href="https://open-streaming-platform.readthedocs.io/en/latest/install/install.html#docker-install"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://demo.openstreamingplatform.com">View Demo</a>
    ·
    <a href="https://gitlab.com/osp-group/flask-nginx-rtmp-manager/-/issues/new">Report Bug</a>
    ·
    <a href="https://gitlab.com/osp-group/flask-nginx-rtmp-manager/-/issues/new">Request Feature</a>
</div>
<br>
<div align="center">
    <a href="https://gitlab.com/osp-group/flask-nginx-rtmp-manager/-/releases"><img src="https://img.shields.io/badge/dynamic/json?color=blue&label=release&query=%24%5B0%5D.tag_name&url=https%3A%2F%2Fgitlab.com%2Fapi%2Fv4%2Fprojects%2F5871108%2Freleases"></a>
    <a href="https://gitlab.com/osp-group/open-streaming-platform-docker"><img src="https://img.shields.io/docker/v/deamos/osp-core/latest?color=blue&label=docker%20version"></a>
    <a href="https://gitlab.com/osp-group/flask-nginx-rtmp-manager"><img src="https://img.shields.io/badge/dynamic/json?color=green&logo=gitlab&label=stars&query=%24.star_count&url=https%3A%2F%2Fgitlab.com%2Fapi%2Fv4%2Fprojects%2F5871108"></a>
    <a href="https://gitlab.com/osp-group/flask-nginx-rtmp-manager/-/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-orange"></a>
</div>

<div align="center">
    <a href="https://discord.gg/Jp5rzbD"><img src="https://img.shields.io/discord/543114856941879296"></a>
    <a href="https://opencollective.com/open-streaming-platform"><img src="https://img.shields.io/opencollective/all/open-streaming-platform"></a>
</div>

## Overview:

**Open Streaming Platform (OSP) is an open-source, RTMP streamer software front-end for [Arut's NGINX RTMP Module](https://github.com/arut/nginx-rtmp-module).**

OSP was designed a self-hosted alternative to services like Twitch.tv, Ustream.tv, and Youtube Live.

[![N|Solid](https://i.imgur.com/ptwGESB.jpg)](https://i.imgur.com/ptwGESB.jpg)

## Features:
 - RTMP Streaming from an input source like Open Broadcast Software (OBS).
 - Multiple Channels per User, allowing a single user to broadcast multiple streams at the same time without needing multiple accounts.
 - Video Stream Recording and On-Demand Playback. [![N|Solid](https://i.imgur.com/6Pd0Mtc.jpg)](https://i.imgur.com/6Pd0Mtc.jpg)
 - Per Channel Real-Time Chat for Video Streams. [![N|Solid](https://i.imgur.com/PlOtzhe.jpg)](https://i.imgur.com/PlOtzhe.jpg)
 - Manual Video Uploading of MP4s that are sourced outside of OSP
 - Video Clipping - Create Shorter Videos of Notable Moments
 - Real-Time Chat Moderation by Channel Owners (Banning/Unbanning)
 - Admin Controlled Adaptive Streaming
 - Protected Channels - Allow Access only to the audience you want.
 - Live Channels - Keep chatting and hang out when a stream isn't on
 - Webhooks - Connect OSP to other services via fully customizable HTTP requests which will pass information
 - Embed your stream or video directly into another web page easily
 - Share channels or videos via Facebook or Twitter quickly
 - Ability to Customize the UI as a Theme for your own personal look [![N|Solid](https://imgur.com/PldclhG.jpg)](https://imgur.com/PldclhG.jpg)
 - Modular Services - Scale your Instance of OSP to support a growing audience.

Installation Instructions may be found at the [OSP Wiki Page](https://open-streaming-platform.readthedocs.io/)

Docker
----
Docker Images can be found at the following locations:
- [OSP-Core (Core, Celery, Beat)](https://hub.docker.com/repository/docker/deamos/osp-core)
- [OSP-RTMP](https://hub.docker.com/repository/docker/deamos/osp-rtmp)
- [OSP-Ejabberd](https://hub.docker.com/repository/docker/deamos/osp-ejabberd)
- [Beta 6 and earlier](https://gitlab.com/Deamos/open-streaming-platform-docker)

Attribution
----
See our [Attribution Page](https://open-streaming-platform.readthedocs.io/en/latest/overview/attribution.html)

Thanks
----
Special thanks to the folks of the [OSP Discord channel](https://discord.gg/Jp5rzbD) and all contributors for their code, testing, and suggestions!

License
----
MIT License
