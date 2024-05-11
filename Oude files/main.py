from flask import Flask, request, url_for, session, redirect
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

import pprint
import os
import spotipy

load_dotenv()

correct = False
counter = 0

app = Flask(__name__)
app.secret_key = 'fyfgyfgyegfyegfy'
app.config['SESSION COOKIE NAME'] = 'Cookies'

@app.route('/')
def index():
    return 'Musictransferhomepage'

@app.route('/getPlaylists')
def getPlaylists():
    return 'playlists....'




yt_api_key = os.getenv('YT_API_KEY')
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')


youtube = build('youtube', 'v3', developerKey=yt_api_key)
playlist_request = youtube.playlistItems().list(part='snippet', playlistId='PL0k_0mP991P7f2zagiEAboXOH9CTCV1Eq',
                                                maxResults=1000)

print('---------------Printing playlist content---------------')
while True:
    try:
        response = playlist_request.execute()
        pprint.pprint(response['items'][counter]['snippet']['title'])
        counter += 1
    except IndexError:
        print('--------------------End of playlist--------------------')
        while correct is False:
            correct_playlist_question = input('Is this the correct playlist? (yes/no):  ')
            if correct_playlist_question == 'yes':
                print('yes')
                correct = True
            elif correct_playlist_question == 'no':
                print('no')
                correct = True
            else:
                print('That is not a correct answer')
