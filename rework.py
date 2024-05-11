import pickle

from flask import Flask, request, url_for, session, redirect, render_template
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from authlib.integrations.flask_client import OAuth
from spotipy.oauth2 import SpotifyOAuth
from flask_login import LoginManager
from Google import Create_Service
from dotenv import load_dotenv
import googleapiclient.errors
import googleapiclient.discovery
import google_auth_oauthlib
import pprint
import os
import spotipy
import time

load_dotenv()
login_manager = LoginManager()
redirect_back_to_spotify = False
google_logged_in = False
spotify_logged_in = False
return_to_sp_function = False
correct = False
flow = None

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
app.secret_key = os.getenv('APP_SECRET_KEY')
login_manager.init_app(app)


CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
CLIENT_FILE = 'client_secrets.json'
TOKEN_INFO = 'token_info'
REDIRECT_URI = 'http://127.0.0.1:5000/ytplaylistselect'
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/youtube',
                 'https://www.googleapis.com/auth/youtubepartner',
                 'https://www.googleapis.com/auth/youtube.force-ssl']
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


print(spotify_logged_in)


@login_manager.user_loader
@app.route('/')
def homepage():
    global return_to_sp_function, return_counter
    print('homepage')
    if return_to_sp_function is True:
        return redirect(url_for('select_pl_from_sp'))
    else:
        return render_template('mainscreen.html')


@app.route('/splogin')
def spotify_login():
    global spotify_logged_in, return_to_sp_function
    spotify_logged_in = True
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    print(auth_url)
    print(auth_url)
    return redirect(auth_url)


@app.route('/googlelogin')
def google_login():
    global flow
    Google = oauth.create_client('Google')
    redirect_uri = 'http://127.0.0.1:5000/authorize'
    return Google.authorize_redirect(redirect_uri)


@app.route('/authorize')
def authorize_function():
    global google_logged_in, token, flow, credentials, redirect_back_to_spotify
    Google = oauth.create_client('Google')
    raw_token = Google.authorize_access_token()
    session['user'] = raw_token
    credentials = raw_token
    access_token_cut = raw_token['access_token']
    google_logged_in = True
    if redirect_back_to_spotify is True:
        return redirect(url_for('select_pl_from_sp', _external=True))
    else:
        return redirect(url_for('select_pl_from_yt', _external=True))


@app.route('/ytplpicker', methods=['POST', 'GET'])
def select_pl_from_yt():
    global token_info, spotify_logged_in, pl_id, pl_wanted_name
    if google_logged_in is True and spotify_logged_in is True:
        while True:
            if request.method == 'POST':
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    'client_secrets.json', GOOGLE_SCOPES)
                credentials = flow.run_local_server()
                # print(credentials)
                with open('Oude files/credentials.pickle', 'wb') as credentialfile:
                    pickle.dump(credentials, credentialfile)
                youtube = googleapiclient.discovery.build(
                    'youtube', 'v3', credentials=credentials)
                sp_oauth = create_spotify_oauth()
                code = request.args.get('code')
                token_info = sp_oauth.get_access_token(code)
                session['token_info'] = token_info
                get_token()
                session.modified = True
                sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
                sp_counter = 0
                sp_playlist_counter = 1
                sp_playlists = []
                pl_wanted_name = request.form['playlist_wanted_name']
                playlist_name_request = sp.current_user_playlists()
                while True:
                    try:
                        playlist_name = playlist_name_request['items'][sp_playlist_counter]['name']
                        sp_playlist_counter += 1
                        sp_playlists.append(playlist_name)
                    except IndexError:
                        print(sp_playlists)
                        if pl_wanted_name not in sp_playlists:
                            break
                        else:
                            print('duplicate')
                            return redirect(url_for('select_pl_from_yt'))
                print('na while loop')
                pl_id = request.form['playlist_id']
                yt_pl_id_request = youtube.playlists().list(mine=True, part='snippet')
                yt_pl_id_response = yt_pl_id_request.execute()
                yt_playlists = []
                yt_playlist_counter = 0
                print('voor 1ste while')
                while True:
                    try:
                        yt_pl_id = yt_pl_id_response['items'][yt_playlist_counter]['id']
                        yt_playlist_counter += 1
                        yt_playlists.append(yt_pl_id)
                    except IndexError:
                        print(yt_playlists)
                        break
                if pl_id in yt_playlists:
                    print('in')
                    return redirect(url_for('create_sp_playlist'))
                else:
                    print('new_id')
                    return redirect(url_for('select_pl_from_yt'))
            else:
                return render_template('select_pl_from_yt_screen.html')
    else:
        print('else')
        if spotify_logged_in is False:
            print('rtsp')
            return redirect(url_for('spotify_login'))

        if google_logged_in is False:
            print('rtyt')
            print('yt_function')
            return redirect(url_for('google_login'))


