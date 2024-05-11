
from flask import Flask, request, url_for, session, redirect, render_template
from authlib.integrations.flask_client import OAuth
from spotipy.oauth2 import SpotifyOAuth
from flask_login import LoginManager
from Google import Create_Service
from dotenv import load_dotenv
import googleapiclient.errors
import googleapiclient.discovery
import pprint
import os
import spotipy
import time

load_dotenv()
login_manager = LoginManager() 
redirect_back_to_spotify = False
google_logged_in = False
spotify_logged_in = False
correct = False

counter = 0

token_info = ''
pl_id = ''
pl_wanted_name = ''
token = ''

ids = []

app = Flask(__name__)
app.config['SESSION_COOKIE_NAME'] = 'Cookies'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_MAX_AGE_DEFAULT'] = 0
login_manager.init_app(app)

app.secret_key = os.getenv('APP_SECRET_KEY')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
CLIENT_FILE = '../client_secrets.json'
TOKEN_INFO = 'token_info'
REDIRECT_URI = 'http://127.0.0.1:5000/ytplaylistselect'
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/youtube',
                 'https://www.googleapis.com/auth/youtubepartner',
                 'https://www.googleapis.com/auth/youtube.force-ssl']
# GOOGLE_SCOPES = ['https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtubepartner https://www.googleapis.com/auth/youtube.force-ssl']
YT_DEV_KEY = None

oauth = OAuth(app)
Google = oauth.register(
    name='Google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params={'access_type': 'offline'},
    api_base_url='https://www.googleapis.com/youtube/v3',
    client_kwargs={
        'prompt': 'consent',
        'scope': 'https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.readonly'
                 '  https://www.googleapis.com/auth/youtubepartner-channel-audit'})


@login_manager.user_loader
@app.route('/')
def homepage():
    return render_template('mainscreen.html')


@app.route('/splogin')
def spotify_login():
    global spotify_logged_in
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    spotify_logged_in = True
    print(auth_url)
    return redirect(auth_url)


@app.route('/spplaylistselect', methods=['POST', 'GET'])
def sp_playlist_select():
    global token_info, spotify_logged_in, pl_id, pl_wanted_name
    if spotify_logged_in is True:

        if request.method == 'POST':
            youtube = Create_Service(CLIENT_FILE, 'youtube', 'v3', GOOGLE_SCOPES)
            sp_oauth = create_spotify_oauth()
            sp_counter = 0
            playlist_counter = 1
            session.clear()
            code = request.args.get('code')
            token_info = sp_oauth.get_access_token(code)
            session['token_info'] = token_info
            get_token()
            sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
            spplaylistids = []
            pl_id = request.form['playlist_id']
            pl_wanted_name = request.form['playlist_wanted_name']
            yt_playlists = []

            while True:
                try:
                    playlist_name_request = youtube.playlists().list(mine=True, part='snippet')
                    playlist_name_execution = playlist_name_request.execute()
                    playlist_name = playlist_name_execution['items'][playlist_counter]['snippet']['title']
                    playlist_counter += 1
                    yt_playlists.append(playlist_name)
                except IndexError:
                    print(yt_playlists)
                    if pl_wanted_name in yt_playlists:
                        print('duplicate')
                        return redirect(url_for('sp_playlist_select'))
                    else:
                        break
            all_playlists = sp.current_user_playlists()

            while True:
                try:
                    sp_playlist = all_playlists['items'][sp_counter]['id']
                    spplaylistids.append(sp_playlist)
                    sp_counter += 1
                except IndexError:
                    print(spplaylistids)
                    break

            if pl_id in spplaylistids:
                return redirect(url_for('transfer_to_yt', _external=True))
            else:
                print('else')
                return redirect(url_for('sp_playlist_select', _external=True))
        else:
            return render_template('select_pl_from_yt_screen.html')
    else:
        return redirect(url_for('spotify_login', _external=True))


