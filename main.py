import os

from dotenv import load_dotenv
from flask import Flask, Response, render_template, redirect, url_for, request
from flask_login import LoginManager

from Spotify_class import Spotify_functions
from Youtube_class import Youtube
from User_class import User

# import setups
load_dotenv()
login_manager = LoginManager()

# Flask setup
app = Flask(__name__)
app.config['SESSION_COOKIE_NAME'] = 'Cookies'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.getenv('APP_SECRET_KEY')
login_manager.init_app(app)

# Class setups
Spotify = Spotify_functions()
Youtube = Youtube(app)
User = User()


@login_manager.user_loader
@app.route('/')
def homepage() -> str:
    """Homepage of the website"""

    return render_template('main.html')


@app.route('/tospotify')
def to_spotify() -> Response:
    """Redirection page entered by hitting the yt -> spotify button"""

    # check if user is logged in, if yes get their id and otherwise redirect them to login
    if Spotify.check_token():
        Spotify.get_user_info()
        return redirect(url_for('get_yt_playlist'))
    else:
        return redirect(url_for('spotify_login'))


@app.route('/splogin')
def spotify_login() -> Response:
    """Login page for spotify"""

    auth_url = Spotify.spotify_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/redirect')
def spotify_redirect_page() -> Response:
    """Redirect page that redirects to get_yt_pl page"""

    # get access token from page link and get user id if needed
    Spotify.spotify_oauth.get_access_token(request.args['code'])
    Spotify.get_user_info()

    return redirect(url_for('get_yt_playlist'))


@app.route('/get_youtube_playlist', methods=['GET', 'POST'])
def get_yt_playlist() -> Response | str:
    """Page that gets an id of a yt playlist from user and checks its validity"""

    # check if user is logged in
    if not Spotify.check_token():
        return redirect(url_for('spotify_login'))

    # Create flow for Google oauth
    Youtube.create_flow()

    while True:

        # wait until user clicks submit button
        if request.method == 'POST':
            id_input = request.form['yt_playlist_id']
            wanted_playlist_name = request.form['sp_playlist_wanted_name']

            # check if playlist is valid and if yes get the items in the playlist
            if Youtube.validate_playlist(id_input):
                song_names = Youtube.get_playlist_items(id_input)
                break
            else:
                return render_template('youtube_playlist_select_page.html')

        else:
            return render_template('youtube_playlist_select_page.html')

    Spotify.create_spotify_playlist(wanted_playlist_name, song_names)

    return render_template('process_done.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True)
