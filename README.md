# watch-tmdb

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

Option 1: save it with the CLI:

```bash
uv run watch set-env <your read access token>
```

Option 2: create a `.env` file in the project root:

`TMDB_READ_ACCESS_TOKEN=<your read access token>` 

## Run

From the project root:

```bash
uv run watch
```

Install with pipx from git:

```bash
pipx install git+https://github.com/you/watch-tmdb
```
