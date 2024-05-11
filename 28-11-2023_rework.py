# import pickle
from flask import Flask, request, url_for, session, redirect, render_template
from google_auth_oauthlib.flow import InstalledAppFlow  #, Flow
from authlib.integrations.flask_client import OAuth
from spotipy.oauth2 import SpotifyOAuth
from flask_login import LoginManager
from youtube_search import YoutubeSearch
# from Google import Create_Service
from dotenv import load_dotenv
import googleapiclient.errors
import googleapiclient.discovery
import google_auth_oauthlib
import ytmusicapi
# import pprint
import os
import spotipy
import time

# import setups
load_dotenv()
login_manager = LoginManager()
yt_api_unofficial = ytmusicapi.YTMusic()

# Flask setup
app = Flask(__name__)
app.config['SESSION_COOKIE_NAME'] = 'Cookies'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.getenv('APP_SECRET_KEY')
login_manager.init_app(app)

# Google/Youtube setup
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

# Google/Youtube Oauth setup
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

# Variables
redirect_back_to_spotify = False
return_to_sp_function = False
spotify_logged_in = False
google_logged_in = False
correct = False
sp_oauth = None
platform = None
flow = None

pl_wanted_name = ''
token_info = ''
pl_id = ''
token = ''

counter = 0

ids = []


# Start pagina, gebeurt niks speciaals op.
@login_manager.user_loader
@app.route('/')
def homepage():
    return render_template('new_main.html')


# Pagina om na inlog op spotify door te redirecten naar de get playlist paginas
@app.route('/redirect')
def redirect_page():
    print('0')
    if platform == 'to_spotify':
        print('1')
        return redirect(url_for('get_yt_playlist'))
    else:
        print('2')
        return redirect(url_for('get_sp_playlist'))


# Functie voor playlists naar spotify transferen, stuurt door naar google login
@app.route('/tospotify')
def to_spotify():
    global platform
    platform = 'to_spotify'
    return redirect(url_for('spotify_login'))


# Pagina die al je youtube playlists ids verzmelt, als de geniputte id hierin zit begin dan met transferen
@app.route('/getyoutubeplaylist', methods=['GET', 'POST'])
def get_yt_playlist():
    create_flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        'client_secrets.json', GOOGLE_SCOPES)
    credentials = create_flow.run_local_server()
    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
    playlist_request = youtube.playlists().list(mine=True, part='snippet')
    pls = playlist_request.execute()
    print(pls)
    total_pls = pls['pageInfo']['totalResults']
    yt_playlist_counter = 0
    yt_pl_ids = []
    for i in range(total_pls):
        try:
            yt_pl_id = pls['items'][yt_playlist_counter]['id']
            print(yt_pl_id)
            yt_pl_ids.append(yt_pl_id)
            yt_playlist_counter += 1
        except IndexError:
            pass
    print(yt_pl_ids)
    while True:
        if request.method == 'POST':
            youtube_inputted_id = request.form['yt_playlist_id']
            spotify_playlist_wanted_name = request.form['sp_playlist_wanted_name']
            if youtube_inputted_id in yt_pl_ids:
                break
        else:
            return render_template('youtube_playlist_select_page.html')
    song_names = get_yt_playlist_items(youtube, youtube_inputted_id)
    create_spotify_playlist(song_names, spotify_playlist_wanted_name)
    return render_template('process_done.html')


# pagina die alle items uit een youtube playlist haalt
def get_yt_playlist_items(youtube, youtube_pl_id):
    yt_pl_items = youtube.playlistItems().list(part='snippet', playlistId=youtube_pl_id, maxResults=50)
    yt_pl_items_response = yt_pl_items.execute()
    songs_in_pl = yt_pl_items_response['pageInfo']['totalResults']
    song_names = []
    song_names_counter = 0
    for i in range(songs_in_pl):
        song_name = yt_pl_items_response['items'][song_names_counter]['snippet']['title']
        optimized_song_name = optimize_song_name(song_name)
        song_names.append(optimized_song_name)
        song_names_counter += 1
    return song_names


# functie die wordt gebruikt om  lied namen te optimaliseren voor betere zoekresultaten op spotify
def optimize_song_name(song_name):
    song_name_split = song_name.split('(')
    song_name_new = song_name_split[0]
    return song_name_new


# maak spotify playlist en voeg items eraan toe
def create_spotify_playlist(song_names, wanted_playlist_name):
    code = request.args.get('code')  # Haal oauthcode uit pagina url
    spotify_token_info = sp_oauth.get_access_token(code)  # creer (spotify)token info  # noqa
    session['token_info'] = spotify_token_info  # zet token info van sessie
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    get_user_id = sp.current_user()
    user_id = get_user_id['id']
    create_new_playlist = sp.user_playlist_create(user=user_id, name=wanted_playlist_name, public=False)
    new_playlist_id = create_new_playlist['id']
    for song_name in song_names:
        sp_song = sp.search(q=song_name, type=['track', 'album'], limit=5)
        song_uri = sp_song['tracks']['items'][0]['uri']
        sp.playlist_add_items(playlist_id=new_playlist_id, items=[song_uri])
    print('done')


