# stravacli
Command-line client for Strava

## Requirements

Uses [`hozn/stravalib`](http://github.com/hozn/stravalib) to interact
with Strava using its [REST-based API v3](http://strava.github.io/api/v3).

## Application authorization

Authorizing a command-line application to use the Strava API is quite
tedious; their API is clearly geared towards web-based apps running on
a central server.

(If you run a `stravacli` utility without an access token in `~/.stravacli` already,
it will automatically direct you to step 2 below.)

1. If you already have a Strava API [`access token`](http://strava.github.io/api/v3/oauth/#post-token), skip to step 3.
2. If not, go to [the simple web app I'm running on OpenShift](//stravacli-dlenski.rhcloud.com), which will handle the OAuth process and present you with your `access_token`. (The web app does **not** retain or store your access token in any way.)
3. Put the access token in `~/.stravacli` as directed: ![Image](http://snag.gy/jJZcF.jpg)

### `server` branch
The `server` branch of this program will allow you to roll-your-own API access tokens without depending on my OpenShift web app. First, you must get your own Strava API key from: [http://www.strava.com/settings/api]

With that done, you'll need to add your `client_id` and `client_secret` values to `~/.stravacli`:
````ini
[API]
client_id = 1234
client_secret = f00f00f00f00f00f00f00f00f00f00f00f00f00f
```

The first time you run [`stravaup`](#stravaup), it will launch a web
browser to display Strava's application authorization page, and a
small web server on `localhost` to capture the authorization code output
from that page. (See
[`QueryGrabber.py`](http://github.com/dlenski/stravacli/blob/server/QueryGrabber.py)
for the implementation of this very minimal web server.)

## <a name="stravaup">Uploading activities</a>

````bash
$ stravaup.py [OPTIONS] activity files
````

Activity files must have TCX, GPX, or FIT extensions (or same followed
by `.gz`). Files will be automatically compressed with `gzip` &mdash; if not
already in compressed format &mdash; to reduce upload time.

By default, the program will look for top-level
[`<name>`](http://www.topografix.com/gpx_manual.asp#name) and
[`<desc>`](http://www.topografix.com/gpx_manual.asp#desc) tags in GPX
files, and use those for the Strava activity name and description. In
TCX files, it looks for the `<Activity><Notes>` tag and [uses the first
line from that field for the activity name, and subsequent lines for
the activity description](https://github.com/cpfair/tapiriik/issues/99).
This behavior may be disabled with `-N`/`--no-parse`.

Activities will be uploaded to Strava and opened in your desktop web
browser (unless `-P`/`--no-popup` is specified).

Options:

    -p, --private      Make activities private
    -P, --no-popup     Don't browse to activities after upload.
    -N, --no-parse     Don't parse name/description fields from files.
    -E ENV, --env ENV  Look for (CLIENT_ID, CLIENT_SECRET) or ACCESS_TOKEN in
                       environment variables rather than ~/.stravacli
