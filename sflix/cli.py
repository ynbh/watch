from sflix.homepage import get_relevant_results
from constants import HOME
from sflix.media import get_media_info, get_episodes_for_season
from sflix.headless import (
    data_watch_id as fetch_data_watch_id,
    get_video_url,
    launch_headless,
)


from textual.app import App
from textual.screen import Screen
from textual.widgets import DataTable, Static, Footer, Header


class HelpScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Close")]
    def compose(self):
        yield Static(
            "\nControls\n"
            "Enter: Select row\n"
            "Esc: Back\n"
            "Up/Down: Move cursor\n"
            "h: Open this help screen\n",
            id="help",
        )

class EpisodesScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    def __init__(self, episodes_data, season_id=None, media_id=None, media_url=None):
        super().__init__()
        self.episodes_data = episodes_data
        self.media_id = media_id
        self.season_id = season_id
        self.media_url = media_url
        
    def compose(self):
        dt = DataTable(id="episodes_table", zebra_stripes=True)
        if not self.episodes_data:
            self.notify("No episodes found!")
            return
        
        dt.add_column("Episode Number")
        dt.add_column("Episode Name")
        dt.add_column("ID")

        
        for object in self.episodes_data:
            ep_number = object['episode_number']
            ep_name = object['episode_name']
            id = object['id']
            dt.add_row(ep_number, ep_name, id)
        
        dt.cursor_type = "row"
        dt.focus()
        yield dt 
        yield Footer()  
        
    async def on_data_table_row_selected(self, event):
        event.stop()
        
        row = event.control.get_row(event.row_key)
        episode_number, episode_name, id = row[0], row[1], row[2]
        
        """
        now that we have information about what episode the user selected, 
        we launch a headless instance of chrome to get where the episode lives, since these IDs are loaded dynamically 
        for each server 
        and we need to fetch the actual video URL to play it
         
        4873288
        once we have the data watch id, we can request:
        https://sflix.ps/ajax/episode/sources/[data-watch-id]
        
        to get the video 
        """
        
        media_url = self.media_url 
        # internal episode ID used to lookup the episode watch id 
        driver = launch_headless()
        try:
            watch_id = fetch_data_watch_id(media_url, id, season_id=self.season_id, driver=driver)
            video_url = get_video_url(watch_id, driver=driver)
            self.notify(f"{watch_id} - {video_url}")
        finally:
            driver.quit()


    
class SeasonScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    CSS = "DataTable { height: 100%; width: 100%; }" 
    
    def __init__(self, seasons_data, media_title=None, media_id = None, media_url = None):
        super().__init__()
        self.seasons_data = seasons_data
        self.media_id = media_id
        self.media_title = media_title
        self.media_url = media_url
        
    async def on_button_pressed(self, _):
        await self.app.pop_screen()  # programmatic back
        
    
    def compose(self):
        dt = DataTable(id="seasons_table", zebra_stripes=True)
        if not self.seasons_data:
            self.notify("No seasons found!")
            return
        
        dt.add_column("Season")
        dt.add_column("Season ID")
        
        for season_dict in self.seasons_data:
            for season_name, season_id in season_dict.items():
                dt.add_row(season_name, str(season_id))
        
        dt.cursor_type = "row"
        dt.focus()
        yield dt 
        yield Footer()
    
    async def on_data_table_row_selected(self, event):
        event.stop()

        row = event.control.get_row(event.row_key)
        season_name, season_id = row[0], row[1]
        
        season_episodes = get_episodes_for_season(season_id)
        
        if season_episodes:
            await self.app.push_screen(EpisodesScreen(season_episodes, season_id, self.media_id, self.media_url))

class MediaScreen(App):
    
    CSS = "DataTable { height: 100%; width: 100%; }" 
    # SCREENS = {"season_screen": SeasonScreen}
    BINDINGS = [
        ("escape", "quit", "Quit"),
        ("h", "help", "Help")
    ]
    SCREENS = {
        "episodes": EpisodesScreen,
        "seasons": SeasonScreen
    }
    
    def __init__(self, data):
        super().__init__()
        self.data = data 
    
    def compose(self):
        dt = DataTable(zebra_stripes=True)
        if not self.data:
            self.notify("No results found!")
            return
        columns = self.data[0].keys()
        for column in columns:
            if column != "poster":
                dt.add_column(column.capitalize())
        
        for item in self.data:
            row = []
            for key in columns:
                if key != "poster":
                    if key == "url":
                        row.append(f"{HOME}{item[key]}" if item[key] else "N/A")
                    else:
                        row.append(str(item[key]) if item[key] is not None else "N/A")
            dt.add_row(*row)
        dt.cursor_type = "row"
        dt.focus()
        yield dt 
        yield Footer()

    async def on_data_table_row_selected(self, event):
        row_key = event.row_key 
        row = event.control.get_row(row_key)

        media_url = row[1]
        media_id = row[2]
        media_title = row[0]
        movie_type = 2 if row[4].lower() == "tv" else 1
        info = get_media_info(movie_type, media_id)
        
        if movie_type == 2 and info:
            await self.push_screen(SeasonScreen(info, media_title, media_id, media_url))
        else:
            print(info)
            
    async def action_help(self):
        await self.push_screen(HelpScreen())

if __name__ == "__main__":
    term = input("Enter search term: ")
    results = get_relevant_results(term)
    media = MediaScreen(data=results)
    media.run()
