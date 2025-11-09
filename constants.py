


TMDB = "https://api.themoviedb.org/3"

SEARCH_TV = "/search/tv"
SEARCH_MOVIE = "/search/movie"

# url = "https://api.themoviedb.org/3/tv/1396/season/1?language=en-US"

FIND_TV_EPISODES = lambda series_id, season_number: f"/tv/{series_id}/season/{season_number}"

FIND_TV = lambda x: f"/tv/{x}" # /tv/1405 example 