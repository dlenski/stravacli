#!/usr/bin/env python3

import configparser
from binascii import a2b_base64
import requests
import os.path
import webbrowser
from sys import stderr
try:
    from stravaweblib import WebClient
except ImportError:
    WebClient = None
from stravalib import Client, exc

from .QueryGrabber import QueryGrabber


def get_authorized_client(access_token=None, need_web_client=True):
    cs = cid = cat = cat_exp = crt = email = password = None
    if access_token:
        cat = access_token
    else:
        cp = configparser.ConfigParser()
        cp.read(os.path.expanduser('~/.stravacli'))
        if cp.has_section('API'):
            cid = cp.get('API', 'CLIENT_ID', fallback=None)
            cs = cp.get('API', 'CLIENT_SECRET', fallback=None)
            cat = cp.get('API', 'ACCESS_TOKEN', fallback=None)
            crt = cp.get('API', 'REFRESH_TOKEN', fallback=None)
        if cp.has_section('Web'):
            email = cp.get('Web', 'EMAIL', fallback=None)
            password_b64 = cp.get('Web', 'PASSWORD_B64', fallback=None)
            if password_b64:
                password = a2b_base64(password_b64).decode()

    if need_web_client:
        if not WebClient:
            raise RuntimeError("Could not import stravaweblib.WebClient")
        elif not (email and password):
            raise RuntimeError("You need to add your Strava web credentials (Web.EMAIL and Web.PASSWORD_B64) to ~/.stravacli.")

    while True:
        client = Client(cat)

        try:
            client.get_athlete()
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError("Could not connect to Strava API") from e
        except exc.AccessUnauthorized as e:
            if cid and cs:
                if crt:
                    print("Refreshing Strava API access_token for client_id=%s." % cid, file=stderr)
                    token = client.refresh_access_token(client_id=cid, client_secret=cs, refresh_token=crt)
                elif cid and cs:
                    print("Launching web browser to obtain Strava API access_token for client_id=%s." % cid, file=stderr)
                    webserver = QueryGrabber(response='<title>Strava auth code received!</title>This window can be closed.')
                    authorize_url = client.authorization_url(client_id=cid, redirect_uri=webserver.root_uri(), scope=['activity:read_all', 'activity:write'])
                    webbrowser.open_new_tab(authorize_url)
                    webserver.handle_request()
                    token = client.exchange_code_for_token(client_id=cid, client_secret=cs, code=webserver.received['code'])
                cat, crt = token['access_token'], token['refresh_token']
                print("Got access token and refresh token.", file=stderr)
            elif cat:
                raise RuntimeError("Your Strava API access_token was not accepted. Try generating a new one. See details at:\n"
                                   "    https://github.com/dlenski/stravacli/blob/master/README.md", file=stderr) from e
            else:
                raise RuntimeError("You need to add either a Strava API access_token, or application client_id/client_secret\n"
                                   "pair, to ~/.stravacli. Details at:\n"
                                   "    https://github.com/dlenski/stravacli/blob/master/README.md") from e

        if need_web_client:
            try:
                client = WebClient(cat, email=email, password=password)
            except exc.LoginFailed as e:
                raise RuntimeError("Website credentials were not accepted. Check Web.EMAIL and Web.PASSWORD_B64 in ~/.stravacli.") from e
            except exc.AccessUnauthorized as e:
                raise RuntimeError("Website credentials were accepted, but Strava API token wasn't. Something is wrong.") from e

        if cat or crt:
            rewrite = False
            if not cp.has_section('API'):
                cp.add_section('API')
                rewrite = True
            if cat and 'ACCESS_TOKEN' not in cp.options('API') or cp.get('API', 'ACCESS_TOKEN', fallback=None) != cat:
                cp.set('API', 'ACCESS_TOKEN', cat)
                rewrite = True
            if crt and 'REFRESH_TOKEN' not in cp.options('API') or cp.get('API', 'REFRESH_TOKEN', fallback=None) != crt:
                cp.set('API', 'REFRESH_TOKEN', crt)
                rewrite = True
            if rewrite:
                with open(os.path.expanduser('~/.stravacli'), "w") as cf:
                    cp.write(cf)
            return client
