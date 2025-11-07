from constants import TMDB, SEARCH_TV, SEARCH_MOVIE, FIND_TV, FIND_TV_EPISODES
import requests
from dotenv import load_dotenv
import os

load_dotenv()


HEADERS = {
    "accept": "application/json",
    "User-Agent": "TaggerCLI/1.0",
    "Authorization": f"Bearer {os.getenv('TMDB_READ_ACCESS_TOKEN')}",
}


def search(url, search_term: str, tv: bool):
    sanitized_query = search_term.replace(" ", "%20")
    full_url = f"{TMDB}{url}?query={sanitized_query}&include_adult=true&page=1"

    response = requests.get(full_url, headers=HEADERS, timeout=20)
    data = response.json()

    results = []

    for item in data.get("results", []):
        name = item.get("name") or item.get("title")
        overview = item.get("overview")
        tmdb_id = item.get("id")
        release = item.get("release_date") or item.get("first_air_date")

        results.append(
            {
                "name": name,
                "overview": overview,
                "id": tmdb_id,
                "media_type": "tv" if tv else "movie",
                "release_date": release,
            }
        )

    return results


def search_tv_shows(search_term: str):
    return search(SEARCH_TV, search_term, tv=True)


def search_movies(search_term: str):
    return search(SEARCH_MOVIE, search_term, tv=False)


def get_seasons(series_id):
    """return the list of seasons for a given TV series id."""
    url = f"{TMDB}{FIND_TV(series_id)}"

    response = requests.get(url, headers=HEADERS, timeout=20)
    data = response.json()

    seasons = data.get("seasons", [])
    return seasons


def get_episodes(series_id, season_number):
    """return all episodes for the provided season."""
    url = f"{TMDB}{FIND_TV_EPISODES(series_id, season_number)}"

    response = requests.get(url, headers=HEADERS, timeout=20)
    data = response.json()

    return data.get("episodes", [])

GET_SHOW_EMBED = lambda tmdb_id, season_number, episode_number: f"https://www.vidking.net/embed/tv/{tmdb_id}/{season_number}/{episode_number}"
GET_MOVIE_EMBED = lambda tmdb_id: f"https://www.vidking.net/embed/movie/{tmdb_id}"