@app.route('/createsppl')
def create_sp_playlist():
    global pl_wanted_name, pl_id, google_logged_in, spotify_logged_in, redirect_back_to_spotify\
        , token_info, credentials, song_uri
    # flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
    #     'client_secrets.json', GOOGLE_SCOPES)
    # credentials = flow.run_local_server()
    try:
        with open('Oude files/credentials.pickle', 'rb') as credentialfile:
            credentials = pickle.load(credentialfile)
    except:
        print('except')
    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
    sp_oauth = create_spotify_oauth()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    get_token()
    session.modified = True
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    get_user_id = sp.current_user()
    user_id = get_user_id['id']
    print(get_user_id)
    print('user id: ' + user_id)
    create_new_playlist = sp.user_playlist_create(user=user_id, name=pl_wanted_name, public=False)
    new_playlist_id = create_new_playlist['id']
    get_song_names_from_yt_pl = youtube.playlistItems().list(part='snippet', playlistId=pl_id, maxResults=50)
    get_song_names_from_yt_pl_response = get_song_names_from_yt_pl.execute()
    songcounter = 0
    while True:
        try:
            print('song_name')
            song_name = get_song_names_from_yt_pl_response['items'][songcounter]['snippet']['title']
            try:
                song_name_split = song_name.split('(')
                song_name_new = song_name_split[0]
                song_name = song_name_new
            except:
                pass
            print('voor_sp_song')
            sp_song = sp.search(q=song_name, type=['track', 'album'], limit=5)
            print('voor_song_uri')
            try:
                song_uri = sp_song['tracks']['items'][0]['uri']
            except IndexError:
                print(sp_song)
            print(song_name)
            add_song_to_sp_pl = sp.playlist_add_items(playlist_id=new_playlist_id, items=[song_uri])
            print('item added')
            songcounter += 1
            print('item deleted')
        except IndexError:
            print('songs transferred, song count: ' + str(songcounter))
            return redirect(url_for('homepage'))


@app.route('/spplpicker', methods=['POST', 'GET'])
def select_pl_from_sp():
    print('spl')
    global token_info, spotify_logged_in, pl_id, pl_wanted_name, redirect_back_to_spotify, google_logged_in, return_to_sp_function
    if google_logged_in is True and spotify_logged_in is True:
        sp_oauth = create_spotify_oauth()
        sp_counter = 0
        playlist_counter = 1
        session.clear()
        code = request.args.get('code')
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
        get_token()
        sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
        while True:
            if request.method == 'POST':
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    'client_secrets.json', GOOGLE_SCOPES)
                credentials = flow.run_local_server()
                # print(credentials)
                with open('Oude files/credentials.pickle', 'wb') as credentialfile:
                    pickle.dump(credentials, credentialfile)
                youtube = googleapiclient.discovery.build(
                    'youtube', 'v3', credentials=credentials)
                print('after_credentials')
                spplaylistids = []
                pl_wanted_name = request.form['yt_playlist_wanted_name']
                print("4")
                session.modified = True
                yt_pl_name_request = youtube.playlists().list(mine=True, part='snippet')
                yt_pl_name_response = yt_pl_name_request.execute()
                print("5")
                yt_playlists = []
                while True:
                    try:
                        playlist_name = yt_pl_name_response['items'][playlist_counter]['snippet']['title']
                        playlist_counter += 1
                        yt_playlists.append(playlist_name)
                    except IndexError:
                        print(yt_playlists)
                        if pl_wanted_name not in yt_playlists:
                            print('new_name')
                            break
                        else:
                            print('duplicate')
                            return redirect(url_for('select_pl_from_sp'))
                pl_id = request.form['sp_playlist_id']
                sp_playlists = []
                sp_pl_id_request = sp.current_user_playlists()
                sp_playlist_counter = 0
                while True:
                    try:
                        sp_pl_id = sp_pl_id_request['items'][sp_playlist_counter]['id']
                        sp_playlist_counter += 1
                        sp_playlists.append(sp_pl_id)
                    except IndexError:
                        print(sp_playlists)
                        break
                if pl_id in sp_playlists:
                    print('in')
                    return redirect(url_for('create_yt_playlist'))
                else:
                    print('new_id')
                    return redirect(url_for('select_pl_from_sp'))
            else:
                return render_template('select_pl_from_sp_screen.html')
    else:
        print('else')
        if spotify_logged_in is False:
            print('rtsp')
            return_to_sp_function = True
            return redirect(url_for('spotify_login'))

        if google_logged_in is False:
            print('rtyt')
            redirect_back_to_spotify = True
            return redirect(url_for('google_login'))


