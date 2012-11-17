#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright 2012, Johannes Mitlmeier, AGPLv3
# probably neeeds at least python 2.7 and linux for unzipping and merging


import urllib.request, urllib.parse, urllib.error, sys, os, re, argparse, subprocess, gc, codecs
from xml.sax import make_parser, handler
from xml.sax._exceptions import SAXParseException
from BoundingBoxSaxParser import BoundingBoxSaxParser
from multiprocessing import Pool

gc.enable()


dl_cache = set()
def download(url, filename):
    if url + '#' + filename in dl_cache:
        return    
    urllib.request.urlretrieve(url, filename)
    dl_cache.add(url + '#' + filename)



# Parameter parsen
parser = argparse.ArgumentParser(description='Download von GPX-Traces über die OpenStreetMap-API.')
parser.add_argument('-ll', '--latlon', dest='latlon', nargs=1, metavar='BOUNDING_BOX', default=['52.4852552,13.2603453,52.5643357,13.4181609'], type=str, help='Bounding-Box im Format lat1,lon1,lat2,lon2')
parser.add_argument('-w', '--width', dest='width', nargs=1, metavar='FLOAT', default=[0.45], type=float, help='Breite/Höhe der unterteilten Bounding-Boxen')
parser.add_argument('-d', '--download', dest='download', action='store_true', help='Download der Rohdaten aktivieren')
parser.add_argument('-e', '--extract', dest='extract', action='store_true', help='Extraktion und Download der GPX-Dateien aktivieren')
parser.add_argument('-u', '--unzip', dest='unzip', action='store_true', help='Archive mit GPX-Dateien auspacken')
parser.add_argument('-bb', '--bounding-box', dest='boundingbox', action='store_true', help='GPX-Dateien auf Bounding Box (siehe Parameter -ll) beschränken')
parser.add_argument('-s', '--safety-border', dest='safety-border', nargs=1, metavar='FLOAT', default=[0.00], type=float, help='Randabstand zur Bounding-Box, um korrekt zu trennen')
parser.add_argument('-m', '--merge', dest='merge', action='store_true', help='Einzelne GPX-Tracks zu einer Datei bündeln')
args = parser.parse_args()
print(args)



if args.__dict__['latlon']:
    latlon = args.__dict__['latlon']
    latlon = [float(i) for i in latlon[0].split(',')]
    latlon = [min(latlon[0], latlon[2]), min(latlon[1], latlon[3]), max(latlon[0], latlon[2]), max(latlon[1], latlon[3])]

# GET-Anfrage an API
if args.__dict__['download']:
    print('Download')
    if not os.path.exists('API'):
        os.makedirs('API')

    # Bounding-Box aufsplitten
    width = args.__dict__['width'][0]
    lats = []
    curr_lat = latlon[0]
    while curr_lat < latlon[2]:
        lats.append(curr_lat)
        curr_lat += width
    lons = []
    curr_lon = latlon[1]
    while curr_lon < latlon[3]:
        lons.append(curr_lon)
        curr_lon += width
    
    tiles = ['%f,%f,%f,%f' % (lon,lat,min(lon+width,latlon[3]),min(lat+width,latlon[2])) for lat in lats for lon in lons]
    print('#Tiles: %d' % len(tiles))

    output_counter = 0
    for tile in tiles:
        page = 0
        while True:
            url = 'http://api.openstreetmap.org/api/0.6/trackpoints?bbox=%s&page=%d' % (tile ,page)
            filename = 'API/page%04d.xml' % output_counter
            print('Download Seite %d: %s' % (page, url))
            download(url, filename)
            page = page + 1
            output_counter = output_counter + 1
            # Dateigröße prüfen
            if os.path.getsize(filename) < 131:
                print('Datenseiten beendet. Dateigröße %d (%s).' % (os.path.getsize(filename), codecs.open(filename, 'rb', 'utf-8').read()))
                os.remove(filename)
                break


