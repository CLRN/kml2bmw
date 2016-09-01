#!/usr/bin/env python

import web
import kml2bmw
import requests
import xml.etree.ElementTree as et
import logging
from urlparse import urlparse, parse_qs

logging.basicConfig(filename='kml2bmw.log',level=logging.DEBUG)

urls = ("/.*", "hello")
app = web.application(urls, globals())

class hello:
    def GET(self):
        try:
            link = web.input().link
            logging.info("converting map: {}".format(link))

            parsed = parse_qs(urlparse(link).query)
            if 'mid' in parsed:
                map_id = parsed['mid'][0]
            else:
                map_id = parsed['id'][0]

            url = "https://www.google.com/maps/d/kml?mid={}&forcekml=1".format(map_id)

            logging.info("quering map: {}".format(url))

            response = requests.get(url)         
            xml = et.fromstring(response.content)

            parser = kml2bmw.Parser(xml, 10)
            parser.parse()
            parser.run()

            web.header('Content-Type', 'application/zip')

            return parser.write()

        except Exception, e:
            logging.exception('failed to handle request')
            raise

if __name__ == "__main__":
    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
    app.run()