@app.route('/createytpl')
def create_yt_playlist():
    global pl_wanted_name, pl_id, google_logged_in, spotify_logged_in, redirect_back_to_spotify\
        , token_info, credentials, song_uri
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        'client_secrets.json', GOOGLE_SCOPES)
    try:
        with open('Oude files/credentials.pickle', 'rb') as credentialfile:
            credentials = pickle.load(credentialfile)
    except:
        print('except')
    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
    sp_oauth = create_spotify_oauth()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    get_token()
    session.modified = True
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    get_user_id = sp.current_user()
    user_id = get_user_id['id']
    sp_counter = 0
    new_yt_pl_request = youtube.playlists().insert(
        part="snippet,contentDetails",
        body={
            "snippet": {
                "title": pl_wanted_name
            }
        }
    )
    new_yt_pl_response = new_yt_pl_request.execute()
    new_playlist_id = new_yt_pl_response['id']
    while True:
        try:
            spotify_song_names_request = sp.playlist_items(playlist_id=pl_id, fields=None)
            spotify_song_name = spotify_song_names_request['items'][sp_counter]['track']['name']
            track_artist = spotify_song_names_request['items'][sp_counter]['track']['artists'][0]['name']
            spotify_search_q = str(track_artist) + ' - ' + str(spotify_song_name)
            pprint.pprint(track_artist)
            search_song_request = youtube.search().list(part='snippet', type='video', maxResults=1, q=spotify_search_q)
            search_results = search_song_request.execute()
            search_result_id = search_results['items'][0]['id']['videoId']
            # full_search_result = str()
            insert_yt_song = youtube.playlistItems().insert(part='snippet,contentDetails', body={
                "snippet": {
                    "playlistId": new_playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": search_result_id
                    }
                }
            })
            insert_yt_song.execute()
            sp_counter += 1
            pprint.pprint('song added: ' + spotify_song_name)
        except IndexError:
            print('except triggered')
            return redirect(url_for('homepage'))
    # songcounter = 0
    # while True:
    #     try:
    #         print('song_name')
    #         song_name = get_song_names_from_yt_pl_response['items'][songcounter]['snippet']['title']
    #         try:
    #             song_name_split = song_name.split('(')
    #             song_name_new = song_name_split[0]
    #             song_name = song_name_new
    #         except:
    #             pass
    #         print('voor_sp_song')
    #         sp_song = sp.search(q=song_name, type=['track', 'album'], limit=5)
    #         print('voor_song_uri')
    #         try:
    #             song_uri = sp_song['tracks']['items'][0]['uri']
    #         except IndexError:
    #             print(sp_song)
    #         print(song_name)
    #         add_song_to_sp_pl = sp.playlist_add_items(playlist_id=new_playlist_id, items=[song_uri])
    #         print('item added')
    #         songcounter += 1
    #         print('item deleted')
    #     except IndexError:
    #         print('songs transferred, song count: ' + str(songcounter))
    #         return redirect(url_for('homepage'))


def get_token():
    global token_info
    token_valid = False
    if not token_valid:
        token_info = session.get('token_info')
        # print('token_not_valid')
        # loginredirection()

    if not session.get('token_info', False):
        token_valid = False
        token_info = session.get('token_info')
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
        redirect_uri=url_for('select_pl_from_sp', _external=True),
        scope=['playlist-read-collaborative', 'user-read-private', 'user-read-email', 'playlist-modify-private', 'playlist-read-private'],
    )


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
    