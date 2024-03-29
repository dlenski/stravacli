#!/usr/bin/env python3

from sys import stderr, stdout
import argparse
import os

from stravaweblib import DataFormat
from stravalib import exc
from .client_helper import get_authorized_client

#####


def main(args=None):
    p = argparse.ArgumentParser(description='''Downloads activities from Strava.''')
    p.add_argument('activities', nargs='+', type=int,
                   help="Activity IDs to download")
    p.add_argument('-t', '--type', type=str.lower, choices=('tcx', 'gpx', 'original'), default='original',
                   help='Format in which to download activities (default is their original format')
    p.add_argument('-N', '--number', action='store_true',
                   help='Label activity files by number, rather than by their titles')
    p.add_argument('-s', '--scrape', action='store_true',
                   help='Use HTML scrape-based method to download activities (will allow you to download activities other than your own)')
    p.add_argument('-E', '--env', help='Look for ACCESS_TOKEN in environment variable rather than ~/.stravacli')
    x = p.add_mutually_exclusive_group()
    x.add_argument('-c', '--stdout', action='store_true', help="Write activity to standard input")
    x.add_argument('-d', '--directory', default='',
                   help="Directory in which to store activity files (default is current directory)")
    args = p.parse_args(args)

    if args.stdout and len(args.activities) != 1:
        p.error('specify only one activity with -c/--stdout')

    fmt = getattr(DataFormat, args.type.upper())
    scrape_fmt = DataFormat.TCX if fmt == DataFormat.ORIGINAL else fmt

    #####
    # Authorize Strava client
    #####

    try:
        client = get_authorized_client(os.environ.get('ACCESS_TOKEN'), need_web_client=True)
    except RuntimeError as e:
        p.error(e.args[0])

    athlete = client.get_athlete()
    print("Authorized to access account of {} {} (id {:d}).".format(athlete.firstname, athlete.lastname, athlete.id))

    #####

    for ii, activity_id in enumerate(args.activities):
        uri = "http://strava.com/activities/{:d}".format(activity_id)

        try_scrape = args.scrape
        if not try_scrape:
            try:
                af = client.get_activity_data(activity_id, fmt)
            except exc.Fault as e:
                words = e.args[0].split()
                if words[:3] == ['Status', 'code', "'404'"]:
                    print("WARNING: Activity {} not found (check {}).".format(activity_id, uri), file=stderr)
                    continue
                elif words[:3] == ['Status', 'code', "'302'"]:
                    print("WARNING: Not allowed to download activity {}; switching to web-scrape.".format(activity_id, uri), file=stderr)
                    try_scrape = True
                else:
                    raise

        if try_scrape:
            af = client.scrape_activity_data(activity_id, scrape_fmt)

        if args.stdout:
            f = stdout.buffer
        else:
            if args.number:
                filename = str(activity_id) + os.path.splitext(af.filename)[1]
            else:
                filename = af.filename
            f = open(os.path.join(args.directory, filename), "wb")

        with f:
            f.writelines(af.content)

        # show results
        print("  Wrote {} from {}".format(f.name, uri), file=stderr)


if __name__ == '__main__':
    main()
