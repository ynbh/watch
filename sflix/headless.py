from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from constants import HOME
import requests

from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.common.exceptions import TimeoutException


LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    # "--headless=new"
]


def launch_headless():
    options = Options()
    for arg in LAUNCH_ARGS:
        options.add_argument(arg)
    options.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"})
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument("--disable-features=BlockThirdPartyCookies")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.cookies": 1,
        "profile.block_third_party_cookies": False,
    })
    
    driver = webdriver.Chrome(options=options)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

    
def set_season(driver, season_id, timeout=5, debug=False):
    """
    ensure the requested season tab is active by opening the dropdown when needed,
    clicking the season trigger, and waiting for the ajax-backed episode pane to
    populate so downstream selectors only see episodes from that season.
    """
    wait = Wait(driver, timeout)
    
    # the selector for the dropdown toggle that reveals the season list
    toggle_sel = "#ssc-sort"
    
    # the selector that targets the specific season link
    link_sel = f'a#ss-{season_id}[href="#ss-episodes-{season_id}"]'
    
    # the selector for the season episode pane that should become active
    pane_sel = f'#ss-episodes-{season_id}'

    # anchor present
    # wait until the season link is present in the dom
    link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, link_sel)))

    # if the link is not already active we must expose it through the dropdown
    if "active" not in link.get_attribute("class").split():
        try:
            # wait until the dropdown toggle is clickable and use a native click
            toggle = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, toggle_sel)))
            # activate the dropdown via a normal click
            toggle.click()
        except Exception:
            # if the native click fails, fall back to a javascript-driven click
            toggle = driver.find_element(By.CSS_SELECTOR, toggle_sel)
            # activate the dropdown by executing a javascript click
            driver.execute_script("arguments[0].click();", toggle)

    try:
        # open the season tab with a click, if native click does not work use js
        link.click()
    except Exception:
        # trigger the episode click via javascript to avoid intercepted clicks
        driver.execute_script("arguments[0].click();", link)

    # pane present
    # wait for the season pane node to exist in the dom
    pane = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, pane_sel)))
    # block until the pane gains both active and show classes
    wait.until(lambda d: 'active' in pane.get_attribute('class') and 'show' in pane.get_attribute('class'))

    # ensure episodes exist
    try:
        # wait for at least one episode card to appear inside the pane
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'{pane_sel} .eps-item[data-id]')))
    except Exception:
        if debug:
            cnt = len(driver.find_elements(By.CSS_SELECTOR, f'{pane_sel} .eps-item[data-id]'))
            print(f'[debug] Episodes present after season switch: {cnt}')
            
    # return the pane selector so we can use it to get the watch-id for the specified episode in data_watch_id
    return pane_sel

def data_watch_id(url, episode_id, season_id, driver=None):
    """
    run a headless browser through the season dropdown, pick the target episode,
    wait for the watch page state to settle, and read the resulting data-watch-id from the final url segment.
    """
    own_driver = False
    if driver is None:
        driver = launch_headless()
        own_driver = True
    try:
        # load the media page that lists the target episode
        driver.get(url)
        wait = Wait(driver, 15)
        
        # by default, it is season 1. season_id's are used to determine what dropdown element to select
        # if using the cli, season_id will always be populated 

        # activate that season and capture its pane selector
        pane_sel = set_season(driver, season_id, timeout=5)

        # find the pane that has the episode_id listed
        episode_selector = f'{pane_sel} .eps-item[data-id="{episode_id}"]'
        # wait until the target episode node loads
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, episode_selector)))
        # wait until the episode becomes clickable
        episode = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, episode_selector)))

        # fetch the anchor tag that triggers navigation to video itself
        link = episode.find_element(By.CSS_SELECTOR, "a")
        # capture the current page url for later comparison, since we rely on it to check for the watch_id loading 
        old_url = driver.current_url
        driver.execute_script("arguments[0].click();", link)
        
        def navigation_complete(d):
            # determine whether navigation to the watch page has finished
            # see if the current url differs from the original
            return d.current_url != old_url

        try:
            # wait until navigation_complete reports success
            wait.until(navigation_complete)
        except TimeoutException:
            # raise when we never observe the watch page transition
            raise RuntimeError("Episode click did not navigate to watch page.")

        # seed a holder for the eventual watch id
        watch_id = None

        # derive the id from the navigation url 
        if not watch_id:
            # capture the watch page url after the click
            new_url = driver.current_url
            # isolate the trailing segment that holds the id
            tail = new_url.split(".")[-1]
            # strip query, hash, and path fragments from the segment
            watch_id = tail.split("?")[0].split("#")[0].split("/")[0]
            if not watch_id:
                # stop execution when no identifier can be determined
                raise RuntimeError("Failed to derive watch ID after navigation.")

        # wait for the watch page document to finish loading so downstream fetches inherit the session state
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        return watch_id
    finally:
        # ensure the browser session is terminated cleanly
        if own_driver:
            driver.quit()


def get_embed_link(data_watch_id, driver=None, timeout=10):
    """
    obtain the embed link for the given watch id. when a selenium driver is supplied,
    the ajax request is executed within the active browser session so that cookies and
    headers established on sflix persist through the request.
    """
    if driver is None:
        url = f"{HOME}/ajax/episode/sources/{data_watch_id}"
        response = requests.get(url)
        payload = response.json()
        return payload.get("link")

    driver.set_script_timeout(timeout)
    result = driver.execute_async_script(
        """
        const watchId = arguments[0];
        const done = arguments[arguments.length - 1];
        fetch(`/ajax/episode/sources/${watchId}`, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(resp => {
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            return resp.json();
        })
        .then(data => done({ ok: true, link: (data && data.link) || null }))
        .catch(err => done({ ok: false, error: err ? err.message : 'Request failed' }));
        """,
        str(data_watch_id),
    )

    if not isinstance(result, dict):
        raise RuntimeError("Unexpected response while fetching embed link.")
    if not result.get("ok"):
        raise RuntimeError(f"Failed to fetch embed link: {result.get('error')}")

    link = result.get("link")
    if not link:
        raise RuntimeError("Sources payload did not include a link field.")

    return link


def get_video_url(watch_id, driver, timeout=20):
    """
    fetch the jwplayer video url by requesting the ajax sources endpoint within
    the active sflix session, navigating to the returned embed link, and
    interrogating the jwplayer instance for its active media file.
    """
    if driver is None:
        raise ValueError("A Selenium driver instance is required to preserve the session context.")

    link = get_embed_link(watch_id, driver=driver, timeout=timeout)
    if not link:
        raise RuntimeError("Sources payload did not include a link field.")

    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride",
        {
            "userAgent": driver.execute_script("return navigator.userAgent;"),
            "platform": "MacIntel",
        },
    )

    driver.execute_script("window.location.href = arguments[0];", link)

    wait = Wait(driver, timeout)

    # block until the embed document finishes loading
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

    def _jwplayer_ready(d):
        script = (
            "return (typeof window.jwplayer === 'function' && "
            "jwplayer().getPlaylistItem && jwplayer().getPlaylistItem());"
        )
        return d.execute_script(script)

    wait.until(_jwplayer_ready)

    video_url = driver.execute_script("return jwplayer().getPlaylistItem().file;")
    if not isinstance(video_url, str) or not video_url:
        raise RuntimeError("JWPlayer did not expose a playable video URL.")

    return video_url
 
