from soup import soupify_url as soupify
from constants import HOME 



seasons = lambda media_id: f"{HOME}/ajax/season/list/{media_id}"
episodes = lambda season_id: f"{HOME}/ajax/season/episodes/{season_id}"

"""
https://sflix.ps/ajax/season/list/39514  -> for season IDs
https://sflix.ps/ajax/season/episodes/324 -> for all episodes in each season 
"""
def get_seasonal_dets(id):

    url = seasons(id)
    soup = soupify(url)
    
    container = soup.find(
        "div",
        class_=lambda c: c and "dropdown-menu" in c.split() and "dropdown-menu-model" in c.split()
    )
    items = container.select("a.dropdown-item") if container else []
    results = []
    
    for item in items:
        season_id = item["data-id"] if item.has_attr("data-id") else None
        season_name = item.get_text(strip=True)
        results.append({season_name: int(season_id)}) 
    return results 

"""
movie_type = 1 -> movie 
movie_tyope = 2 -> tv show
"""
def get_media_info(movie_type, media_id):
    
    if movie_type == 1:
        pass 
    elif movie_type == 2:
        seasons = get_seasonal_dets(media_id)
        return seasons 
    else:
        raise ValueError("Invalid movie type specified.")    


def get_episodes_for_season(season_id):
    
    url = episodes(season_id)
    soup = soupify(url)
    
    container = soup.find(
        "div",
        class_=lambda c: c and "swiper-wrapper" in c.split()
    )
    
    items = container.select("div.swiper-slide") if container else []
    results = []
    for i, item in enumerate(items):

        flw_item = item.select_one(".flw-item")
        episode_id = flw_item.get("data-id") if flw_item and flw_item.has_attr("data-id") else None
        
        # episode name lives under film-detail div > h3 in class film-name, inside a, where the title exists 
        episode_name = item.select_one(".film-detail .film-name a") 
        episode_name = episode_name.get("title") if episode_name and episode_name.has_attr("title") else (episode_name.get_text(strip=True) if episode_name else None)
        ep_number = i + 1
        
        results.append({"id": episode_id, "episode_number": ep_number, "episode_name": episode_name}) 
    return results 

