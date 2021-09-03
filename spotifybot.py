##imports
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util
from pathlib import Path
import pandas as pd
import numpy as np
from spotifuncs import authenticate, create_df_playlist, create_df_recommendations,append_audio_features, create_similarity_score, filter_with_meansong, feature_filter
import warnings
warnings.filterwarnings('ignore')
#set path
path = Path("D:\\spotify-recommender-systems\\Spotify_playlist")

#get client credentials and user name
with open(path / "client_s.txt") as f:
    content = f.readlines()
content = [x.strip() for x in content]

client_id = content[0]
client_secret = content[1]

with open(path / "usernames.txt") as f:
    usernames = f.readlines()
usernames = [x.strip() for x in usernames]

username1 = usernames[0] #could be made a user input, may however require new authentication

#set scope, uri and client_credentials_manager
scope = "user-library-read user-read-recently-played user-top-read playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative"

redirect_uri = "https://developer.spotify.com/dashboard/applications/46fe7619628c463b8b597c255f056a5c"

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, 
                                                      client_secret=client_secret)

#authenticate user
sp_m = authenticate(redirect_uri, client_credentials_manager, username1, scope, client_id, client_secret)

#get playlist based on uri input

playlist_uri = "https://open.spotify.com/playlist/3XoR63J8VxAfkrqOANAkB9"
playlist = sp_m.playlist(playlist_uri)
playlist_df = create_df_playlist(playlist,sp = sp_m)

#create mean_song
mean_song = pd.DataFrame(columns=playlist_df.columns)
mean_song.loc["mean"] = playlist_df.mean()

#get seed tracks for recommendations
seed_tracks = playlist_df["track_id"].tolist()
#create recommendation df
recomm_dfs = []
for i in range(5,len(seed_tracks)+1,5):
    recomms = sp_m.recommendations(seed_tracks = seed_tracks[i-5:i],limit = 25)
    recomms_df = append_audio_features(create_df_recommendations(recomms),sp_m)
    recomm_dfs.append(recomms_df)
recomms_df = pd.concat(recomm_dfs)
recomms_df.reset_index(drop = True, inplace = True)
#create similarity scoring between playlist and recommendations
similarity_score = create_similarity_score(playlist_df,recomms_df)
while True:
    #get a filtered recommendations df
    final_recomms = recomms_df.iloc[[np.argmax(i) for i in similarity_score]]
    final_recomms = final_recomms.drop_duplicates()
    #filter again so tracks are not already in playlist_df
    final_recomms = final_recomms[~final_recomms["track_name"].isin(playlist_df["track_name"])]
    final_recomms.reset_index(drop = True, inplace = True)

    #manual filtering by audio feature
    manual_filter = input("Do you wish to filter the recommendations manually by setting one of the following audio features very high or very low: speechiness, acousticness, instrumentalness, liveness [y/n]").lower()
    if manual_filter == "y":
        features = input("Which features would you like to filter by? (Not more than 1-2 recommended) [e.g. speechiness,liveness]").split(",")
        assert isinstance(features,list), "Something went wrong. Please enter the features seperated by a comma"
        high_low = input("For each feature please enter 'high' if you want the feature to be high or 'low' if you want it to be low [e.g. high,low]").split(",")
        high_low = [True if x == "high" else False for x in high_low]
        assert isinstance(high_low,list), "Something went wrong. Please enter the features seperated by a comma"
        assert len(features) == len(high_low), "Number of features and True/False must be equal"
        #loop through selected features to filter by
        for feat,high in zip(features,high_low):
            final_recomms = feature_filter(final_recomms,feature = feat, high=high)
        print(f"Your list of recommended songs is now {len(final_recomms)} songs long")
        proceed = input("Do you wish to proceed or filter differently? [proceed/filter]").lower()
        if proceed == "proceed":
            break
    else:
        break
        



#filter with mean song or sample from recommended
n_recommendations = int(input("how many songs would you like to add to your playlist? Please enter a number between 1 - 20   "))
assert 21 > n_recommendations > 0 , "Number of Recommendations must be between 1 and 20"
assert len(final_recomms) > n_recommendations, "Can't add more song than the filtered dataframe contains"

mean_song_filter = input("Do you wish to filter the songs further by comparing them to the average playlist song? [y/n] (This is works for playlists with a very unified 'sound')").lower()
if mean_song_filter == "y":
    final_recomms = filter_with_meansong(mean_song,final_recomms, n_recommendations=n_recommendations)
else:
    final_recomms = final_recomms.sample(n = n_recommendations)

# add songs to playlist
confirm = input("Please confirm that you want to add songs to the playlist by typing YES   ")
if confirm == "YES":
    sp_m.user_playlist_add_tracks(username1,
                              playlist_id = playlist_uri,
                              tracks = final_recomms["track_id"].tolist())