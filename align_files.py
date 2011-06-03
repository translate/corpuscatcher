#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008,2011 Zuza Software Foundation
#
# This file is part of CorpusCatcher.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os
from os import path
import shutil
import re
from translate.search import lshtein

global html_weight
global num_weight
global url_weight

def strip_text(filestring=""):
    p = re.compile('>.*<')
    return p.sub(r'><', filestring)

def get_numbers(filestring=""):
    numlist = []
    p = re.compile('\d[\d.:, ]*\d')
    prenumlist = re.findall(p, filestring)
    for n in prenumlist:
        if n != '':
            numlist.append(n)
    return numlist

def get_numbers_shortlist(srcfile, tgtfiles, listsize=3):
    slist = [None]*listsize
    dummylist = []
    for t in tgtfiles:
        dummylist.append(t)
    for i in range(listsize):
        slist[i] = dummylist[0]
        intersect = len(set(get_numbers(srcfile['html'])) & set(get_numbers(slist[i]['html'])))
        for t in dummylist:
            tintersect = len(set(get_numbers(srcfile['html'])) & set(get_numbers(t['html'])))
            if tintersect > intersect:
                slist[i] = t
                intersect = tintersect
        dummylist.remove(slist[i])
    return slist

#computes distance on html structure
def get_lshtein_shortlist(srcfile, tgtfiles, listsize=3):
    slist = [None]*listsize
    dummylist = []
    for t in tgtfiles:
        dummylist.append(t)
    for i in range(listsize):
        slist[i] = dummylist[0]
        dist = lshtein.distance(strip_text(srcfile['html']), strip_text(slist[i]['html']))
        for t in dummylist:
            ldist = lshtein.distance(strip_text(srcfile['html']), strip_text(t['html']))
            if ldist < dist:
                slist[i] = t
                dist = ldist
        dummylist.remove(slist[i])
    return slist

def get_match(srcfile, slist, hweight, nweight, uweight, c, v):
    match = slist[0]
    bconf = 0.0
    if len(slist) > 0:
        for t in slist:
            html = lshtein.distance(strip_text(srcfile['html']), strip_text(t['html']))
            html_rel = float(len(strip_text(srcfile['html']))-html) / len(strip_text(srcfile['html']))
            
            srcnumbers = set(get_numbers(srcfile['html']))
            num_rel = float(len(srcnumbers & set(get_numbers(t['html'])))) / float(len(srcnumbers))
            
            url = lshtein.distance(srcfile['url'], t['url'])
            url_rel = float(len(srcfile['url']) - url) / len(srcfile['url'])
            
            conf = url_rel*uweight + num_rel*nweight + html_rel*hweight
            if v:
                print "TGTFILE: ", t['filename']
                print "url: ", url_rel
                print "num: ", num_rel
                print "html: ", html_rel
                print "conf:", conf
            
            if conf > bconf:
                match = t
                bconf = conf
        
        if bconf < c: #below threshhold
            return None
                
        if match['match'] != None:
            if srcfile['conf'] < bconf: #if better match
                match['match']['match'] = None
                match['match']['conf'] = 0.0
                match['match'] = srcfile
                return (match, bconf)
            else:
                return None #srcfile not matched
        
        match['match'] = srcfile
        return (match, bconf)

def copy_matched_files(srcfiles, srcdir, tgtdir, destdir, s, v):
    #TODO: add line to matched target file that includes original filename and confidence
    if not os.path.exists(destdir):
        os.mkdir(destdir)
    for f in srcfiles:
        if f['match'] != None:
            shutil.copy2(os.path.join(srcdir, f['filename']), os.path.join(destdir, f['filename']))
            shutil.copy2(os.path.join(tgtdir, f['match']['filename']), os.path.join(destdir, f['match']['filename']))
            if v:
                print "Copied", os.path.join(srcdir, f['filename']), "to", os.path.join(destdir, f['filename'])
                print "Copied", os.path.join(tgtdir, f['match']['filename']), "to", os.path.join(destdir, f['match']['filename'])
            fl = f['filename'].split(".")
            if len(fl) > 1:
                os.rename(os.path.join(destdir, f['match']['filename']), os.path.join(destdir, fl[0]+"-"+s+"."+fl[1]))
                if v:
                    print "Renamed", os.path.join(destdir, f['match']['filename']), "to", os.path.join(destdir, fl[0]+"-"+s+"."+fl[1])
            else:
                os.rename(os.path.join(destdir, f['match']['filename']), os.path.join(destdir, s+"-"+f['filename']))
                if v:
                    print "Renamed", os.path.join(destdir, f['match']['filename']), os.path.join(destdir, s+"-"+f['filename'])

