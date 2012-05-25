#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# 2012, Johannes Mitlmeier, GPL
# Benötigt wohl Python 2.7 unter Linux, xml-twig-tools zum Einrücken von XML


import urllib, sys, os, re, argparse, subprocess, gc
from xml.sax import make_parser, handler
from BoundingBoxSaxParser import BoundingBoxSaxParser
gc.enable()


dl_cache = set()
def download(url, filename):
    if url + "#" + filename in dl_cache:
        return    
    urllib.urlretrieve(url, filename)
    dl_cache.add(url + "#" + filename)


# Parameter parsen
parser = argparse.ArgumentParser(description='Download von GPX-Traces über die OpenStreetMap-API.')
parser.add_argument('-ll, --latlon', dest="latlon", nargs=1, metavar="BOUNDING_BOX", default="52.4852552,13.2603453,52.5643357,13.4181609", type=str, help='Bounding-Box im Format lat1,lon1,lat2,lon2')
parser.add_argument('-w, --width', dest="width", nargs=1, metavar="INT", default="0.45", type=float, help='Breite/Höhe der unterteilten Bounding-Boxen')
parser.add_argument('-d, --download', dest="download", action='store_true', help='Download der Rohdaten aktivieren')
parser.add_argument('-e, --extract', dest="extract", action='store_true', help='Extraktion und Download der GPX-Dateien aktivieren')
parser.add_argument('-bb, --bounding-box', dest="boundingbox", action='store_true', help='GPX-Dateien auf Bounding Box (siehe Parameter -ll) beschränken')
#parser.add_argument('-m, --merge', dest="merge", action='store_true', help='Einzelne GPX-Tracks zu einer Datei bündeln')
args = parser.parse_args()
print args



# GET-Anfrage an API
if args.__dict__['download']:
    if not os.path.exists("API"):
        os.makedirs("API")

    # Bounding-Box aufsplitten
    width = args.__dict__['width']
    latlon = args.__dict__['latlon'][0].split(',')
    lats = []
    curr_lat = float(parts[0])
    while curr_lat < float(parts[2]):
        lats.append(curr_lat)
        curr_lat += width
    lons = []
    curr_lon = float(parts[1])
    while curr_lon < float(parts[3]):
        lons.append(curr_lon)
        curr_lon += width
    
    tiles = ["%s,%s,%s,%s" % (lat,lon,max(lat+width,parts[2]),max(lon+width,parts[3])) for lat in lats for lon in lons]
    
    output_counter = 0
    for tile in tiles:
        page = 0
        while True:
            url = "http://api.openstreetmap.org/api/0.6/trackpoints?bbox=%s&page=%d" % (tile ,page)
            filename = "API/page%04d.xml" % output_counter
            print "Download Seite %d: %s" % (page, url)
            download(url, filename)
            page = page + 1
            output_counter = output_counter + 1
            # Dateigröße prüfen
            if os.path.getsize(filename) < 131:
                print "Datenseiten beendet. Dateigröße %s." % str(os.path.getsize(filename))
                os.remove(filename)
                break


# XML einlesen
# URLs extrahieren
if args.__dict__['extract']:
    if not os.path.exists("GPX"):
        os.makedirs("GPX")
    folder = os.getcwd() + "/API/"
    files = os.listdir(folder)
    for filename in files:
        if not filename.endswith('.xml'):
            continue
        full_filename = folder + filename
        print "Extrahiere Links aus Datei %s" % full_filename
        results = re.finditer('<url>(.*?(\d+))</url>', open(full_filename, 'r').read())
        for result in results:
            gpx_url = "http://www.openstreetmap.org/trace/%s/data/" % result.group(2)
            filename = "GPX/%s.gpx" % result.group(2)
            print "Download GPX-Datei: %s" % gpx_url
            # URLs herunterladen
            if not os.path.exists(filename): # kein Überschreiben
                download(gpx_url, filename)
                # tar.gz- oder gz-Archive auspacken
                subprocess.call(["tar", "-zxf", filename, "GPX"], stderr=subprocess.PIPE)



# Tracks splitten und croppen
if args.__dict__['boundingbox']:
    if not os.path.exists("output"):
        os.makedirs("output")
    
    # GPX-Dateien lesen
    folder = os.getcwd() + "/GPX/"
    files = os.listdir(folder)
    for filename in files:
        #continue
        if not filename.endswith('.gpx'):
            continue
        print "Verarbeite %s" % filename
        my_id, ext = os.path.splitext(filename)
        full_filename = folder + filename
        parser = make_parser()
        parser.setContentHandler(BoundingBoxSaxParser(os.getcwd() + '/output', my_id, args.__dict__['latlon']))
        try:
            parser.parse(full_filename)
        except Exception:
            print 'ERROR: Parse-Fehler'
        gc.collect()


# TODO implementieren?
#if args.__dict__['merge']:
#    pass
