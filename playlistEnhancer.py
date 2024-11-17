# Spotify playlist enhancer
# Ethan Greenhouse 5/16/2024

import spotipy  # Import the Spotipy library for interacting with the Spotify API
from spotipy.oauth2 import SpotifyOAuth  # Import SpotifyOAuth for handling OAuth authentication
from collections import defaultdict  # Import defaultdict for handling default dictionary behavior
import random  # Import random for random number generation
from typing import Dict, List, Tuple  # Import type annotations for type hinting
import os  # Import os for interacting with the operating system (e.g., creating directories)

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

# Create a directory for storing data if it doesn't already exist
if not os.path.exists("data"):
    os.makedirs("data")

# Class definition for Spotify Playlist Enhancer
class SpotifyPlaylistEnhancer:
    # Initialize the Spotify client with necessary permissions.
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

    # Analyze the number of tracks added by each contributor in a playlist.
    def analyze_contributor_balance(self, playlist_id: str) -> Dict[str, int]:
        # Retrieve the playlist details from Spotify
        playlist = self.sp.playlist(playlist_id)
        contributor_counts = defaultdict(int)  # Default dictionary to count tracks by contributors
        
        # Loop through the tracks in the playlist and count the number of tracks per contributor
        for track in playlist['tracks']['items']:
            if track['added_by']['id']:
                contributor_counts[track['added_by']['id']] += 1
        
        # Return the contributor counts as a regular dictionary
        return dict(contributor_counts)

    # Retrieve available genres from Spotify for track recommendations.
    def get_available_genres(self) -> List[str]:
        """Get a list of available genres from Spotify."""
        return self.sp.recommendation_genre_seeds()['genres']

    # Suggest similar tracks based on audio features and seed tracks/genres.
    def suggest_similar_tracks(self, playlist_id: str, num_suggestions: int = 6) -> List[Dict]:
        """Suggest similar tracks based on audio features and seed tracks/genres."""
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

# Extract the playlist ID from various Spotify URL/URI formats.
def extract_playlist_id(playlist_input):
    # Handle Spotify URLs in the format "open.spotify.com/playlist/"
    if "open.spotify.com/playlist/" in playlist_input:
        playlist_id = playlist_input.split("playlist/")[1]
        # Remove any additional parameters from the URL
        playlist_id = playlist_id.split("?")[0]
        return playlist_id
    
    # Handle Spotify URIs in the format "spotify:playlist:xxxxx"
    elif "spotify:playlist:" in playlist_input:
        return playlist_input.split("spotify:playlist:")[1]
    
    # Handle direct playlist IDs (length of 22 characters)
    elif len(playlist_input.strip()) == 22:
        return playlist_input.strip()
    
    # Raise an error if the playlist format is invalid
    raise ValueError("Invalid playlist format. Please provide a valid Spotify playlist URL, URI, or ID")

# Print a separator line to make the output more readable
def print_separator():
    print("\n" + "="*50 + "\n")

# Main function to drive the program
def main():
    try:
        print("Initializing Spotify Playlist Enhancer...")
        # Create an instance of the SpotifyPlaylistEnhancer class
        enhancer = SpotifyPlaylistEnhancer(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI
        )

        print_separator()
        print("You can find the playlist URL by:")
        print("1. Right-clicking the playlist in Spotify")
        print("2. Selecting 'Share'")
        print("3. Clicking 'Copy link to playlist'")
        print_separator()
        
        # Ask the user for the playlist URL or ID
        playlist_input = input("Enter Spotify playlist URL or ID: ")
        
        try:
            # Extract the playlist ID from the provided input
            playlist_id = extract_playlist_id(playlist_input)
            print("\nAnalyzing playlist...")
            
            # Get the playlist details using the Spotify client
            playlist = enhancer.sp.playlist(playlist_id)
            print(f"\nAnalyzing playlist: {playlist['name']}")
            print(f"Total tracks: {playlist['tracks']['total']}")
            
            print("\nGetting song suggestions...")
            # Suggest similar tracks based on the playlist
            suggestions = enhancer.suggest_similar_tracks(playlist_id)
            
            if suggestions:
                print_separator()
                print("Suggested tracks:")
                for i, track in enumerate(suggestions, 1):
                    artists = ", ".join(artist['name'] for artist in track['artists'])
                    print(f"{i}. {track['name']} by {artists}")
                    print(f"   Spotify URI: spotify:track:{track['id']}")
            
            print_separator()
            print("Analyzing contributor balance...")
            # Analyze the number of tracks contributed by each user
            balance = enhancer.analyze_contributor_balance(playlist_id)
            
            if balance:
                print("\nContributor statistics:")
                total_tracks = sum(balance.values())
                for user_id, count in balance.items():
                    percentage = (count / total_tracks) * 100
                    print(f"User {user_id}: {count} tracks ({percentage:.1f}%)")
            
            print_separator()

        except ValueError as e:
            print(f"Error: {str(e)}")
        except Exception as e:
            print(f"An error occurred while processing the playlist: {str(e)}")
            print("Try checking if the playlist is accessible and contains tracks.")

    except Exception as e:
        print(f"An error occurred during initialization: {str(e)}")
        print("Please check your Spotify credentials in config.py")

# This block runs the `main()` function if the script is executed directly (not imported).
if __name__ == "__main__":
    main()