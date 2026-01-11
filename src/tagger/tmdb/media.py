from ..constants import TMDB, SEARCH_TV, SEARCH_MOVIE, FIND_TV, FIND_TV_EPISODES
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from urllib.parse import quote
from dotenv import load_dotenv
import os

load_dotenv()


class TMDBError(Exception):
    pass


class TMDBConnectionError(TMDBError):
    pass


class TMDBTimeoutError(TMDBError):
    pass


class TMDBAuthError(TMDBError):
    pass


class TMDBResponseError(TMDBError):
    pass


def _get_api_token():
    token = os.getenv("TMDB_READ_ACCESS_TOKEN")
    if not token:
        raise TMDBAuthError(
            "TMDB_READ_ACCESS_TOKEN not found in environment. "
            "Please set it in your .env file."
        )
    return token


def _get_headers():
    return {
        "accept": "application/json",
        "User-Agent": "TaggerCLI/1.0",
        "Authorization": f"Bearer {_get_api_token()}",
    }


def _make_request(url: str) -> dict:
    headers = _get_headers()

    try:
        response = requests.get(url, headers=headers, timeout=20)
    except ConnectionError as e:
        raise TMDBConnectionError(
            "Unable to connect to TMDB API. Please check your internet connection."
        ) from e
    except Timeout as e:
        raise TMDBTimeoutError(
            "Request to TMDB API timed out. Please try again later."
        ) from e
    except RequestException as e:
        raise TMDBError(f"Unexpected request error: {e}") from e

    if response.status_code == 401:
        raise TMDBAuthError(
            "Authentication failed. Please check your TMDB_READ_ACCESS_TOKEN."
        )
    elif response.status_code == 404:
        raise TMDBResponseError(f"Resource not found: {url}")
    elif response.status_code == 429:
        raise TMDBResponseError(
            "Rate limit exceeded. Please wait before making more requests."
        )
    elif response.status_code >= 400:
        raise TMDBResponseError(
            f"TMDB API error (HTTP {response.status_code}): {response.text}"
        )

    try:
        return response.json()
    except ValueError as e:
        raise TMDBResponseError(f"Invalid JSON response from TMDB: {e}") from e


def search(url, search_term: str, tv: bool):
    encoded_query = quote(search_term)
    full_url = f"{TMDB}{url}?query={encoded_query}&include_adult=true&page=1"

    data = _make_request(full_url)
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
    url = f"{TMDB}{FIND_TV(series_id)}"
    data = _make_request(url)
    return data.get("seasons", [])


def get_episodes(series_id, season_number):
    url = f"{TMDB}{FIND_TV_EPISODES(series_id, season_number)}"
    data = _make_request(url)
    return data.get("episodes", [])


GET_SHOW_EMBED = lambda tmdb_id, season_number, episode_number: f"https://www.vidking.net/embed/tv/{tmdb_id}/{season_number}/{episode_number}?color=e50914&episodeSelector=true"
GET_MOVIE_EMBED = lambda tmdb_id: f"https://www.vidking.net/embed/movie/{tmdb_id}"
