#!/bin/bash

set -ex

pip install -r requirements.txt
mkdir -p /var/log/kml2bmw
ln -fs $(pwd)/conf/kml2bmw.service /etc/systemd/system/kml2bmw.service
rm -rf /opt/kml2bmw || true
cp -rf $(pwd) /opt/kml2bmw

systemctl daemon-reload
systemctl restart kml2bmw

apt install nginx
rm /etc/nginx/sites-enabled/default || true
ln -fs $(pwd)/conf/bmw /etc/nginx/sites-enabled/bmw

systemctl restart nginx 
