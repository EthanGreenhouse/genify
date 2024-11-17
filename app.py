# Genify: Playlist Enhancer
# Ethan Greenhouse 
# 5/16/2024

from flask import Flask, render_template, request
from spotipy.oauth2 import SpotifyOAuth
import spotipy
import random
import os
from collections import defaultdict
from typing import Dict, List

app = Flask(__name__, template_folder='templates')

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

class SpotifyPlaylistEnhancer:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        scope = "playlist-modify-public playlist-modify-private playlist-read-collaborative user-library-read"
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope
        ))

    def suggest_similar_tracks(self, playlist_id: str, num_suggestions: int = 6, danceability: float = 0.5, energy: float = 0.5, valence: float = 0.5) -> List[Dict]:
        try:
            results = self.sp.playlist_tracks(playlist_id)
            tracks = results['items']

            if not tracks:
                raise ValueError("Playlist is empty")

            valid_tracks = [track['track'] for track in tracks if track['track'] and track['track']['id']]

            if not valid_tracks:
                raise ValueError("No valid tracks found in playlist")

            track_ids = [track['id'] for track in valid_tracks]
            audio_features = [f for f in self.sp.audio_features(track_ids) if f]

            if not audio_features:
                raise ValueError("Could not analyze audio features")

            avg_features = {
                'danceability': sum(f['danceability'] for f in audio_features) / len(audio_features),
                'energy': sum(f['energy'] for f in audio_features) / len(audio_features),
                'valence': sum(f['valence'] for f in audio_features) / len(audio_features)
            }

            seed_tracks = random.sample(track_ids, min(2, len(track_ids)))
            artists = list(set(track['artists'][0]['id'] for track in valid_tracks))
            seed_artists = random.sample(artists, min(2, len(artists)))

            available_genres = self.sp.recommendation_genre_seeds()['genres']
            seed_genre = [random.choice(available_genres)]

            recommendations = self.sp.recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                seed_genres=seed_genre,
                target_danceability=danceability,
                target_energy=energy,
                target_valence=valence,
                limit=num_suggestions
            )

            new_tracks = [track for track in recommendations['tracks'] if track['id'] not in track_ids]

            return new_tracks[:num_suggestions]

        except Exception as e:
            print(f"Error in suggest_similar_tracks: {str(e)}")
            raise

    def analyze_contributor_balance(self, playlist_id: str) -> Dict[str, int]:
        contributor_counts = defaultdict(int)
        offset = 0
        limit = 100

        while True:
            response = self.sp.playlist_tracks(playlist_id, offset=offset, limit=limit)
            tracks = response.get('items', [])

            if not tracks:
                break

            for track in tracks:
                added_by = track['added_by']
                if added_by and added_by.get('id'):
                    contributor_counts[added_by['id']] += 1

            offset += limit

        return dict(contributor_counts)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    playlist_input = request.form['spotify_url']
    playlist_id = playlist_input.strip()

    num_recommendations = int(request.form['num_recommendations'])
    danceability = float(request.form['danceability'])
    energy = float(request.form['energy'])
    valence = float(request.form['valence'])

    enhancer = SpotifyPlaylistEnhancer(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI
    )

    try:
        tracks = enhancer.suggest_similar_tracks(
            playlist_id,
            num_suggestions=num_recommendations,
            danceability=danceability,
            energy=energy,
            valence=valence
        )

        contributor_balance = enhancer.analyze_contributor_balance(playlist_id)

        # Format tracks with artists as comma-separated strings
        formatted_tracks = []
        for track in tracks:
            artist_names = [artist['name'] for artist in track['artists']]  # Extract artist names
            formatted_tracks.append({
                'name': track['name'],
                'artists': ', '.join(artist_names),  # Join artist names with commas
                'id': track['id']
            })

        return render_template('result.html', tracks=formatted_tracks, contributor_balance=contributor_balance)

    except Exception as e:
        error_message = f"Error: {str(e)}"
        return render_template('result.html', error=error_message)

if __name__ == '__main__':
    app.run(debug=True)
