from flask import Flask, request, Response
import requests
import xml.etree.ElementTree as et
import logging
import sys
import os
from urlparse import urlparse, parse_qs

sys.path.append(os.path.abspath('.'))

import kml2bmw

logging.basicConfig(filename='/var/log/kml2bmw/kml2bmw.log',level=logging.DEBUG)

app = Flask(__name__)

@app.route('/api/route')
def convert():
    try:
        link = request.args['link']
        logging.info("converting map: {}".format(link))

        parsed = parse_qs(urlparse(link).query)
        if 'mid' in parsed:
            map_id = parsed['mid'][0]
        else:
            map_id = parsed['id'][0]

        url = "https://www.google.com/maps/d/kml?mid={}&forcekml=1".format(map_id)

        logging.info("quering map: {}".format(url))

        response = requests.get(url)         

       	try:
        	xml = et.fromstring(response.content)
        	open('out.kml', 'w').write(response.content)
       	except Exception:
       		logging.exception('failed to load map: {}'.format(response.content))
       		return response.content

        parser = kml2bmw.Parser(xml, 10)
        parser.parse()
        parser.run()

       	r = Response(parser.write())
        r.headers['Content-Type'] = 'application/zip'
        r.headers['content-disposition'] = 'attachment; filename="unpack-to-usb.zip"'

        return r

    except Exception, e:
        logging.exception('failed to handle request')
        raise


if __name__ == '__main__':
    app.run(threaded=True, port=8090)