def create_option_parser():
    """Creates command-line option parser for when this script is used on the
        command-line. Run "align_files.py -h" for help regarding options."""
    from optparse import OptionParser
    usage='Usage: %prog [<options>] <source dir> <target dir> <destination dir>'
    parser = OptionParser(usage=usage)

    parser.add_option(
        '-q', '--quiet',
        dest='quiet',
        action="store_true",
        help='Suppress output (quiet mode).',
        default=False
    )
    parser.add_option(
        '-v', '--verbose',
        dest='verbose',
        action="store_true",
        help='More output (verbose mode).',
        default=False
    )
    parser.add_option(
        '-w', '--weights',
        dest='weights',
        type="float",
        nargs=3,
        action="store",
        help='Weights assigned to html, numbers and url correspondence.',
        default=(0.1, 0.7, 0.2)
    )
    parser.add_option(
        '-c', '--confidence',
        dest='confidence',
        type="float",
        action="store",
        help='Confidence threshhold for accepting matches.',
        default=(0.9)
    )
    parser.add_option(
        '-s', '--string',
        dest='string',
        type="str",
        action="store",
        help='String to use in renaming process',
        default=("target")
    )
    return parser

def main():
    """Main entry-point for command-line usage."""
    options, args = create_option_parser().parse_args()
    
    html_weight = options.weights[0]
    num_weight = options.weights[1]
    url_weight = options.weights[2]
    q = options.quiet
    v = options.verbose
    c = options.confidence
    s = options.string
    
    if len(args) == 3:
        sourcedir = args[0]
        targetdir = args[1]
        destdir = args[2]
        
        try:
            srcfilenames = os.listdir(sourcedir)
        except OSError:
            print "OSError:", sourcedir, "not a valid directory"
            return
        try:
            tgtfilenames = os.listdir(targetdir)
        except OSError:
            print "OSError:", targetdir, "not a valid directory"
            return
        
        srcfiles = []
        tgtfiles = []
        
        for f in srcfilenames:
            if f.endswith('html'):
                u = file(os.path.join(sourcedir,f)).readline()[10:-5]
                h = file(os.path.join(sourcedir,f)).read()
                srcfiles.append({'filename':f, 'url':u, 'html':h, 'match':None, 'conf':0})
        for f in tgtfilenames:
            if f.endswith('html'):
                u = file(os.path.join(targetdir,f)).readline()[10:-5]
                h = file(os.path.join(targetdir,f)).read()
                tgtfiles.append({'filename':f, 'url':u, 'html':h, 'match':None})
        
        if not q:
            print "Matching files..."
        for f in srcfiles:
            if v:
                print "\nSRCFILE: ", f['filename']
            ftuple = get_match(f, get_numbers_shortlist(f, tgtfiles), html_weight, num_weight, url_weight, c, v)
            if ftuple != None:
                f['match'] = ftuple[0]
                f['conf'] = ftuple[1]
                if not q:
                    print "Match:", f['filename'], "=>", f['match']['filename'], "\nConfidence:", f['conf']
                if v:
                    print file(os.path.join(sourcedir,f['filename'])).readline(), file(os.path.join(targetdir,f['match']['filename'])).readline()
            else:
                if not q:
                    print f['filename'], "could not be matched"
        if not q:
            print "Copying matched files to %s..." % (destdir)
        copy_matched_files(srcfiles, sourcedir, targetdir, destdir, s, v)
    else:
        print "Usage: %prog [<options>] <source dir> <target dir> <destination dir>"

if __name__ == '__main__':
    main()