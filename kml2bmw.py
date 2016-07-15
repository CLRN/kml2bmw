import argparse
import os
import xml.etree.ElementTree as et
import ntpath
import tarfile
import datetime
import xml.dom.minidom as minidom
import sys
import codecs


sys.stdout = codecs.getwriter("iso-8859-1")(sys.stdout, 'xmlcharrefreplace')

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, default="in.kml",
                    help="path to a kml file")
parser.add_argument("--output", type=str, default="out",
                    help="path to usb device")
args = parser.parse_args()


class Parser:
    def __init__(self, file):
        self.root_kml = et.parse(file).getroot()

        self.name = os.path.splitext(ntpath.basename(file))[0]
        self.places = []
        self.points = []
        self.output = et.Element('DeliveryPackage')
        self.route_id = 1
        self.wp_count = 0

        self.parse()

    def parse(self):

        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        # parse places
        for place in self.root_kml.findall('kml:Document/kml:Placemark/[kml:Point]', ns):
            location = {'name': place.find('kml:name', ns).text,
                        'pos': place.find('kml:Point/kml:coordinates', ns).text.split(',')}

            self.places.append(location)

        # parse coordinates
        text = self.root_kml.find('*//kml:LineString/kml:coordinates', ns).text
        self.points = [point.split(',') for point in text.split(' ')]
        
        #self.points = self.points[:10]

    def write(self, out_name):
        dir = os.path.join(out_name, 'BMWData', 'Navigation', 'Routes')
        if not os.path.exists(dir):
            os.makedirs(dir)

        xml_name = "{}.xml".format(self.route_id)
        path = os.path.join(dir, xml_name)
        arch_name = os.path.join(dir, "{}.tar.gz".format(self.name))

        rough_string = et.tostring(self.output, 'utf-8')
        reparsed = minidom.parseString(rough_string)

        pretty = reparsed.toprettyxml(indent="  ")
        codecs.open(path, 'wb', 'utf-8').write(pretty)

        with tarfile.open(arch_name, "w:gz") as tar:
            tar.add(path, arcname=xml_name)

        os.remove(path)


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
        et.SubElement(entry_points, 'EntryPoint', {'Route': '1'}).text = '0_{}'.format(len(self.points) + len(self.places) - 1)

        routes = et.SubElement(tour, 'Routes')
        route = et.SubElement(routes, 'Route')
        et.SubElement(route, 'RouteID').text = str(self.route_id)

        return route

    def write_place(self, root, place):
        self.write_waypoint(root, place['pos'], place['name'])

    def write_waypoint(self, root, point, place):
        wp = et.SubElement(root, 'WayPoint')
        et.SubElement(wp, 'Id').text = "0_{}".format(self.wp_count)
        
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
        route = self.write_header()

        self.write_place(route, self.places[0])

        for point in self.points:
            self.write_waypoint(route, point, None)

        self.write_place(route, self.places[1])

        et.SubElement(route, 'Length', {'Unit': 'km'}).text = '0'
        et.SubElement(route, 'Duration', {'Unit': 'h'}).text = '0'
        et.SubElement(route, 'CostModel').text = '0'
        et.SubElement(route, 'Criteria').text = '0'
               
        return self


if not os.path.exists(args.input):
    raise Exception("File '{}' doesn't exist".format(args.input))

Parser(args.input).run().write(args.output)