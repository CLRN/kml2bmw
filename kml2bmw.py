#!/usr/bin/env python

import argparse
import os
import xml.etree.ElementTree as et
import tarfile
import zipfile
import datetime
import xml.dom.minidom as minidom
import sys
import codecs
import math
import StringIO

class InMemoryZip(object):
    def __init__(self):
        # Create the in-memory file-like object
        self.in_memory_zip = StringIO.StringIO()

    def append(self, filename_in_zip, file_contents):
        '''Appends a file with name filename_in_zip and contents of
        file_contents to the in-memory zip.'''
        # Get a handle to the in-memory zip in append mode
        zf = zipfile.ZipFile(self.in_memory_zip, "a", zipfile.ZIP_DEFLATED, False)

        # Write the file to the in-memory zip
        zf.writestr(filename_in_zip, file_contents)

        # Mark the files as having been created on Windows so that
        # Unix permissions are not inferred as 0000
        for zfile in zf.filelist:
            zfile.create_system = 0

        return self

    def read(self):
        '''Returns a string with the contents of the in-memory zip.'''
        self.in_memory_zip.seek(0)
        return self.in_memory_zip.read()

class Place:
    def __init__(self, name, pos):
        self.name = name
        self.pos = pos
        self.closest_point = -1
        self.closest_distance = -1
        self.wp_count = 0
        self.waypoints = []

    def __str__(self):
        return '{} at {}, point: {}, count: {}'.format(self.name, self.pos, self.closest_point, self.wp_count)

    def __repr__(self):
        return str(self)

