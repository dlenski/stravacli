# stravacli
Command-line clients for Strava

## Installation

Requires Python 3. Uses [`hozn/stravalib`](//github.com/hozn/stravalib) to interact with Strava using its [REST-based API v3](//strava.github.io/api/v3),
and optionally [`pR0Ps/stravaweblib`](//github.com/pR0Ps/stravaweblib) to download activities.

Install with:

```
$ pip3 install https://github.com/dlenski/stravacli/archive/master.zip
...
$ stravaup
usage: stravaup [-h] [-c] [-P] [-E ENV] [-p] [-t {.tcx,.gpx,.fit}] [-x]
                [-T TITLE] [-D DESCRIPTION] [-A ACTIVITY_TYPE]
                [activities [activities ...]]
stravaup: error: specify either activity files or -c/--stdin (but not both)

$ usage: stravadown [-h] [-t {tcx,gpx,original}] [-N] [-E ENV]
                    [-c | -d DIRECTORY]
                    activities [activities ...]
stravadown: error: the following arguments are required: activities
```

## Application authorization

Authorizing a command-line application to use the Strava API is somewhat
tedious; their API is geared towards web-based apps running on a central
server.

(If you run a `stravacli` utility without an access token in `~/.stravacli`
already, it will direct you to this README.)

1. If you already have a Strava API [`access token`](//strava.github.io/api/v3/oauth/#post-token), put it in `~/.stravacli`:
```ini
[API]
access_token = f00f00f00f00f00f00f00f00f00f00f00f00f00f
```
2. If not, create your own Strava API application ([here](https://www.strava.com/settings/api)) or use one that you already
   have, and put the application's client ID and secret in `~/.stravacli`:
```ini
[API]
client_id = 1234
client_secret = f00f00f00f00f00f00f00f00f00f00f00f00f00f
```
3. Strava's REST-based API does not allow downloading activity files, so it must be augmented with web-based scraping. For
this, [`pR0Ps/stravaweblib`](//github.com/pR0Ps/stravaweblib) must be installed, and you must
also put your registered email address and base64-encoded password in `~/.stravacli`:
```ini
[Web]
email = my.name@me.com
password_b64 = cGFzc3dvcmQ=
```

  The first time you run [`stravaup`](#uploading-activities) or [`stravadown`](#downloading-activities),
  it will launch a web
  browser to display Strava's application authorization page, and a
  small web server on `localhost` to capture the authorization code output
  from that page. (See [`QueryGrabber.py`](//github.com/dlenski/stravacli/blob/server/QueryGrabber.py)
  for the implementation of this very minimal web server.)

## Uploading activities

```bash
$ stravaup [OPTIONS] [activity files]
```

Activity files must have TCX, GPX, or FIT extensions (or same followed
by `.gz`). Files will be automatically compressed with `gzip` —
if not already in such format — to reduce upload time. If no
activity files are specified, the default is to read from `stdin`, so
`stravaup` can be used as a pipe, and to autodetect the file type
based on its contents.

If `-x`/`--xml-desc` is specified, the program will look for top-level
[`<name>`](//www.topografix.com/gpx_manual.asp#name) and
[`<desc>`](//www.topografix.com/gpx_manual.asp#desc) tags in GPX
files, and use those for the Strava activity title and description. In
TCX files, it looks for the `<Activity><Notes>` tag and [uses the first
line from that field for the activity name, and subsequent lines for
the activity description](//github.com/cpfair/tapiriik/issues/99).

You can also specify title and description from the command line with
the `-T`/`--title` and `-D`/`--desc` options.

Activities will be uploaded to Strava and opened in your desktop web
browser (unless `-P`/`--no-popup` is specified).

### Options

```
usage: stravaup [-h] [-c] [-P] [-E ENV] [-p] [-t {.tcx,.gpx,.fit}] [-x]
                [-T TITLE] [-D DESCRIPTION] [-A ACTIVITY_TYPE]
                [activities [activities ...]]

Uploads activities to Strava.

positional arguments:
  activities            Activity files to upload (plain or gzipped .tcx, .gpx,
                        .fit)

optional arguments:
  -h, --help            show the help message and exit
  -c, --stdin           Read activity file from standard input
  -P, --no-popup        Don't browse to activities after upload.
  -E ENV, --env ENV     Look for ACCESS_TOKEN in environment variable rather
                        than ~/.stravacli

Activity file details:
  -p, --private         Make activities private
  -t {.tcx,.gpx,.fit}, --type {.tcx,.gpx,.fit}
                        Force files to be interpreted as being of given type
                        (default is to autodetect based on name, or contents
                        for stdin)
  -x, --xml-desc        Parse name/description fields from GPX and TCX files.
  -T TITLE, --title TITLE
                        Activity title
  -D DESCRIPTION, --desc DESCRIPTION
                        Activity description
  -A ACTIVITY_TYPE, --activity-type ACTIVITY_TYPE
                        Type of activity. If not specified, the default value
                        is taken from user profile. Supported values: ride,
                        run, swim, workout, hike, walk, nordicski, alpineski,
                        backcountryski, iceskate, inlineskate, kitesurf,
                        rollerski, windsurf, workout, snowboard, snowshoe
```

## Downloading activities

```bash
$ stravadown [OPTIONS] [activity IDs]
```

This will download activity files from Strava. By default, it will
download them in the same format they were originally uploaded, but
TCX or GPX format may also be requested with `-t tcx` or `-t gpx`.

It is generally only possible to download your _own_ activities, not
activities recorded by other athletes, but the `--scrape` option
_may_ allow you to circumvent this in some cases.

### Options

```
usage: stravadown [-h] [-t {tcx,gpx,original}] [-N] [-c | -d DIRECTORY]
                  activities [activities ...]

Downloads activities from Strava.

positional arguments:
  activities            Activity IDs to download

optional arguments:
  -h, --help            show this help message and exit
  -t {tcx,gpx,original}, --type {tcx,gpx,original}
                        Format in which to download activities (default is
                        their original format
  -s, --scrape          Use HTML scrape-based method to download activities
                        (will allow you to download activities other than your
                        own)
  -N, --number          Label activity files by number, rather than by their
                        titles
  -E ENV, --env ENV     Look for ACCESS_TOKEN in environment variable rather
                        than ~/.stravacli
  -c, --stdout          Write activity to standard input
  -d DIRECTORY, --directory DIRECTORY
                        Directory in which to store activity files (default is
                        current directory)
```
