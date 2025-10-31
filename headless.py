import time
import asyncio
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from constants import HOME 
import requests 


LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]


def launch_headless():
    options = Options()
    options.add_argument("--headless")
    for arg in LAUNCH_ARGS:
        options.add_argument(arg)
    
    driver = webdriver.Chrome(options=options)
    
    # Apply selenium-stealth
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

def check_if_automation(url):
    driver = launch_headless()
    driver.get(url)
    driver.quit()

def data_watch_id(url, id):
    
    driver = launch_headless() 
    driver.get(url)
    
    # select the div with data-id == id 
    season_link_selector = f'div[data-id="{id}"] a'
    
    # wait for element and click
    wait = WebDriverWait(driver, 10)
    season_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, season_link_selector)))
    season_link.click()
    
    # wait for navigation to complete
    time.sleep(2)  # simple wait for page load
    
    # wait for the detail_page-media div to load
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.detail_page-media')))
    
    # extract the data-watch-id from the detail_page-media div
    detail_div = driver.find_element(By.CSS_SELECTOR, 'div.detail_page-media')
    data_watch_id = detail_div.get_attribute('data-watch-id')
    
    driver.quit()
    return data_watch_id


def get_embed_link(data_watch_id):
    url = f"{HOME}/ajax/episode/sources/{data_watch_id}"
    request = requests.get(url)
    json = request.json() 
    return json.get("link")

def get_m3u8(data_watch_id: str):
    embed_link = get_embed_link(data_watch_id)
    print(embed_link)  # keep this for debugging
    if not embed_link:
        raise RuntimeError("No embed_link returned by AJAX endpoint")

    driver = launch_headless()
    try:
        # many embeds require their own referer or the parent site
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": driver.execute_script("return navigator.userAgent;"),
            "platform": "MacIntel"
        })
        
        driver.get(embed_link)
        
        # wait for jwplayer to be available and have playlist item
        wait = WebDriverWait(driver, 20)
        wait.until(lambda d: d.execute_script(
            "return window.jwplayer && jwplayer().getPlaylistItem && jwplayer().getPlaylistItem()"
        ))
        
        m3u8 = driver.execute_script("return jwplayer().getPlaylistItem().file")
        return m3u8 if isinstance(m3u8, str) else None
    finally:
        driver.quit()



# m3u8 = get_m3u8("4873288")
# print("RESULT:", m3u8)    
# check_if_automation("https://arh.antoinevastel.com/bots/areyouheadless")   