class Route:
    def __init__(self, xml, max_wp, name, index):
        self.places = []
        self.points = []
        self.output = et.Element('DeliveryPackage')
        self.max_wp = max_wp
        self.name = name
        self.route_id = index

        self.parse(xml)

    def parse(self, xml):

        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        # parse places

        xmlstr = et.tostring(xml, encoding='utf8', method='xml')

        for place in xml.findall('kml:Placemark/[kml:Point]', ns):
            location = Place(place.find('kml:name', ns).text,
                             place.find('kml:Point/kml:coordinates', ns).text.split(','))
            self.places.append(location)

        # parse coordinates
        text = xml.find('*//kml:LineString/kml:coordinates', ns).text.strip()
        for point in text.split(' '):
            temp = point.strip().split(',')
            if len(temp) == 3:
                self.points.append(temp)

        # calculate nearest positions to the places
        for index, point in enumerate(self.points):
            for place in self.places:
                distance = self.distance(point, place.pos)
                current = place.closest_distance
                if current == -1 or distance < current:
                    place.closest_point = index
                    place.closest_distance = distance

        # remove excessive waypoints
        for index, place in enumerate(self.places):
            if index < len(self.places) - 1:
                place.wp_count = self.places[index + 1].closest_point - place.closest_point

        for index, place in enumerate(self.places[:-1]):
            if index == 0:
                place.waypoints.append(place.pos)
            step = place.wp_count / self.max_wp
            if step == 0:
                step = 1
            for i in range(place.closest_point, place.closest_point + place.wp_count, step):
                place.waypoints.append(self.points[i])
            place.waypoints.append(self.places[index + 1].pos)

    def distance(self, p1, p2):
        return math.sqrt(pow(float(p1[0]) - float(p2[0]), 2) + pow(float(p1[1]) - float(p2[1]), 2))

    def write_header(self):

        self.output.attrib['VersionNo'] = '0.0'
        self.output.attrib['CreationTime'] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        self.output.attrib['MapVersion'] = '0.0'
        self.output.attrib['Language_Code_Desc'] = '../definitions/language.xml'
        self.output.attrib['Country_Code_Desc'] = '../definitions/country.xml'
        self.output.attrib['Supplier_Code_Desc'] = '../definitions/supplier.xml'
        self.output.attrib['XY_Type'] = 'WGS84'
        self.output.attrib['Category_Code_Desc'] = '../definitions/category.xml'
        self.output.attrib['Char_Set'] = 'UTF-8'
        self.output.attrib['UpdateType'] = 'BulkUpdate'
        self.output.attrib['Coverage'] = '0'
        self.output.attrib['Category'] = '4096'
        self.output.attrib['MajorVersion'] = '0'
        self.output.attrib['MinorVersion'] = '0'

        tour = et.SubElement(self.output, 'GuidedTour', {'access': 'WEEKDAYS', 'use': 'ONFOOT'})
        et.SubElement(tour, 'Id').text = str(self.route_id)
        et.SubElement(tour, 'TripType').text = str(6)

        countries = et.SubElement(tour, 'Countries')
        country = et.SubElement(countries, 'Country')
        et.SubElement(country, 'CountryCode').text = str(3)
        et.SubElement(country, 'Name', {'Language_Code': 'ENG'}).text = 'Germany'

        names = et.SubElement(tour, 'Names')
        name = et.SubElement(names, 'Name', {'Language_Code': 'ENG'})
        et.SubElement(name, 'Text').text = self.name

        et.SubElement(tour, 'Length', {'Unit': 'km'}).text = '0'
        et.SubElement(tour, 'Duration', {'Unit': 'h'}).text = '0'

        intros = et.SubElement(tour, 'Introductions')
        intro = et.SubElement(intros, 'Introduction', {'Language_Code': 'ENG'})
        et.SubElement(intro, 'Text').text = 'hello!'

        descrs = et.SubElement(tour, 'Descriptions')
        descr = et.SubElement(descrs, 'Description', {'Language_Code': 'ENG'})
        et.SubElement(descr, 'Text').text = 'route description goes here...'

        pics = et.SubElement(tour, 'Pictures')

        entry_points = et.SubElement(tour, 'EntryPoints')
        et.SubElement(entry_points, 'EntryPoint', {'Route': '1'}).text = '0_0'
        for i, place in enumerate(self.places[:-1]):
            name = '{}_{}'.format(i, len(place.waypoints) - 1)
            et.SubElement(entry_points, 'EntryPoint', {'Route': '{}'.format(i + 1)}).text = name

        return et.SubElement(tour, 'Routes')

    def write_waypoint(self, root, point, index, place=None):
        wp = et.SubElement(root, 'WayPoint')
        et.SubElement(wp, 'Id').text = "{}_{}".format(index, self.wp_count)

        locations = et.SubElement(wp, 'Locations')
        location = et.SubElement(locations, 'Location')

        if place:
            address = et.SubElement(location, 'Address')
            parsed = et.SubElement(address, 'ParsedAddress')

            street = et.SubElement(parsed, 'ParsedStreetAddress')
            et.SubElement(street, 'StreetName').text = place

            parsed_place = et.SubElement(parsed, 'ParsedPlace')
            et.SubElement(parsed_place, 'PlaceLevel4').text = place

        position = et.SubElement(location, 'GeoPosition')
        et.SubElement(position, 'Latitude').text = point[1]
        et.SubElement(position, 'Longitude').text = point[0]

        et.SubElement(wp, 'Importance').text = 'always' if place else 'optional'

        self.wp_count += 1

    def run(self):
        routes = self.write_header()
        for i, place in enumerate(self.places[:-1]):
            route = et.SubElement(routes, 'Route')
            et.SubElement(route, 'RouteID').text = str(self.route_id)

            self.wp_count = 0  # reset counter for this route
            for wp_index, wp in enumerate(place.waypoints):
                if wp_index == len(place.waypoints) - 1:
                    # write next waypoint with location
                    self.write_waypoint(route, wp, i, self.places[i + 1].name)
                elif i == 0 and wp_index == 0:
                    # write waypoint with location
                    self.write_waypoint(route, wp, i, place.name)
                else:
                    self.write_waypoint(route, wp, i)

            et.SubElement(route, 'Length', {'Unit': 'km'}).text = '0'
            et.SubElement(route, 'Duration', {'Unit': 'h'}).text = '0'
            et.SubElement(route, 'CostModel').text = '0'
            et.SubElement(route, 'Criteria').text = '0'

        return self

    def write(self):
        string = StringIO.StringIO(et.tostring(self.output, 'utf-8'))
        info = tarfile.TarInfo(name="{}.xml".format(self.route_id))
        info.size = len(string.buf)

        stream = StringIO.StringIO()
        with tarfile.open(mode="w:gz", fileobj=stream) as tar:
            tar.addfile(tarinfo=info, fileobj=string)

        stream.seek(0)
        return stream.read()


class Parser:
    def __init__(self, kml, max_wp):
        self.root_kml = kml
        self.routes = []
        self.max_wp = max_wp

    def parse(self):
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        # parse routes
        i = 0
        for folder in self.root_kml.findall('kml:Document/kml:Folder', ns):
            if folder.find('kml:Placemark/kml:LineString', ns) is None:
                continue

            name = folder.find('kml:name', ns).text
            i += 1
            self.routes.append(Route(folder, self.max_wp, name, i))

    def run(self):
        for r in self.routes:
            r.run()

    def write(self):
        zip = InMemoryZip()

        for route in self.routes:
            name = os.path.join('BMWData', 'Navigation', 'Routes', "{}.tar.gz".format(route.name.encode('utf-8')))
            zip.append(name, route.write())

        return zip.read()

if __name__ == "__main__":
    sys.stdout = codecs.getwriter("iso-8859-1")(sys.stdout, 'xmlcharrefreplace')

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="in.kml",
                        help="path to a kml file")
    parser.add_argument("--output", type=str, default="out",
                        help="path to usb device")
    parser.add_argument("--max_wp", type=int, default=10,
                        help="how many waypoints to store between places")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise Exception("File '{}' doesn't exist".format(args.input))

    root_kml = et.parse(args.input).getroot()

    parser = Parser(root_kml, args.max_wp)
    parser.parse()
    parser.run()
    open(args.output, 'wb').write(parser.write())