# Functie voor playlists naar youtube transferen, stuurt door naar spotify inlog
@app.route('/toyoutube')
def to_youtube():
    global platform
    platform = 'to_youtube'
    return redirect(url_for('spotify_login'))


# Dit is de echte login van spotify waarbij je moet inloggen
@app.route('/splogin')
def spotify_login():
    global sp_oauth
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


# Pagina die wacht tot er een spotify id word gegeven, als deze playlist bestaat start dan transfer naar youtube
@app.route('/getspotifyplaylist', methods=['GET', 'POST'])
def get_sp_playlist():
    global token_info
    spotify_ids = get_spotify_ids()  # call functie die playlist ids verzamelt
    while True:
        if request.method == 'POST':  # als er iets is ingeput
            spotify_input_id = request.form['sp_playlist_id']  # verzamel data uit Spotify id velt
            wanted_name = request.form['yt_playlist_wanted_name']  # verzamel gewilde playlist naam
            if spotify_input_id in spotify_ids:  # als id bestaat,
                break  # breek dan de loop en start het transfer process
        else:
            return render_template('spotify_playlist_select_page.html')
    get_spotify_playlist_items(spotify_input_id, wanted_name)  # begin transfer
    return render_template('process_done.html')


# Verzamel ids van al de gebruiker zijn spotify playlists
def get_spotify_ids():
    global token_info, sp_oauth

    # Variabelen
    sp_playlists = []
    sp_playlist_counter = 0

    # Spotify setup
    code = request.args.get('code')  # Haal oauthcode uit pagina url
    token_info = sp_oauth.get_access_token(code)  # creer token info  # noqa
    session['token_info'] = token_info  # zet token info van sessie
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))  # creer spotify item
    sp_pl_id_request = sp.current_user_playlists()  # request die al de gebruiker zijn spotify playlists ids verzamelt
    while True:
        try:
            sp_pl_id = sp_pl_id_request['items'][sp_playlist_counter]['id']  # verzamel id uit request
            sp_playlist_counter += 1
            sp_playlists.append(sp_pl_id)
        except IndexError:
            return sp_playlists


# Verzamel alle items uit een spotify playlist
def get_spotify_playlist_items(playlist_id, wanted_name):
    code = request.args.get('code')  # Haal oauthcode uit pagina url
    spotify_token_info = sp_oauth.get_access_token(code)  # creer (spotify)token info  # noqa
    session['token_info'] = spotify_token_info  # zet token info van sessie
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))  # creer spotify item
    total_items_request = sp.playlist_items(playlist_id=playlist_id, fields='total')  # kijk hoeveel liedjes in de playlist zitten # noqa
    totaal_aantal_liedjes = total_items_request.get('total')

    sp_counter = 0
    search_q_list = []

    # Verzamel een search_qeury om toe te voegen aan youtube playlist
    for i in range(totaal_aantal_liedjes):
        playlist_items_request = sp.playlist_items(playlist_id=playlist_id)
        spotify_song_name = playlist_items_request['items'][sp_counter]['track']['name']
        track_artist = playlist_items_request['items'][sp_counter]['track']['artists'][0]['name']
        spotify_search_q = str(track_artist) + ' - ' + str(spotify_song_name)
        print(spotify_search_q)
        search_q_list.append(spotify_search_q)
        sp_counter += 1
    print(search_q_list)
    create_youtube_playlist(search_q_list, wanted_name)


# creer youtube playlist en voeg daar de items uit de spotify playlist aan toe
def create_youtube_playlist(search_list, yt_pl_wanted_name):
    create_flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        'client_secrets.json', GOOGLE_SCOPES)
    credentials = create_flow.run_local_server()
    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
    new_playlist = youtube.playlists().insert(part="snippet,contentDetails", body={"snippet": {"title": yt_pl_wanted_name}})  # noqa
    new_playlist_response = new_playlist.execute()
    new_playlist_id = new_playlist_response['id']
    for item in search_list:
        song_to_add_id = search_yt_song(item, credentials)
        insert_yt_song = youtube.playlistItems().insert(part='snippet,contentDetails', body={
            "snippet": {
                "playlistId": new_playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": song_to_add_id
                }
            }
        })
        insert_yt_song.execute()


# zoek voor een youtube lied en return hiervan de id om gebruikt te worden bij het teovoegen in de playlist
def search_yt_song(search_term, credentials):
    videos = YoutubeSearch(search_term, max_results=1).to_dict()
    search_result_id = videos[0]['id']
    return search_result_id


# Deze functie word gebruikt om een spotify user token te genereren als deze nog niet bestaat.
def get_token():
    global token_info, sp_oauth
    token_valid = False
    if not token_valid:
        token_info = session.get('token_info')

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


# Creert oauth voor spotify
def create_spotify_oauth():
    print('oauth')
    return SpotifyOAuth(
        client_id='ffdb071c081b4cbe880dfe549167e244',
        client_secret='206ce55f95f74a1099d7770b0311354b',
        redirect_uri=url_for('redirect_page', _external=True),
        scope=['playlist-read-collaborative', 'user-read-private', 'user-read-email', 'playlist-modify-private',
               'playlist-read-private'],
    )


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
