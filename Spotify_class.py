import os
import spotipy
import jellyfish

from dotenv import load_dotenv
from flask import session
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

# import setups
load_dotenv()
cache_handler = FlaskSessionCacheHandler(session)


# Spotify variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
scopes = ['playlist-read-collaborative', 'user-read-private', 'playlist-modify-private',
          'playlist-read-private']

# handles spotify oauth
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri='http://127.0.0.1:5000/redirect',
    scope=scopes,
    cache_handler=cache_handler,
    show_dialog=True
)

# spotify client
sp = Spotify(auth_manager=sp_oauth)


class Spotify_functions:
    """Class that contains all functions that use spotify api"""

    def __init__(self):
        self.spotify_oauth: spotipy.SpotifyOAuth = sp_oauth
        self.sp: spotipy.Spotify = sp
        self.user_id = None

    def check_token(self) -> bool:
        """Check if user is logged into spotify"""

        # check if the user has a valid access token and thus is logged in
        if not self.spotify_oauth.validate_token(cache_handler.get_cached_token()):
            return False
        else:
            return True

    def get_user_info(self) -> None:
        """Use Spotify client to get current user info"""

        self.user_id = self.sp.current_user()['id']

    def create_spotify_playlist(self, playlist_name, song_names) -> None:
        """Use Spotify client to create a new playlist on the current user's account and transfer
         the songs of the chosen youtube playlist"""

        # create a new playlist and get its id
        new_playlist = sp.user_playlist_create(user=self.user_id, name=playlist_name, public=False, collaborative=False)
        playlist_id = new_playlist['id']

        # Transfer every song
        for song_name in song_names:

            spotify_song = self.sp.search(q=song_name, limit=5, type=['track'])
            highest_similarity = 0
            song_uri = None

            # Search for song with the highest similarity
            for i in range(5):
                song_artist = spotify_song['tracks']['items'][i]['artists'][0]['name']
                song_title = spotify_song['tracks']['items'][i]['name']

                full_title = f'{song_artist} - {song_title}'
                full_title_2 = f'{song_title} - {song_artist}'

                similarity = jellyfish.jaro_similarity(song_name, full_title)
                similarity_2 = jellyfish.jaro_similarity(song_name, full_title_2)

                if similarity > highest_similarity or similarity_2 > highest_similarity:

                    # Skip unwanted remixes
                    if 'remix' in song_title and 'remix' not in song_name:
                        pass
                    elif 'Remix' in song_title and 'Remix' not in song_name:
                        pass
                    elif 'REMIX' in song_title and 'REMIX' not in song_name:
                        pass
                    else:
                        if similarity > highest_similarity:
                            highest_similarity = similarity

                        else:
                            highest_similarity = similarity_2

                        song_uri = spotify_song['tracks']['items'][i]['uri']

            self.sp.playlist_add_items(playlist_id=playlist_id, items=[song_uri])

    def check_artist(self, artist_name: str) -> bool:
        """Search for an artist to see if the string passed to this function is an artist"""

        artist_search_result = self.sp.search(q=artist_name, type='artist', limit=5)

        # try 5 times to see if an artist is valid
        for i in range(5):
            artist = artist_search_result['artists']['items'][i]['name']

            if jellyfish.jaro_similarity(artist, artist_name) > 0.7:
                return True

        else:
            return False

    def get_playlist_items(self):
        pass
