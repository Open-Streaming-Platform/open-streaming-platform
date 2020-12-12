Requires OSP Beta 5

The OSP Edge Streamer Acts as a load balancer for OSP, allowing Live Stream viewers to be offloaded from the primary OSP Node to a cluster of Nginx-RTMP servers configured to receive RTMP restreams from the master.

As many OSP Edge Streamer Nodes are needed can be created and added to OSP by an admin under the Admin -> Edge Streamers Configuration options.

To setup the OSP Edge Streamer:
* Run the setup-ospEdge.sh Script and enter the IP Address of the primary OSP Server

```
sudo bash setup-ospEdge.sh
```

* Once the server has finished setting up, Go to OSP and add the Fully qualified domain name to the Edge Streamer section in the Admin Settings.
* After adding your settings, you will need to reload Nginx-RTMP on the primary OSP Server
```
sudo systemctl reload nginx-osp
```

For more detailed and up-to-date information, see https://wiki.openstreamingplatform.com/OSPEdge/Overview