#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright 2012, Johannes Mitlmeier, AGPLv3
# Benötigt wohl mindestens Python 2.7 unter Linux


import subprocess, os, re, codecs
from xml.sax import make_parser, handler

class BoundingBoxSaxParser(handler.ContentHandler):
    def __init__(self, latlon):
        self.latlon = latlon
        self.open_tags = set()
        self.open_source_tags = set()
        self.active = False

        # Einstellungen
        self.filter_urls = False
        self.extra_border = 0.0


    def set_file(self, folder, filename):
        self.folder = folder
        self.filename = filename        
        self.out_doc = None

        self.file_counter = 0
        self.point_counter = 0
        self.level = 0


    def close_file(self):
        #print('Trying to close file')
        if self.out_doc is None:
            return
        # trk trkseg trkpt    
        self.closeTag('trkseg')
        self.closeTag('trk')
        self.out_doc.write('\n</gpx>')
        self.out_doc.close()
        self.out_doc = None

        print('%d Punkte' % self.point_counter)
        # leer?
        if self.point_counter == 0:
            os.remove(self.gen_filename)

    def next_file(self):
        self.file_counter += 1
        self.gen_filename = '%s/%s-%04d.gpx' % (self.folder, self.filename, self.file_counter)
        self.out_doc = codecs.open(self.gen_filename, 'wb', 'utf-8')
        print('Schreibe Track in Datei %s' % (self.gen_filename))
        self.out_doc.write("""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="getgpxosm aus Daten von OpenStreetMap">
        """)
        self.level = 0
        self.point_counter = 0

    def is_good_point(self, lat, lon):
        if lat < self.latlon[0] + self.extra_border:
            return False
        if lat > self.latlon[2] - self.extra_border:
            return False
        if lon < self.latlon[1] + self.extra_border:
            return False
        if lon > self.latlon[3] - self.extra_border: 
            return False
        return True
        
    def openTag(self, name, attrs):
        if self.out_doc is None:
            return
        self.out_doc.write('\n%s<%s' % ('\t'*self.level, name))
        if not attrs is None:
            for attr in list(attrs.keys()):
                self.out_doc.write(' %s="%s"' % (attr, attrs[attr]))
        self.out_doc.write('>')
        self.level += 1
        self.open_tags.add(name)

    def closeTag(self, name):
        if self.out_doc is None:
            return
        try:
            self.open_tags.remove(name)
            self.out_doc.write('</%s>' % (name))
            self.level -= 1
        except KeyError:
            pass

    def startElement(self, name, attrs):
        self.open_source_tags.add(name)

        if 'cmt' in self.open_source_tags:
            return
        if name == 'url' and self.filter_urls:
            self.active = False
            return
        if name == 'trk':
            self.next_file()
            self.active = True
        elif name == 'trkseg':
            return
        elif name == 'trkpt':
            if not self.filter_urls or self.active:
                if self.is_good_point(float(attrs['lat']), float(attrs['lon'])):
                    self.point_counter += 1                
                    # ggf. Segment öffnen (weil unterbrochen)
                    if not 'trkseg' in self.open_tags:
                        self.openTag('trkseg', None)
                    self.active = True
                else:
                    if 'trkseg' in self.open_tags:
                        self.closeTag('trkseg')
                    self.active = False # es darf nichts ausgegeben werden, der Punkt ist raus

        if self.active:
            self.openTag(name, attrs)

    def endElement(self, name):
        try:
            self.open_source_tags.remove(name)
        except KeyError:
            pass

        if 'cmt' in self.open_source_tags:
            if not name == 'cmt':
                return
                
        if name == 'trk':
            self.active = False
            self.close_file()
        elif name == 'trkseg':
            if 'trkseg' in self.open_tags:
                self.closeTag('trkseg')
                return           
        elif name == 'trkpt':
            self.active = True            

        if self.active:
            self.closeTag(name)

    def characters(self, content):
        if 'cmt' in self.open_source_tags:
            return
        if re.match('^\s*$', str(content)):
            return
        if self.active:
            self.out_doc.write(content)

    def endDocument(self):
        self.close_file()

    def ignorableWhitespace(self, whitespace):
        pass
            

