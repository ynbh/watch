import requests 
from bs4 import BeautifulSoup
from constants import HOME

search = lambda term: f'{HOME}/search/{term}'

def soupify(url):
    respose = requests.get(url)
    return BeautifulSoup(respose.text, 'html.parser')

def transform_term(term):
    return term.replace(" ", "-").lower()

def get_relevant_results(term):
    
    term = transform_term(term)
    url = search(term)
    soup = soupify(url) 
    container = soup.find(
        "div",
        class_=lambda c: c and "film_list" in c.split() and "film_list-grid" in c.split()
    )
    items = container.select("div.film_list-wrap > div.flw-item")
    results  = []
    for it in items:
        a = it.select_one(".film-poster-ahref") or it.select_one(".film-name a")
        href = a["href"] if a else None
        title = a.get("title") if a and a.has_attr("title") else (a.get_text(strip=True) if a else None)
        
        # year and type (tv/movie)
        year = it.select_one(".fd-infor .fdi-item")
        kind = it.select(".fd-infor .fdi-item")
        year = year.get_text(strip=True) if year else None
        kind = kind[1].get_text(strip=True) if len(kind) > 1 else None
        
        # poster image, try data-src first
        img = it.select_one(".film-poster img")
        poster = img.get("data-src") or img.get("src") if img else None

        results.append({"title": title, "url": href, "year": year, "type": kind, "poster": poster})
    
    return results


    
    