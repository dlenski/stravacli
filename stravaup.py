#!/usr/bin/env python2
from __future__ import print_function

from stravalib import Client, exc
from sys import stderr
from tempfile import NamedTemporaryFile
import webbrowser, os.path, ConfigParser, gzip
import argparse
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

#####

allowed_exts = ('.tcx','.gpx','.fit')

p = argparse.ArgumentParser(description='''Uploads activities to Strava.''')
p.add_argument('activities', nargs='+', type=argparse.FileType("rb"), help="Activity files to upload (plain or gzipped {})".format(', '.join(allowed_exts)))
p.add_argument('-p', '--private', action='store_true', help='Make activities private')
p.add_argument('-P', '--no-popup', action='store_true', help="Don't browse to activities after upload.")
p.add_argument('-N', '--no-parse', action='store_true', help="Don't parse name/description fields from files.")
p.add_argument('-E', '--env', help='Look for ACCESS_TOKEN in environment variable rather than ~/.stravacli')
args = p.parse_args()

#####

# Authorize Strava

cid = 3163 # CLIENT_ID
if args.env:
    cat = os.environ.get('ACCESS_TOKEN')
else:
    cp = ConfigParser.ConfigParser()
    cp.read(os.path.expanduser('~/.stravacli'))
    cat = None
    if cp.has_section('API'):
        cat = cp.get('API', 'ACCESS_TOKEN') if 'access_token' in cp.options('API') else None

authorized = False
while not authorized:
    client = Client(cat)
    try:
        athlete = client.get_athlete()
    except Exception as e:
        print("NOT AUTHORIZED")
        print("Need Strava API access token. Launching web browser to obtain one.", file=stderr)
        client = Client()
        authorize_url = client.authorization_url(client_id=cid, redirect_uri='http://stravacli-dlenski.rhcloud.com/auth', scope='view_private,write')
        webbrowser.open_new_tab(authorize_url)
        client.access_token = cat = raw_input("Enter access token: ")
    else:
        authorized = True
        if not cp.has_section('API'):
            cp.add_section('API')
        if not 'ACCESS_TOKEN' in cp.options('API') or cp.get('API', 'ACCESS_TOKEN', None)!=cat:
            cp.set('API', 'ACCESS_TOKEN', cat)
            cp.write(open(os.path.expanduser('~/.stravacli'),"w"))

print("Authorized to access account of {} {} (id {:d}).".format(athlete.firstname, athlete.lastname, athlete.id))

#####

for ii,f in enumerate(args.activities):
    print("Uploading activity from {}...".format(f.name))

    base, ext = os.path.splitext(f.name)
    gz = False
    if ext.lower()=='.gz':
        base, ext = os.path.splitext(base)
        # un-gzip it in order to parse it
        cf, uf = f, gzip.GzipFile(fileobj=f, mode='r')
    else:
        # gzip it for upload
        uf, cf = f, NamedTemporaryFile(suffix='.gz', delete=False)
        gzip.GzipFile(fileobj=cf, mode='w+').writelines(f)
        uf.seek(0, 0)

    if ext.lower() not in allowed_exts:
        p.error("  Don't know how to handle extension {} (allowed are {}).".format(ext, ', '.join(allowed_exts)))

    # try to parse activity name, description from file if requested
    name = desc = None
    if not args.no_parse:
        if ext.lower()=='.gpx':
            x = etree.parse(uf)
            nametag, desctag = x.find("{*}name"), root.find("{*}desc")
            name = nametag and nametag.text
            desc = desctag and desctag.text
        elif ext.lower()=='.tcx':
            x = etree.parse(uf)
            notestag = x.find("{*}Activities/{*}Activity/{*}Notes")
            if notestag is not None:
                name, desc = (notestag.text.split('\n',1)+[None])[:2]

    # upload activity
    cf.seek(0, 0)
    try:
        upstat = client.upload_activity(cf, ext[1:] + '.gz', name, desc, private=args.private)
        if cf is not f:
            cf.close()
            os.unlink(cf.name)
        elif uf is not f:
            uf.close()
        activity = upstat.wait()
        duplicate = False
    except exc.ActivityUploadFailed as e:
        words = e.args[0].split()
        if words[-4:-1]==['duplicate','of','activity']:
            activity = client.get_activity(words[-1])
            duplicate = True
        else:
            raise

    # show results
    uri = "http://strava.com/activities/{:d}".format(activity.id)
    print("  {}{}".format(uri, " (duplicate)" if duplicate else ''), file=stderr)
    if not args.no_popup:
        webbrowser.open_new_tab(uri)