# XML einlesen
# URLs extrahieren
if args.__dict__['extract']:
    print('Extract')
    if not os.path.exists('GPX'):
        os.makedirs('GPX')
    folder = os.getcwd() + '/API/'
    files = os.listdir(folder)

    working_dir = os.getcwd()
    os.chdir(working_dir + '/GPX')

    for filename in files:
        if not filename.endswith('.xml'):
            continue
        full_filename = folder + filename
        print('Extrahiere Links aus Datei %s' % full_filename)
        results = re.finditer('<url>(.*?(\d+))</url>', codecs.open(full_filename, 'r', 'utf-8').read())
        for result in results:
            gpx_url = 'http://www.openstreetmap.org/trace/%s/data/' % result.group(2)
            filename_real = '%s.gpx' % result.group(2)
            print('Download GPX-Datei: %s' % gpx_url)
    
            # URLs herunterladen
            retcode = 1
            if not os.path.exists(filename_real): # kein Überschreiben
                download(gpx_url, filename_real)
            
    os.chdir(working_dir)


# Archive auspacken
if args.__dict__['unzip']:
    folder = os.getcwd() + '/GPX/'
    files = os.listdir(folder)

    working_dir = os.getcwd()
    os.chdir(working_dir + '/GPX')

    for filename in files:
        filename_packed = filename + '.packed'
        os.rename(filename, filename + '.packed')

        # zip
        retcode = subprocess.call(['unzip', '-u', os.getcwd() + '/' + filename_packed], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if retcode == 0:
            print("%s (ZIP-Archiv)" % filename)
        if retcode > 0: 
            # tar.gz
            retcode = subprocess.call(['tar', '-zxfv', os.getcwd() + '/' + filename_packed], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if retcode == 0:
                print("%s (tar.gz-Archiv)" % filename)
            if retcode > 0:
                # gz
                retcode = subprocess.call(['gunzip', '--suffix', '.packed', '--force', '--verbose', os.getcwd() + '/' + filename_packed], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if retcode == 0:
                    print("%s (gz-Archiv)" % filename)

        # wurde etwas entpackt?     
        try:
            if retcode == 0:
                os.remove(filename_packed)
            else:
                os.rename(filename_packed, filename)
        except OSError:
            pass
    os.chdir(working_dir)



# Tracks splitten und croppen
if args.__dict__['boundingbox']:
    if not os.path.exists('output'):
        os.makedirs('output')
    
    # GPX-Dateien lesen
    folder = os.getcwd() + '/GPX/'
    files = os.listdir(folder)
    parser = make_parser()
    my_parser = BoundingBoxSaxParser(latlon)
    parser.setContentHandler(my_parser)
    for filename in files:
        if not filename.endswith('.gpx'):
            continue
        print('Verarbeite %s' % filename)
        my_id, ext = os.path.splitext(filename)
        full_filename = folder + filename
        my_parser.set_file(os.getcwd() + '/output', my_id)
        try:
            fh = codecs.open(full_filename, 'r', encoding='utf-8', errors='ignore')
            #print fh
            parser.parse(fh)
        except SAXParseException as ex:
            print('%s: %s' % (type(ex), ex))
        except (UnicodeEncodeError, UnicodeDecodeError) as ex:
            print('%s: %s' % (type(ex), ex))
        except Exception as ex:
            print('%s: %s' % (type(ex), ex))

        my_parser.close_file()
        gc.collect()

    # API-Dateien lesen
    folder = os.getcwd() + '/API/'
    files = os.listdir(folder)
    my_parser.filter_urls = True
    my_parser.extra_border = args.__dict__['safety-border'][0]
    for filename in files:
        if not filename.endswith('page0000.xml'):
            continue
        print('Verarbeite %s' % filename)
        my_id, ext = os.path.splitext(filename)
        full_filename = folder + filename
        my_parser.set_file(os.getcwd() + '/output', my_id)
        try:
            parser.parse(codecs.open(full_filename, 'r', 'utf-8'))
        except Exception as ex:
            print('%s: %s' % (type(ex), ex))

        my_parser.close_file()
        gc.collect()





# Jens Fischer
if args.__dict__['merge']:
    print('Dateien zusammenfügen...')    
    folder = os.getcwd() + '/output/'
    try:    
        os.remove(folder + '_merged.gpx')
    except OSError:
        pass
    babelargs = ['gpsbabel', '-i', 'gpx']
    files = os.listdir(folder)
    for filename in files:
    	babelargs.extend(['-f', folder + filename])
    babelargs.extend(['-o', 'gpx', '-F', folder + '_merged.gpx'])
    subprocess.call(babelargs)
    print('Fertig')


