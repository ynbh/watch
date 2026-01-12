import textwrap
import threading

from rich.text import Text
from textual.app import App
from textual.screen import Screen
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from .tmdb.media import (
    get_episodes,
    get_seasons,
    search_multi,
    GET_SHOW_EMBED,
    GET_MOVIE_EMBED,
)
from .launcher import launch_media


class SearchScreen(Screen):
    """Initial screen where the user types the TMDB search term."""

    def compose(self):
        yield Static("What do you wanna watch today?")
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

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("n", "next_page", "Next page"),
        ("p", "prev_page", "Previous page"),
        ("a", "filter_all", "All"),
        ("m", "filter_movies", "Movies"),
        ("t", "filter_tv", "TV"),
    ]

    def __init__(self, results, page, total_pages, filter_type="all"):
        super().__init__()
        self.results = results or []
        self.page = page
        self.total_pages = total_pages
        self.lookup = {str(item.get("id")): item for item in self.results}
        self.highlighted_item_id = None
        self.filter_type = filter_type

    def _format_year(self, release_date):
        if not release_date or len(release_date) < 4:
            return "N/A"
        return release_date[:4]

    def _format_rating(self, rating, popularity):
        if rating is None:
            if popularity is None:
                return None
            return f"pop {popularity:.0f}"
        return f"★ {rating:.1f}"

    def _build_label(self, item, highlighted):
        title = item.get("name") or "Untitled"
        year = self._format_year(item.get("release_date"))
        rating_text = self._format_rating(item.get("rating"), item.get("popularity"))
        overview = item.get("overview") or "No overview available."
        blurb = textwrap.shorten(overview, width=80, placeholder="…")
        media_type = item.get("media_type")

        type_label = None
        type_style = None
        if media_type == "movie":
            type_label = "movie"
            type_style = "dim #fecaca"
        elif media_type == "tv":
            type_label = "tv series"
            type_style = "dim #fdba74"

        meta = year
        if rating_text:
            meta = f"{meta} ★{rating_text.replace('★ ', '')}"

        label = Text(f"{title} ({meta})", style="bold")
        if type_label:
            label.append(" · ")
            label.append(type_label, style=type_style)

        overview_style = None if highlighted else "dim"
        label.append(f"\n{blurb}", style=overview_style)
        return label

    def compose(self):
        page_label = f" (Page {self.page} of {self.total_pages})" if self.total_pages > 1 else ""
        yield Static(self._header_text(page_label), id="results-header")

        option_list = OptionList(id="results")

        self._populate_options(option_list)

        yield option_list
        yield Footer()

    def on_mount(self):
        self._refresh_header()
        option_list = self.query_one(OptionList)
        if option_list.highlighted is not None:
            option = option_list.get_option_at_index(option_list.highlighted)
            self._set_highlighted_item(option.id)

    def _set_highlighted_item(self, option_id):
        if option_id == self.highlighted_item_id:
            return

        option_list = self.query_one(OptionList)
        if self.highlighted_item_id in self.lookup:
            # restore prior row styling when highlight moves
            previous = self.lookup[self.highlighted_item_id]
            prev_index = option_list.get_option_index(self.highlighted_item_id)
            option_list.replace_option_prompt_at_index(
                prev_index, self._build_label(previous, highlighted=False)
            )

        if option_id in self.lookup:
            # emphasize the newly highlighted row
            current = self.lookup[option_id]
            current_index = option_list.get_option_index(option_id)
            option_list.replace_option_prompt_at_index(
                current_index, self._build_label(current, highlighted=True)
            )
            self.highlighted_item_id = option_id
        else:
            self.highlighted_item_id = None

    async def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        self._set_highlighted_item(event.option.id)

    def _header_text(self, page_label):
        filter_label = self.filter_type.replace("_", " ").title()
        return f"Select a title for '{self.app.search_term}':{page_label}  Filter: {filter_label}"

    def _refresh_header(self):
        page_label = f" (Page {self.page} of {self.total_pages})" if self.total_pages > 1 else ""
        header = self.query_one("#results-header", Static)
        header.update(self._header_text(page_label))

    def _filtered_results(self):
        if self.filter_type == "movie":
            return [item for item in self.results if item.get("media_type") == "movie"]
        if self.filter_type == "tv":
            return [item for item in self.results if item.get("media_type") == "tv"]
        return self.results

    def _populate_options(self, option_list):
        option_list.clear_options()
        results = self._filtered_results()
        if not results:
            option_list.add_option(Option("No results", id="none"))
        else:
            for item in results:
                tmdb_id = item.get("id")
                label = self._build_label(item, highlighted=False)
                option_list.add_option(Option(label, id=str(tmdb_id)))

        if self.page > 1:
            option_list.add_option(Option("Previous page", id="prev-page"))
        if self.page < self.total_pages:
            option_list.add_option(Option("Next page", id="next-page"))

    def _apply_filter(self, filter_type):
        if self.filter_type == filter_type:
            return
        self.filter_type = filter_type
        self.highlighted_item_id = None
        option_list = self.query_one(OptionList)
        self._populate_options(option_list)
        self._refresh_header()

    def update_results(self, results, page, total_pages, filter_type):
        # refresh list state without rebuilding the screen
        self.results = results or []
        self.page = page
        self.total_pages = total_pages
        self.lookup = {str(item.get("id")): item for item in self.results}
        self.filter_type = filter_type
        self.highlighted_item_id = None
        option_list = self.query_one(OptionList)
        self._populate_options(option_list)
        self._refresh_header()
        if option_list.highlighted is not None:
            option = option_list.get_option_at_index(option_list.highlighted)
            self._set_highlighted_item(option.id)

    async def action_filter_all(self):
        self._apply_filter("all")

    async def action_filter_movies(self):
        self._apply_filter("movie")

    async def action_filter_tv(self):
        self._apply_filter("tv")

    async def action_next_page(self):
        if self.page < self.total_pages:
            await self.app.load_results(page=self.page + 1, filter_type=self.filter_type)

    async def action_prev_page(self):
        if self.page > 1:
            await self.app.load_results(page=self.page - 1, filter_type=self.filter_type)

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        event.stop()
        option_id = event.option.id

        if option_id == "prev-page":
            await self.app.load_results(page=self.page - 1, filter_type=self.filter_type)
            return

        if option_id == "next-page":
            await self.app.load_results(page=self.page + 1, filter_type=self.filter_type)
            return

        if option_id == "none":
            self.notify("Nothing to select.")
            return

        item = self.lookup.get(option_id)
        if not item:
            self.notify("Unable to load selection.")
            return

        tmdb_id = item.get("id")

        media_type = item.get("media_type")
        if media_type == "movie":
            movie_embed_url = GET_MOVIE_EMBED(tmdb_id)
            self.notify(f"Movie '{item.get('name')}' queued")
            threading.Thread(target=launch_media, args=(movie_embed_url,), daemon=True).start()
            return

        if media_type != "tv":
            self.notify("Unsupported media type.")
            return

        self.notify(f"TV show '{item.get('name')}' selected. Choose a season…")

        seasons = get_seasons(tmdb_id)
        if not seasons:
            self.notify("No seasons returned for that show.")
            return

        await self.app.push_screen(SeasonsOptionScreen(seasons, tmdb_id, item.get("name")))


