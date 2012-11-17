#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright 2012, Johannes Mitlmeier, AGPLv3
# probably neeeds at least python 2.7 and linux for unzipping and merging


import subprocess, os, re, codecs
from xml.sax import make_parser, handler

class BoundingBoxSaxParser(handler.ContentHandler):
    def __init__(self, latlon):
        self.tag_order = ['trk', 'trkseg', 'trkpt']
        self.latlon = latlon
        self.open_tags = set()
        self.open_source_tags = set()
        self.filter_this_track = False
        self.do_output = True

        # Einstellungen
        self.filter_urls = True
        self.extra_border = 0.0


    def set_file(self, folder, filename):
        self.folder = folder
        self.filename = filename        
        self.out_doc = None

        self.file_counter = 0
        self.point_counter = 0
        self.level = 0


    def close_file(self):
        print('Trying to close file')
        if self.out_doc is None:
            return
        # trk trkseg trkpt
        self.do_output = True
        self.closeTag('trkseg')
        self.closeTag('trk')
        self.out_doc.write('\n</gpx>')
        self.out_doc.close()
        self.out_doc = None

        # leer?
        if self.point_counter == 0:
            print("removing file " + self.gen_filename)
            os.remove(self.gen_filename)
            self.file_counter -= 1
        else:
            print('Track in Datei %s (%d Punkte)' % (self.gen_filename, self.point_counter))
        
    def next_file(self):
        self.file_counter += 1
        print("new file no. " + str(self.file_counter))
        self.gen_filename = '%s/%s-%04d.gpx' % (self.folder, self.filename, self.file_counter)
        self.out_doc = codecs.open(self.gen_filename, 'wb', 'utf-8')
        self.out_doc.write("""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="getgpxosm from OpenStreetMap GPS data">
        """)
        self.do_output = True
        self.open_tags.add('gpx')
        self.level = 0
        self.point_counter = 0

    def is_good_point(self, lat, lon):
        if lat < self.latlon[0] - self.extra_border:
            return False
        if lat > self.latlon[2] + self.extra_border:
            return False
        if lon < self.latlon[1] - self.extra_border:
            return False
        if lon > self.latlon[3] + self.extra_border: 
            return False
        return True
        
    def openTag(self, name, attrs=None, autocall=False):
        print("shall open tag " + name)
        if not self.do_output:
            return
        if name in self.open_tags:
            print("tag already open: " + name + " > " + str(self.open_tags))
            return
        if self.out_doc is None:
            self.next_file()

        index = self.tag_order.index(name) if name in self.tag_order else 0
        if not autocall:
            for i in range(index):
                self.openTag(self.tag_order[i], autocall=True)

        print("opening tag " + name)
        try:
            self.out_doc.write('\n%s<%s' % ('\t'*self.level, name))
            if not attrs is None:
                for attr in list(attrs.keys()):
                    self.out_doc.write(' %s="%s"' % (attr, attrs[attr]))
            self.out_doc.write('>')
            self.level += 1
            self.open_tags.add(name)
        except AttributeError:
            traceback.print_exc()

    def closeTag(self, name):
        if self.out_doc is None:
            return
        if not self.do_output:
            return
        try:
            self.open_tags.remove(name)
            self.out_doc.write('</%s>' % (name))
            self.level -= 1
        except KeyError:
            pass

    def startElement(self, name, attrs):
        self.open_source_tags.add(name)
        #if not (name == 'time') and not (name == 'trkpt'):
        #    print(name)

        if 'cmt' in self.open_source_tags:
            return
        if name == 'url' and self.filter_urls:
            #print("filtering track")
            self.filter_this_track = True
            #self.next_file()
            self.do_output = False
            return
        elif name == 'gpx':
            return
        elif name == 'trk':
            #print("starting track")
            self.filter_this_track = False
            return
        elif name == 'trkpt':
            if self.filter_this_track:
                return
            else:
                if self.is_good_point(float(attrs['lat']), float(attrs['lon'])):
                    print("point is visible")
                    self.point_counter += 1                
                    self.do_output = True
                else:
                    print("point is not visible")
                    self.do_output = False
                    if self.point_counter > 0:
                        self.close_file()
                    return
    
        print("do_output (" + name + "): " + str(self.do_output))
        if self.do_output:
            self.openTag(name, attrs)

    def endElement(self, name):
        try:
            self.open_source_tags.remove(name)
        except KeyError:
            pass

        if 'cmt' in self.open_source_tags:
            if not name == 'cmt':
                return                
        if name == 'trkseg':
            self.close_file()         

        self.closeTag(name)

    def characters(self, content):
        if 'cmt' in self.open_source_tags:
            return
        if not self.do_output:
            return
        if re.match('^\s*$', str(content)):
            return
        if not self.filter_this_track:
            self.out_doc.write(content)

    def endDocument(self):
        self.close_file()

    def ignorableWhitespace(self, whitespace):
        pass
            

