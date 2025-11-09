# Tagger

A fast, ad-free way to search and watch shows from your terminal.

## Vidking CLI

`vidking/cli.py` is a standalone Textual TUI that drives the full Vidking flow:

1. **SearchScreen** — enter a TMDB query without leaving the terminal  
2. **MediaTypeScreen** — choose TV or Movie search  
3. **ResultsOptionScreen** — browse formatted TMDB matches (titles + blurbs)  
4. **SeasonsOptionScreen / EpisodesOptionScreen** — drill down to the exact episode, fetching fresh metadata at each step  
5. **Playback** - launches a chromeless player window in a background thread so the TUI stays responsive; natural queueing of next items is planned  
6. **Ad-less** - the video is rendered in a sandboxed iframe to block ad redirects

## Setup

### TMDB API Key

This tool uses TMDB for search and metadata. Follow TMDB’s “Getting Started” guide to create an **API Read Access Token**: <https://developer.themoviedb.org/docs/getting-started>

Create a `.env` file in the project root:

`TMDB_READ_ACCESS_TOKEN=<your read access token>` 

## Run

From the project root:

```bash
./run.sh
```

You might have to update some permissions! If you don't want to do that, just run:
```bash 
python cli.py
```
