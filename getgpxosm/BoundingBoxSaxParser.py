#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# 2012, Johannes Mitlmeier, GPL
# Benötigt wohl Python 2.7 unter Linux


import subprocess, os

from xml.sax import make_parser, handler

class BoundingBoxSaxParser(handler.ContentHandler):
    def __init__(self, folder, my_id, latlon):
        self.folder = folder
        self.my_id = my_id
        if not isinstance(latlon, basestring):
            self.latlon = latlon[0]
        self.latlon = [float(i) for i in latlon.split(',')]
        self.file_counter = 0
        self.out_doc = None
        self.level = 0
        self.point_counter = 0

        self.open_tags = set()
        self.active = False

    def close_file(self):
        if self.out_doc is None:
            return
        # trk trkseg trkpt    
        if 'trkseg' in self.open_tags:
            self.closeTag('trkseg')
        if 'trk' in self.open_tags:
            self.closeTag('trk')
        self.out_doc.write('\n</gpx>')
        self.out_doc.close()
        self.out_doc = None

        print '%d Punkte' % self.point_counter
        # leer?
        if self.point_counter == 0:
            os.remove(self.filename)

    def next_file(self):
        self.file_counter += 1
        self.filename = '%s/%s-%04d.gpx' % (self.folder, self.my_id, self.file_counter)
        self.out_doc = open(self.filename, 'wb')
        print 'Schreibe Track in Datei %s' % (self.filename)
        self.out_doc.write("""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="getgpxosm aus Daten von OpenStreetMap">
        """)
        self.level = 0
        self.point_counter = 0

    def is_good_point(self, lat, lon):
        if lat < self.latlon[0]:
            return False
        if lat > self.latlon[2]:
            return False
        if lon < self.latlon[1]:
            return False
        if lon > self.latlon[3]: 
            return False
        return True
        
    def openTag(self, name, attrs):
        if self.out_doc is None:
            return
        self.out_doc.write('%s<%s' % ('\t'*self.level, name))
        if not attrs is None:
            for attr in attrs.keys():
                self.out_doc.write(' %s="%s"' % (attr, attrs[attr]))
        self.out_doc.write('>')
        self.level += 1
        self.open_tags.add(name)

    def closeTag(self, name):
        if self.out_doc is None:
            return
        self.out_doc.write('</%s>' % (name))
        self.level -= 1
        try:
            self.open_tags.remove(name)
        except KeyError:
            pass

    def startElement(self, name, attrs):
        if name == 'trk':
            self.next_file()
            self.active = True
        elif name == 'trkseg':
            return
        elif name == 'trkpt':
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
        if name == 'trk':
            self.active = False
            self.close_file()
        elif name == 'trkseg':
            if 'trkseg' in self.open_tags:
                self.closeTag('trkseg')
                return           

        if self.active:
            self.closeTag(name)

    def characters(self, content):
        if self.active:
            self.out_doc.write(content.encode('utf8'))

    def endDocument(self):
        self.close_file()

    def ignorableWhitespace(self, whitespace):
        pass
            

