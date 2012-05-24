#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import urllib, os, re, argparse

# Parameter parsen
parser = argparse.ArgumentParser(description='Download von GPX-Traces über die OpenStreetMap-API.')
parser.add_argument('-ll, --latlon', dest="latlon", nargs=1, metavar="BOUNDING_BOX", default="10.038045799999999,49.3093614,10.0412616,49.749925599999995", type=str, help='Bounding-Box im Format lat1,lon1,lat2,lon2')
parser.add_argument('-d, --download', dest="download", action='store_true', help='Download der Rohdaten aktivieren')
parser.add_argument('-e, --extract', dest="extract", action='store_true', help='Extraktion und Download der GPX-Dateien aktivieren')
args = parser.parse_args()
print args

# GET-Anfrage an API
if args.__dict__['download']:
    # TODO Bounding-Box aufsplitten

    page=0
    while True:
        url = "http://api.openstreetmap.org/api/0.6/trackpoints?bbox=%s&page=%d" % (args.__dict__['latlon'],page)
        filename = "page%04d.xml" % page
        print "Download Seite %d: %s" % (page, url)
        urllib.urlretrieve(url, filename)
        page = page + 1
        # Dateigröße prüfen
        if os.path.getsize(filename) < 131:
            print "Datenseiten beendet. " + str(os.path.getsize(filename))
            os.remove(filename)
            break

# XML einlesen
# URLs extrahieren
if args.__dict__['extract']:
    files = os.listdir(os.getcwd())
    for filename in files:
        if not filename.endswith('.xml'):
            continue
        print "testing %s" % filename
        results = re.finditer('<url>(.*?(\d+))</url>', open(filename, 'r').read())
        for result in results:
            gpx_url = "http://www.openstreetmap.org/trace/%s/data/" % result.group(2)
            filename = "%s.gpx" % result.group(2)
            print "Download GPX-Datei: %s" % gpx_url
            # URLs herunterladen
            urllib.urlretrieve(gpx_url, filename)


# TODO eventuell Tracks auslesen und croppen
