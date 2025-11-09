import textwrap
import threading

from rich.text import Text
from textual.app import App
from textual.screen import Screen
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from tmdb.media import (
    get_episodes,
    get_seasons,
    search_movies,
    search_tv_shows,
    GET_SHOW_EMBED,
    GET_MOVIE_EMBED,
)
from launcher import launch_media


class SearchScreen(Screen):
    """Initial screen where the user types the TMDB search term."""

    def compose(self):
        yield Static("Enter a search term for TMDB results:")
        yield Input(placeholder="e.g. Breaking Bad, Dune, etc.", id="search-input")
        yield Footer()

    def on_mount(self):
        self.query_one(Input).focus()

    async def on_input_submitted(self, event: Input.Submitted):
        event.stop()
        term = event.value.strip()
        if not term:
            self.notify("Please enter a search term.")
            return

        await self.app.handle_search_term(term)


class MediaTypeScreen(Screen):
    """Screen for choosing between movie or TV searches."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self):
        yield Static("What would you like to search?")
        options = OptionList(id="media-types")
        options.add_option(Option("Movies", id="movie"))
        options.add_option(Option("TV Shows", id="tv"))
        yield options
        yield Footer()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        event.stop()
        await self.app.load_results(event.option.id)


class EpisodesOptionScreen(Screen):
    """Screen that lets the user pick an episode for a selected season."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, episodes, show_id, season_number):
        super().__init__()
        self.episodes = episodes or []
        self.show_id = show_id
        self.season_number = season_number

    def compose(self):
        yield Static(f"Choose an episode (Season {self.season_number})")
        option_list = OptionList(id="episodes")

        if not self.episodes:
            option_list.add_option(Option("No episodes found", id="none"))
        else:
            for episode in self.episodes:
                number = episode.get("episode_number", "N/A")
                title = episode.get("name")
                overview = episode.get("overview") or ""
                blurb = textwrap.shorten(overview, width=80, placeholder="…") if overview else ""

                label = Text(f"E{number}: {title}", style="bold")
                if blurb:
                    label.append(f"\n{blurb}", style="dim")

                option_list.add_option(Option(label, id=str(number)))

        yield option_list
        yield Footer()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        event.stop()
        option_id = event.option.id

        if option_id == "none":
            self.notify("No episodes available.")
            return
        
        embed_url = GET_SHOW_EMBED(self.show_id, self.season_number, option_id)
        message = f"Season {self.season_number}, Episode {option_id} queued"
        self.notify(message)
        threading.Thread(target=launch_media, args=(embed_url,), daemon=True).start()


class SeasonsOptionScreen(Screen):
    """Screen that lets the user pick a season for the selected show."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, seasons, show_id, show_name):
        super().__init__()
        self.seasons = seasons or []
        self.show_id = show_id
        self.show_name = show_name

    def compose(self):
        yield Static(f"Choose a season for {self.show_name}")
        option_list = OptionList(id="seasons")

        if not self.seasons:
            option_list.add_option(Option("No seasons found", id="none"))
        else:
            for season in self.seasons:
                number = season.get("season_number", "N/A")
                name = season.get("name") or f"Season {number}"
                count = season.get("episode_count", "N/A")
                label = f"{name} (Episodes: {count})"
                option_list.add_option(Option(label, id=str(number)))

        yield option_list
        yield Footer()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        event.stop()
        option_id = event.option.id

        if option_id == "none":
            self.notify("No seasons available.")
            return

        try:
            season_number = int(option_id)
        except ValueError:
            self.notify("Invalid season number.")
            return

        episodes = get_episodes(self.show_id, season_number)
        await self.app.push_screen(
            EpisodesOptionScreen(episodes, self.show_id, season_number)
        )


class ResultsOptionScreen(Screen):
    """Screen for showing movie or TV search results."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, results, media_type):
        super().__init__()
        self.results = results or []
        self.media_type = media_type
        self.lookup = {str(item.get("id")): item for item in self.results}

    def compose(self):
        descriptor = "movie" if self.media_type == "movie" else "TV show"
        yield Static(f"Select a {descriptor} for '{self.app.search_term}':")

        option_list = OptionList(id="results")

        if not self.results:
            option_list.add_option(Option("No results", id="none"))
        else:
            for item in self.results:
                tmdb_id = item.get("id")
                title = item.get("name") or "Untitled"
                release = item.get("release_date") or "N/A"
                overview = item.get("overview") or "No overview available."
                blurb = textwrap.shorten(overview, width=80, placeholder="…")

                label = Text(f"{title} ({release})", style="bold")
                label.append(f"\n{blurb}", style="dim")

                option_list.add_option(Option(label, id=str(tmdb_id)))

        yield option_list
        yield Footer()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        event.stop()
        option_id = event.option.id

        if option_id == "none":
            self.notify("Nothing to select.")
            return

        item = self.lookup.get(option_id)
        if not item:
            self.notify("Unable to load selection.")
            return

        tmdb_id = item.get("id")

        if self.media_type == "movie":
            movie_embed_url = GET_MOVIE_EMBED(tmdb_id)
            self.notify(f"Movie '{item.get('name')}' queued")
            threading.Thread(target=launch_media, args=(movie_embed_url,), daemon=True).start()
            return

        self.notify(f"TV show '{item.get('name')}' selected. Choose a season…")

        seasons = get_seasons(tmdb_id)
        if not seasons:
            self.notify("No seasons returned for that show.")
            return

        await self.app.push_screen(SeasonsOptionScreen(seasons, tmdb_id, item.get("name")))


class SearchOptionApp(App):
    """App orchestrating search term -> media type -> results workflow."""

    CSS = "OptionList { height: 100%; }"
    BINDINGS = [
        ("escape", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.search_term: str | None = None

    def on_mount(self):
        self.push_screen(SearchScreen())

    async def handle_search_term(self, term: str):
        self.search_term = term
        await self.push_screen(MediaTypeScreen())

    async def load_results(self, media_type: str):
        if not self.search_term:
            self.notify("Enter a search term first.")
            return

        if media_type not in {"movie", "tv"}:
            self.notify("Invalid choice.")
            return

        if media_type == "movie":
            results = search_movies(self.search_term)
        else:
            results = search_tv_shows(self.search_term)

        await self.push_screen(ResultsOptionScreen(results, media_type))


def main():
    SearchOptionApp().run()


if __name__ == "__main__":
    main()
