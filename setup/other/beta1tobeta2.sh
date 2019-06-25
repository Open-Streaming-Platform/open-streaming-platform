pip3 install -r /opt/osp/setup/requirements.txt
sudo mkdir -p /opt/osp/vapid
sudo chown -R www-data:www-data /opt/osp/vapid
sudo chmod -R 774 /opt/osp/vapid
sudo openssl ecparam -name prime256v1 -genkey -noout -out /opt/osp/vapid/vapid_private.pem
sudo openssl ec -in /opt/osp/vapid/vapid_private.pem -pubout -out /opt/osp/vapid/vapid_public.pem
sudo openssl ec -in /opt/osp/vapid/vapid_private.pem -outform DER|tail -c +8|head -c 32|base64|tr -d '=' |td -d '\n' |tr '/+' '_-' >> /opt/osp/vapid/private_key.txt
sudo openssl ec -in /opt/osp/vapid/vapid_private.pem -pubout -outform DER|tail -c 65|base64|tr -d '=' | tr -d '\n' |tr '/+' '_-' >> /opt/osp/vapid/public_key.txt