@app.route('/transfertoyt')
def transfer_to_yt():
    global pl_wanted_name, pl_id, google_logged_in, spotify_logged_in, redirect_back_to_spotify, token_info
    if google_logged_in is True and spotify_logged_in is True:
        youtube = googleapiclient.discovery.build('youtube', 'v3', credentials)
        sp_oauth = create_spotify_oauth()
        sp_counter = 0
        session.clear()
        code = request.args.get('code')
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
        get_token()
        sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
        create_yt_pl_task = youtube.playlists().insert(part='snippet', body={
            'snippet': {
                'title': pl_wanted_name
            },
            'status': {
                'privacyStatus': 'private'
            }
        })
        create_yt_pl_task.execute()
        print('playlist_created')
        while True:
            try:
                spotify_song_names_request = sp.playlist_items(playlist_id=pl_id, fields=None)
                spotify_song_name = spotify_song_names_request['items'][sp_counter]['track']['name']
                sp_counter += 1
                pprint.pprint(spotify_song_name)
            except IndexError:
                print('except triggered')
                return redirect(url_for('homepage'))
    elif google_logged_in is not True:
        redirect_back_to_spotify = True
        return redirect(url_for('google_login'))
    elif spotify_logged_in is not True:
        return redirect(url_for('spotify_login'))
    else:
        pass


@app.route('/googlelogin')
def google_login():
    global flow
    Google = oauth.create_client('Google')
    redirect_uri = 'http://127.0.0.1:5000/authorize'
    return Google.authorize_redirect(redirect_uri)


@app.route('/authorize')
def authorize_function():
    global google_logged_in, token, flow, credentials
    Google = oauth.create_client('Google')
    raw_token = Google.authorize_access_token()
    resp = oauth.Google.get('user_info')
    # user_info = resp.json()
    # session['user'] = raw_token
    credentials = raw_token
    # access_token_cut = raw_token['access_token']
    print(raw_token)
    google_logged_in = True

    return redirect(url_for('yt_playlist_select', _external=True))


@app.route('/ytplaylistselect', methods=['POST', 'GET'])
def yt_playlist_select():
    global redirect_back_to_spotify
    if google_logged_in is True:
        if redirect_back_to_spotify is True:
            return redirect(url_for('transfer_to_yt'))
        if request.method == 'POST':
            playlist_request_counter = 0
            playlist_ids = []
            youtube = Create_Service(CLIENT_FILE, 'youtube', 'v3', GOOGLE_SCOPES)
            playlist_list_request = youtube.playlists().list(mine=True, part='snippet')
            playlist_reponse = playlist_list_request.execute()
            youtube_playlist_input = request.form['youtube_playlist_id']
            while True:
                try:
                    playlist_id = playlist_reponse['items'][playlist_request_counter]['id']
                    playlist_request_counter += 1
                    playlist_ids.append(playlist_id)
                except IndexError:
                    # print('except triggered, list of id\'s' + str(playlist_ids))
                    if youtube_playlist_input in playlist_ids:
                        # print('in_list')
                        return redirect(url_for('homepage', _external=True))
                    else:
                        # print('not_in_playlist')
                        return redirect(url_for('yt_playlist_select', _external=True))
        else:
            return render_template('select_pl_from_sp_screen.html')

    else:
        return redirect(url_for('google_login', _external=True))


@app.route('/main')
def mainpage():
    global token_info
    if 'logged_in' in session:
        global counter
        song_count = 1
        sp_oauth = create_spotify_oauth()
        session.clear()
        code = request.args.get('code')
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
        get_token()
        session.modified = True
        sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
        while True:
            playlists = sp.playlist_items(playlist_id='4P4zM5fXhERrbc40dLWCIp',
                                          limit=100, offset=0)
            try:
                pprint.pprint(str(song_count) + '. ' + playlists['items'][song_count]['track']['name'])
                song_count += 1

            except IndexError:
                sp_playlist_select()
                break
        return str(playlists)
    else:
        return redirect(url_for('spotify_login', _external=True))


def get_token():
    global token_info
    token_valid = False
    if not token_valid:
        token_info = session.get('token_info', {})

    if not session.get('token_info', False):
        token_valid = False
        print('token_session_thing')
        return token_info, token_valid

    now = int(time.time())
    is_expired = session.get('token_info').get('expires_at') - now < 60
    if is_expired:
        sp_oauth = create_spotify_oauth()
        print('token_expired')
        token_info = sp_oauth.refresh_access_token(session.get('token_info').get('refresh_token'))
    token_valid = True
    return token_info, token_valid


def create_spotify_oauth():
    return SpotifyOAuth(
        client_id='ffdb071c081b4cbe880dfe549167e244',
        client_secret='206ce55f95f74a1099d7770b0311354b',
        redirect_uri=url_for('sp_playlist_select', _external=True),
        scope=['playlist-read-collaborative', 'user-read-private', 'user-read-email'],
    )


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
