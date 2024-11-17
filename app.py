from flask import Flask, render_template, request
from spotipy.oauth2 import SpotifyOAuth
import spotipy
import random
import os

app = Flask(__name__, template_folder='templates')

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

# Define the SpotifyPlaylistEnhancer class
class SpotifyPlaylistEnhancer:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public playlist-modify-private playlist-read-collaborative user-library-read"
        ))

    def suggest_similar_tracks(self, playlist_id, num_suggestions=5):
        results = self.sp.playlist_tracks(playlist_id)
        tracks = results['items']
        valid_tracks = [track['track'] for track in tracks if track['track']]

        track_ids = [track['id'] for track in valid_tracks]
        audio_features = [f for f in self.sp.audio_features(track_ids) if f]

        avg_features = {
            'danceability': sum(f['danceability'] for f in audio_features) / len(audio_features),
            'energy': sum(f['energy'] for f in audio_features) / len(audio_features),
            'valence': sum(f['valence'] for f in audio_features) / len(audio_features)
        }

        seed_tracks = random.sample(track_ids, min(2, len(track_ids)))
        available_genres = self.sp.recommendation_genre_seeds()['genres']
        seed_genre = [random.choice(available_genres)]

        recommendations = self.sp.recommendations(
            seed_tracks=seed_tracks,
            seed_genres=seed_genre,
            target_danceability=avg_features['danceability'],
            target_energy=avg_features['energy'],
            target_valence=avg_features['valence'],
            limit=num_suggestions
        )

        return recommendations['tracks']

    def analyze_contributor_balance(self, playlist_id):
        playlist = self.sp.playlist(playlist_id)
        contributor_counts = {}
        for track in playlist['tracks']['items']:
            user_id = track['added_by']['id']
            contributor_counts[user_id] = contributor_counts.get(user_id, 0) + 1
        return contributor_counts

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    playlist_input = request.form['playlist_input']
    playlist_id = playlist_input.strip()

    enhancer = SpotifyPlaylistEnhancer(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI
    )

    tracks = enhancer.suggest_similar_tracks(playlist_id)
    contributor_balance = enhancer.analyze_contributor_balance(playlist_id)

    # Prepare track and contributor information for rendering
    formatted_tracks = [{'name': track['name'], 'artists': ', '.join(artist['name'] for artist in track['artists']), 'id': track['id']} for track in tracks]

    return render_template('result.html', tracks=formatted_tracks, contributor_balance=contributor_balance)

if __name__ == '__main__':
    app.run(debug=True)