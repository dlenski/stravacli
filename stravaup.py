#!/usr/bin/env python3

from stravalib import Client, exc
from sys import stderr, stdin
from tempfile import NamedTemporaryFile
import webbrowser, os.path, configparser, gzip
import argparse
from io import BytesIO
import requests
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

#####

def main(args=None):
    allowed_exts = {'.tcx': lambda v: b'<TrainingCenterDatabase' in v[:200],
                    '.gpx': lambda v: b'<gpx' in v[:200],
                    '.fit': lambda v: v[8:12]==b'.FIT'}

    p = argparse.ArgumentParser(description='''Uploads activities to Strava.''')
    p.add_argument('activities', nargs='*', type=argparse.FileType("rb"),
                   help="Activity files to upload (plain or gzipped {})".format(', '.join(allowed_exts)))
    p.add_argument('-c', '--stdin', action='store_true', help="Read activity file from standard input")
    p.add_argument('-P', '--no-popup', action='store_true', help="Don't browse to activities after upload.")
    p.add_argument('-E', '--env', help='Look for ACCESS_TOKEN in environment variable rather than ~/.stravacli')
    g = p.add_argument_group('Activity file details')
    g.add_argument('-p', '--private', action='store_true', help='Make activities private')
    g.add_argument('-t', '--type', choices=allowed_exts, default=None,
                   help='Force files to be interpreted as being of given type (default is to autodetect based on name, or contents for stdin)')
    g.add_argument('-x', '--xml-desc', action='store_true', help="Parse name/description fields from GPX and TCX files.")
    g.add_argument('-T', '--title', help='Activity title')
    g.add_argument('-D', '--desc', dest='description', help='Activity description')
    g.add_argument('-A', '--activity-type', default=None, help='''Type of activity. If not specified, the default value is taken
                                                                  from user profile. Supported values:
                                                                  ride, run, swim, workout, hike, walk, nordicski, alpineski,
                                                                  backcountryski, iceskate, inlineskate, kitesurf, rollerski,
                                                                  windsurf, workout, snowboard, snowshoe''')
    args = p.parse_args(args)

    if (args.activities and args.stdin) or (not args.activities and not args.stdin):
        p.error('specify either activity files or -c/--stdin (but not both)')
    elif args.stdin:
        args.activities = (stdin.buffer,)
    if args.xml_desc:
        if args.title:
            p.error('argument -T/--title not allowed with argument -x/--xml-desc')
        if args.description:
            p.error('argument -D/--desc not allowed with argument -x/--xml-desc')

    #####

    # Authorize Strava

    cid = 3163 # CLIENT_ID
    if args.env:
        cat = os.environ.get('ACCESS_TOKEN')
    else:
        cp = configparser.ConfigParser()
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
                with open(os.path.expanduser('~/.stravacli'),"w") as cf:
                    cp.write(cf)
            break

    print("Authorized to access account of {} {} (id {:d}).".format(athlete.firstname, athlete.lastname, athlete.id))

    #####

    for ii,f in enumerate(args.activities):
        if f is stdin.buffer:
            fn = 'stdin'
            contents = f.read()
            f = BytesIO(contents)
            if args.type is None:
                # autodetect gzip and extension based on content
                if contents.startswith(b'\x1f\x8b'):
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
            ext = ext.lower()
            # autodetect based on extensions
            if ext=='.gz':
                base, ext = os.path.splitext(base)
                ext = ext.lower()
                # un-gzip it in order to parse it
                gz, cf, uf = '.gz', f, None if args.no_parse else gzip.GzipFile(fileobj=f, mode='rb')
            else:
                gz, uf, cf = '', f, NamedTemporaryFile(suffix='.gz')
                gzip.GzipFile(fileobj=cf, mode='w+b').writelines(f)
            if ext not in allowed_exts:
                p.error("Don't know how to handle extension {} (allowed are {}).".format(ext, ', '.join(allowed_exts)))
            print("Uploading {} activity from {}...".format(ext+gz, f.name))

        # try to parse activity name, description from file if requested
        if args.xml_desc:
            uf.seek(0, 0)
            if ext=='.gpx':
                x = etree.parse(uf)
                nametag, desctag = x.find("{*}name"), x.find("{*}desc")
                title = nametag and nametag.text
                desc = desctag and desctag.text
            elif ext=='.tcx':
                x = etree.parse(uf)
                notestag = x.find("{*}Activities/{*}Activity/{*}Notes")
                if notestag is not None:
                    title, desc = (notestag.text.split('\n',1)+[None])[:2]
        else:
            title = args.title
            desc = args.description

        # upload activity
        try:
            cf.seek(0, 0)
            upstat = client.upload_activity(cf, ext[1:] + '.gz', title, desc, private=args.private, activity_type=args.activity_type)
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

if (__name__ == '__main__'):
    main()
