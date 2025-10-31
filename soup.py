from bs4 import BeautifulSoup
from constants import HOME
import requests 

search = lambda term: f'{HOME}/search/{term}'

def soupify_url(url):
    respose = requests.get(url)
    return BeautifulSoup(respose.text, 'html.parser')

def soupify_html(html):
    return BeautifulSoup(html, 'html.parser') 