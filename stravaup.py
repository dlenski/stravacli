#!/usr/bin/env python2
from __future__ import print_function

from stravalib import Client, exc
from sys import stderr, stdin
from tempfile import NamedTemporaryFile
import webbrowser, os.path, ConfigParser, gzip
import argparse
from cStringIO import StringIO
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

#####

allowed_exts = {'.tcx': lambda v: '<TrainingCenterDatabase' in v[:200],
                '.gpx': lambda v: '<gpx' in v[:200],
                '.fit': lambda v: v[8:12]=='.FIT'}

p = argparse.ArgumentParser(description='''Uploads activities to Strava.''')
p.add_argument('activities', nargs='*', type=argparse.FileType("rb"), default=(stdin,),
               help="Activity files to upload (plain or gzipped {})".format(', '.join(allowed_exts)))
p.add_argument('-p', '--private', action='store_true', help='Make activities private')
p.add_argument('-P', '--no-popup', action='store_true', help="Don't browse to activities after upload.")
p.add_argument('-N', '--no-parse', action='store_true', help="Don't parse name/description fields from files.")
p.add_argument('-E', '--env', help='Look for ACCESS_TOKEN in environment variable rather than ~/.stravacli')
p.add_argument('-t', '--type', choices=allowed_exts, default=None,
               help='Force files to be interpreted as being of given type (default is to autodetect based on name, or contents for stdin')
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

while True:
    client = Client(cat)
    try:
        athlete = client.get_athlete()
    except requests.exceptions.ConnectionError:
        p.error("Could not connect to Strava API")
    except Exception as e:
        print("NOT AUTHORIZED", file=stderr)
        print("Need Strava API access token. Launching web browser to obtain one.", file=stderr)
        client = Client()
        authorize_url = client.authorization_url(client_id=cid, redirect_uri='http://stravacli-dlenski.rhcloud.com/auth', scope='view_private,write')
        webbrowser.open_new_tab(authorize_url)
        client.access_token = cat = raw_input("Enter access token: ")
    else:
        if not cp.has_section('API'):
            cp.add_section('API')
        if not 'ACCESS_TOKEN' in cp.options('API') or cp.get('API', 'ACCESS_TOKEN', None)!=cat:
            cp.set('API', 'ACCESS_TOKEN', cat)
            cp.write(open(os.path.expanduser('~/.stravacli'),"w"))
        break

print("Authorized to access account of {} {} (id {:d}).".format(athlete.firstname, athlete.lastname, athlete.id))

#####

for ii,f in enumerate(args.activities):
    if f is stdin:
        fn = 'stdin'
        contents = f.read()
        f = StringIO(contents)
        if args.type is None:
            # autodetect gzip and extension based on content
            if contents.startswith('\x1f\x8b'):
                gz, cf, uf = '.gz', f, gzip.GzipFile(fileobj=f, mode='rb')
                contents = uf.read()
            else:
                gz, uf, cf = '', f, NamedTemporaryFile(suffix='.gz')
                gzip.GzipFile(fileobj=cf, mode='w+b').writelines(f)
            for ext, checker in allowed_exts.items():
                if checker(contents):
                    print("Uploading {} activity from stdin...".format(ext+gz))
                    break
            else:
                p.error("Could not determine file type of stdin")
        else:
            base, ext = 'activity', args.type
    else:
        base, ext = os.path.splitext(f.name if args.type is None else 'activity.'+args.type)
        # autodetect based on extensions
        if ext.lower()=='.gz':
            base, ext = os.path.splitext(base)
            # un-gzip it in order to parse it
            gz, cf, uf = '.gz', f, None if args.no_parse else gzip.GzipFile(fileobj=f, mode='rb')
        else:
            gz, uf, cf = '', f, NamedTemporaryFile(suffix='.gz')
            gzip.GzipFile(fileobj=cf, mode='w+b').writelines(f)
        if ext.lower() not in allowed_exts:
            p.error("Don't know how to handle extension {} (allowed are {}).".format(ext, ', '.join(allowed_exts)))
        print("Uploading {} activity from {}...".format(ext+gz, f.name))

    # try to parse activity name, description from file if requested
    name = desc = None
    if not args.no_parse:
        uf.seek(0, 0)
        if ext.lower()=='.gpx':
            x = etree.parse(uf)
            nametag, desctag = x.find("{*}name"), x.find("{*}desc")
            name = nametag and nametag.text
            desc = desctag and desctag.text
        elif ext.lower()=='.tcx':
            x = etree.parse(uf)
            notestag = x.find("{*}Activities/{*}Activity/{*}Notes")
            if notestag is not None:
                name, desc = (notestag.text.split('\n',1)+[None])[:2]

    # upload activity
    try:
        cf.seek(0, 0)
        upstat = client.upload_activity(cf, ext[1:] + '.gz', name, desc, private=args.private)
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