class SearchOptionApp(App):
    """App orchestrating search term -> media type -> results workflow."""

    CSS = """
    App {
        background: #110808;
        color: #f8fafc;
    }

    OptionList {
        height: 100%;
        border: round #b91c1c;
        background: #140909;
    }

    OptionList:focus {
        border: round #ef4444;
    }

    Input {
        border: round #b91c1c;
        background: #120909;
    }

    Input:focus {
        border: round #ef4444;
    }

    Footer {
        background: #1a0b0b;
        color: #fecaca;
    }

    Static {
        color: #f8fafc;
    }
    """
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
        await self.load_results(page=1, filter_type="all")

    async def load_results(self, page: int, filter_type: str):
        if not self.search_term:
            self.notify("Enter a search term first.")
            return

        payload = search_multi(self.search_term, page=page)
        screen = self.screen
        if isinstance(screen, ResultsOptionScreen):
            # update current results view in place to avoid screen flicker
            screen.update_results(
                payload.get("results", []),
                payload.get("page", page),
                payload.get("total_pages", 1),
                filter_type=filter_type,
            )
            return

        # initial results view for a new search
        await self.push_screen(
            ResultsOptionScreen(
                payload.get("results", []),
                payload.get("page", page),
                payload.get("total_pages", 1),
                filter_type=filter_type,
            )
        )


def main():
    SearchOptionApp().run()


if __name__ == "__main__":
    main()
