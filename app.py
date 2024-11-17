# Spotify playlist enhancer
# Ethan Greenhouse 5/16/2024

# Import necessary modules from Flask, Spotipy, and other libraries
from flask import Flask, render_template, request  # Import Flask for web framework and request handling
from spotipy.oauth2 import SpotifyOAuth  # Import SpotifyOAuth for authentication
import spotipy  # Import Spotipy for interacting with the Spotify API
import random  # Import random for generating random selections (e.g., for seed tracks)
import os  # Import os for environment variable handling
from collections import defaultdict  # Import defaultdict for handling default dictionary behavior
from typing import Dict, List  # Import type annotations for type hinting

# Initialize the Flask web application with a custom template folder
app = Flask(__name__, template_folder='templates')

# Spotify API credentials (from environment variables for security)
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')  # Fetch Spotify Client ID from environment variable
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')  # Fetch Spotify Client Secret from environment variable
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"  # Define the callback URI for OAuth authentication

# SpotifyPlaylistEnhancer class for interacting with the Spotify API
class SpotifyPlaylistEnhancer:
    # Initialize the class with the Spotify credentials
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        # Define the scope of permissions required to interact with Spotify's API
        scope = "playlist-modify-public playlist-modify-private playlist-read-collaborative user-library-read"
        # Set up the Spotify client with OAuth authentication
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope
        ))

    # Suggest similar tracks based on audio features and seed tracks/genres
    def suggest_similar_tracks(self, playlist_id: str, num_suggestions: int = 6) -> List[Dict]:
        try:
            # Get the list of tracks in the playlist
            results = self.sp.playlist_tracks(playlist_id)
            tracks = results['items']
            
            if not tracks:
                raise ValueError("Playlist is empty")

            # Filter out invalid tracks (those that are None or have no track ID)
            valid_tracks = [
                track['track'] for track in tracks 
                if track['track'] and track['track']['id']
            ]

            if not valid_tracks:
                raise ValueError("No valid tracks found in playlist")

            # Get the audio features for the valid tracks
            track_ids = [track['id'] for track in valid_tracks]
            audio_features = [f for f in self.sp.audio_features(track_ids) if f]

            if not audio_features:
                raise ValueError("Could not analyze audio features")

            # Calculate the average of danceability, energy, and valence from the audio features
            avg_features = {
                'danceability': sum(f['danceability'] for f in audio_features) / len(audio_features),
                'energy': sum(f['energy'] for f in audio_features) / len(audio_features),
                'valence': sum(f['valence'] for f in audio_features) / len(audio_features)
            }

            # Select seed tracks (up to 2) from the playlist's tracks
            seed_tracks = random.sample(track_ids, min(2, len(track_ids)))

            # Select seed artists (up to 2) from the playlist's artists
            artists = list(set(track['artists'][0]['id'] for track in valid_tracks))
            seed_artists = random.sample(artists, min(2, len(artists)))

            # Select a random genre from available genres for recommendations
            available_genres = self.sp.recommendation_genre_seeds()['genres']
            seed_genre = [random.choice(available_genres)]

            # Get track recommendations based on the selected seed types (tracks, artists, genre)
            recommendations = self.sp.recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                seed_genres=seed_genre,
                target_danceability=avg_features['danceability'],
                target_energy=avg_features['energy'],
                target_valence=avg_features['valence'],
                limit=num_suggestions
            )

            # Filter out tracks that are already in the playlist
            new_tracks = [
                track for track in recommendations['tracks']
                if track['id'] not in track_ids
            ]

            # Return the suggested tracks, limiting to the requested number
            return new_tracks[:num_suggestions]

        except Exception as e:
            print(f"Error in suggest_similar_tracks: {str(e)}")
            raise

    # Analyze the number of tracks added by each contributor in a playlist
    def analyze_contributor_balance(self, playlist_id: str) -> Dict[str, int]:
        playlist = self.sp.playlist(playlist_id)
        contributor_counts = defaultdict(int)  # Default dictionary to count tracks by contributors
        
        for track in playlist['tracks']['items']:
            if track['added_by']['id']:
                contributor_counts[track['added_by']['id']] += 1
        
        return dict(contributor_counts)

# Web route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route for handling the form submission and analysis
@app.route('/analyze', methods=['POST'])
def analyze():
    playlist_input = request.form['playlist_input']
    playlist_id = playlist_input.strip()  # Clean up the playlist ID (e.g., remove spaces)

    # Create an instance of the SpotifyPlaylistEnhancer class
    enhancer = SpotifyPlaylistEnhancer(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI
    )

    # Get the suggested similar tracks based on the provided playlist
    tracks = enhancer.suggest_similar_tracks(playlist_id)
    # Analyze the contributor balance for the playlist (who added which tracks)
    contributor_balance = enhancer.analyze_contributor_balance(playlist_id)

    # Format the track data for rendering in the template
    formatted_tracks = [{'name': track['name'], 'artists': ', '.join(artist['name'] for artist in track['artists']), 'id': track['id']} for track in tracks]

    # Render and return the 'result.html' template with the tracks and contributor data
    return render_template('result.html', tracks=formatted_tracks, contributor_balance=contributor_balance)

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)