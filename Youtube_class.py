import os
import re
import ytmusicapi
import SongNameSplit
import googleapiclient.errors
import googleapiclient.discovery
import google_auth_oauthlib

from User_class import User
from Spotify_class import Spotify_functions

from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from google_auth_oauthlib.flow import InstalledAppFlow

# import setups
load_dotenv()
yt_api_unofficial = ytmusicapi.YTMusic()

# Class setups
User = User()
Spotify = Spotify_functions()

# Google/Youtube setup
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
CLIENT_FILE = 'client_secrets.json'
REDIRECT_URI = 'http://127.0.0.1:5000/ytplaylistselect'
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/youtube',
                 'https://www.googleapis.com/auth/youtubepartner',
                 'https://www.googleapis.com/auth/youtube.force-ssl']
YT_DEV_KEY = None

# Variables
terms_to_remove: list = ['(Official Videoclip)', '(Official Video)', '[Official video]', '(Official Live Video)',
                         '(Official Music Video)', '[Official Music Video]', '(Lyric Video)', '(Lyric)', 'VEVO',
                         '[Official Video]', '(Official HD Music Video)', '(Official HD Video)', '(Official)',
                         '(Official Lyric Video)', '- Topic', '[4K Upgrade]']


class Youtube:
    """Class that contains all functions that use Youtube"""

    def __init__(self, app):
        self.app = app
        self.oauth = None
        self.flow = None
        self.credentials = None
        self.youtube_build = None
        self.google_build = None

    def create_yt_oauth(self) -> None:
        """Function that sets up google oauth needed to access a youtube account"""

        self.oauth = OAuth(self.app)
        self.google_build = self.oauth.register(
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

    def create_flow(self) -> None:
        """Function that creates the flow that is used for running the Google server"""

        self.flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            'client_secrets.json', GOOGLE_SCOPES)
        self.credentials = self.flow.run_local_server()
        self.youtube_build = googleapiclient.discovery.build('youtube', 'v3',
                                                             credentials=self.credentials)

    def validate_playlist(self, playlist_id: str) -> bool:
        """Function that checks if a playlist is valid or not"""

        request = self.youtube_build.playlists().list(part="snippet", id=playlist_id)
        response = request.execute()

        # Response is empty if a playlist is invalid
        if not response['items']:
            return False
        else:
            return True

    def get_playlist_items(self, playlist_id) -> list:
        """Function that uses yt api to get song names from a playlist"""

        next_page_token: str | None = None
        song_names: list = []

        while True:
            # Check if there is a next page
            if next_page_token:
                playlist_request = self.youtube_build.playlistItems().list(part='snippet',
                                                                           playlistId=playlist_id,
                                                                           pageToken=next_page_token,
                                                                           maxResults=50)
            else:
                playlist_request = self.youtube_build.playlistItems().list(part='snippet',
                                                                           playlistId=playlist_id,
                                                                           maxResults=50)

            playlist_response = playlist_request.execute()
            items_on_page: int = len(playlist_response['items'])

            # Go through every song and get its name and artist
            for index in range(items_on_page):
                yt_video_id: str = playlist_response['items'][index]['snippet']['resourceId']['videoId']

                try:
                    song_name_request = self.youtube_build.videos().list(part='snippet', id=yt_video_id)
                    song_name_response = song_name_request.execute()
                    song_name = song_name_response['items'][0]['snippet']['title']
                    song_artist = song_name_response['items'][0]['snippet']['channelTitle']

                    song_name = optimize_song_name(song_name, song_artist)

                    song_names.append(song_name)

                except IndexError:
                    pass

            # check if there is a next page with songs and end function if not
            try:
                next_page_token: str = playlist_response['nextPageToken']
            except KeyError:
                break

        return song_names


def optimize_song_name(song_name: str, channel_title: str) -> str:
    """Optimize a song name to include both title and artist to get optimal results from spotify api"""

    # Try splitting song into artist and title using SongNameSplit package
    try:
        song_info = SongNameSplit.namesplit(song_name, runQuietly=True)

        song_title = song_info['songname']
        song_artist = song_info['artist']

        song_name = f'{song_artist} - {song_title}'

    # if song title is not standard
    except SongNameSplit.NonStandardSongTitle:

        # get every word from song
        for item in song_name.split(' '):
            try:
                # see if word matches an artist
                match = re.match(item.upper(), channel_title.upper())

                # if song title already features an artist the title is ok
                if match:
                    song_name = song_name
                    break

            except re.error:
                pass

        # If song title doesn't include any artists check if the channel title is an artist and otherwise
        # return the song title
        else:
            valid_artist = Spotify.check_artist(channel_title)

            if valid_artist:
                song_name = f'{channel_title} - {song_name}'

    # remove unwanted terms from song name
    for term in terms_to_remove:
        song_name = song_name.replace(term, '')
        song_name = song_name.replace(term.upper(), '')

    song_name = song_name.replace('  ', ' ')
    song_name = song_name.replace('   ', ' ')

    return song_name
