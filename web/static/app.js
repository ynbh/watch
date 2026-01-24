const listEl = document.getElementById("list");
const contextTitle = document.getElementById("context-title");
const contextSub = document.getElementById("context-sub");
const cmdk = document.getElementById("cmdk");
const cmdkInput = document.getElementById("cmdk-input");
const cmdkButton = document.getElementById("cmdk-button");
const playerShell = document.getElementById("player-shell");
const player = document.getElementById("player");

const POSTER_BASE = "https://image.tmdb.org/t/p/w342";

const state = {
  query: "",
  page: 1,
  totalPages: 1,
  filter: "all",
  mode: "idle",
  results: [],
  items: [],
  selection: 0,
  showId: null,
  showName: "",
  seasonNumber: null,
};

const formatYear = (dateValue) => {
  if (!dateValue || dateValue.length < 4) return "N/A";
  return dateValue.slice(0, 4);
};

const formatRating = (rating, popularity) => {
  if (rating == null) {
    return popularity == null ? "" : `pop ${Math.round(popularity)}`;
  }
  return `rating ${rating.toFixed(1)}`;
};

const shortenText = (text, maxLength) => {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 1))}…`;
};

const buildResultLabel = (item) => {
  const year = formatYear(item.release_date);
  const rating = formatRating(item.rating, item.popularity);
  const meta = rating ? `${year} | ${rating}` : year;
  const posterUrl = item.poster_path ? `${POSTER_BASE}${item.poster_path}` : "";
  return {
    title: item.name,
    meta,
    blurb: shortenText(item.overview || "No overview available.", 160),
    tag: item.media_type === "movie" ? "movie" : "tv",
    posterUrl,
  };
};

const setContext = (title, sub) => {
  contextTitle.textContent = title;
  contextSub.textContent = sub;
};

const setPlayer = (url) => {
  if (!url) {
    playerShell.classList.remove("active");
    player.src = "";
    return;
  }
  player.src = url;
  playerShell.classList.add("active");
};

player.addEventListener("load", () => {
  const sandboxValue = player.getAttribute("sandbox");
  if (!sandboxValue) return;
  // briefly drop sandbox to mimic the launcher behavior
  player.removeAttribute("sandbox");
  requestAnimationFrame(() => {
    player.setAttribute("sandbox", sandboxValue);
  });
});

const openCmdk = () => {
  cmdk.classList.add("active");
  cmdk.setAttribute("aria-hidden", "false");
  cmdkInput.value = state.query;
  cmdkInput.focus();
  cmdkInput.select();
};

const closeCmdk = () => {
  cmdk.classList.remove("active");
  cmdk.setAttribute("aria-hidden", "true");
};

const apiGet = async (url) => {
  const response = await fetch(url, { credentials: "same-origin" });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.error || "Request failed");
  }
  return data;
};

const rebuildList = () => {
  listEl.innerHTML = "";
  if (!state.items.length) {
    const empty = document.createElement("li");
    empty.className = "list-empty";
    empty.textContent = "No items to show.";
    listEl.appendChild(empty);
    return;
  }

  state.items.forEach((item, index) => {
    const li = document.createElement("li");
    li.className = "list-item" + (index === state.selection ? " selected" : "");
    li.dataset.index = String(index);

    const title = document.createElement("div");
    title.className = "title";

    if (item.kind === "result") {
      const label = buildResultLabel(item.data);
      if (label.posterUrl) {
        li.classList.add("poster-item");
        const img = document.createElement("img");
        img.className = "poster";
        img.alt = `${label.title} poster`;
        img.loading = "lazy";
        img.src = label.posterUrl;
        li.appendChild(img);
      }

      const copy = document.createElement("div");
      copy.className = "copy";
      li.appendChild(copy);

      copy.appendChild(title);
      title.textContent = label.title;

      const meta = document.createElement("small");
      meta.textContent = label.meta;
      copy.appendChild(meta);

      const tag = document.createElement("div");
      tag.className = "tag";
      tag.textContent = label.tag;
      copy.appendChild(tag);

      const blurb = document.createElement("div");
      blurb.className = "muted";
      blurb.textContent = label.blurb;
      copy.appendChild(blurb);
    } else {
      li.appendChild(title);
      title.textContent = item.title;
      if (item.meta) {
        const meta = document.createElement("small");
        meta.textContent = item.meta;
        li.appendChild(meta);
      }
    }

    listEl.appendChild(li);
  });
};

const updateSelectionDOM = () => {
  // keep selection snappy without rebuilding the list
  const previous = listEl.querySelector(".list-item.selected");
  if (previous) {
    previous.classList.remove("selected");
  }
  const next = listEl.querySelector(`[data-index="${state.selection}"]`);
  if (next) {
    next.classList.add("selected");
  }
};

const ensureSelectionInView = () => {
  const selected = listEl.children[state.selection];
  if (!selected) return;
  selected.scrollIntoView({ block: "nearest" });
};

const setSelection = (index, { scroll = true } = {}) => {
  if (Number.isNaN(index)) return;
  state.selection = index;
  updateSelectionDOM();
  if (scroll) ensureSelectionInView();
};

const setItems = (items, selection = 0) => {
  state.items = items;
  state.selection = Math.min(selection, items.length - 1);
  if (state.selection < 0) state.selection = 0;
  rebuildList();
  ensureSelectionInView();
};

const applyFilter = (filter) => {
  if (state.filter === filter) return;
  state.filter = filter;
  renderResults();
};

const renderResults = () => {
  const filtered = state.results.filter((item) => {
    if (state.filter === "movie") return item.media_type === "movie";
    if (state.filter === "tv") return item.media_type === "tv";
    return true;
  });

  const items = filtered.map((item) => ({ kind: "result", data: item }));

  if (state.page > 1) {
    items.push({ kind: "page", action: "prev", title: "Previous page" });
  }
  if (state.page < state.totalPages) {
    items.push({ kind: "page", action: "next", title: "Next page" });
  }

  setItems(items);
  setContext(
    `Results for "${state.query}"`,
    `Filter: ${state.filter.toUpperCase()} | Page ${state.page} / ${state.totalPages}`
  );
  state.mode = "results";
};

const loadResults = async (page = 1) => {
  if (!state.query) return;
  const payload = await apiGet(`/api/search?query=${encodeURIComponent(state.query)}&page=${page}`);
  state.results = payload.results || [];
  state.page = payload.page || page;
  state.totalPages = payload.total_pages || 1;
  renderResults();
};

const loadSeasons = async (showId, showName) => {
  const payload = await apiGet(`/api/seasons?show_id=${showId}`);
  const seasons = payload.seasons || [];
  const items = seasons.map((season) => ({
    kind: "season",
    data: season,
    title: season.name || `Season ${season.season_number}`,
    meta: `Episodes: ${season.episode_count || "N/A"}`,
  }));
  setItems(items);
  state.mode = "seasons";
  state.showId = showId;
  state.showName = showName;
  setContext(`Choose a season`, showName);
};

const loadEpisodes = async (seasonNumber) => {
  const payload = await apiGet(`/api/episodes?show_id=${state.showId}&season_number=${seasonNumber}`);
  const episodes = payload.episodes || [];
  const items = episodes.map((episode) => ({
    kind: "episode",
    data: episode,
    title: `E${episode.episode_number}: ${episode.name}`,
    meta: episode.overview ? episode.overview : "",
  }));
  setItems(items);
  state.mode = "episodes";
  state.seasonNumber = seasonNumber;
  setContext(`Season ${seasonNumber}`, state.showName);
};

const playMovie = async (tmdbId) => {
  const payload = await apiGet(`/api/embed?media_type=movie&tmdb_id=${tmdbId}`);
  setPlayer(payload.url);
};

const playEpisode = async (tmdbId, seasonNumber, episodeNumber) => {
  const payload = await apiGet(
    `/api/embed?media_type=tv&tmdb_id=${tmdbId}&season=${seasonNumber}&episode=${episodeNumber}`
  );
  setPlayer(payload.url);
};

const selectItem = async () => {
  const item = state.items[state.selection];
  if (!item) return;

  if (state.mode === "results" && item.kind === "result") {
    if (item.data.media_type === "movie") {
      await playMovie(item.data.id);
      setContext(item.data.name, "Movie playback");
      return;
    }
    if (item.data.media_type === "tv") {
      await loadSeasons(item.data.id, item.data.name);
      return;
    }
  }

  if (state.mode === "results" && item.kind === "page") {
    if (item.action === "prev") await loadResults(state.page - 1);
    if (item.action === "next") await loadResults(state.page + 1);
    return;
  }

  if (state.mode === "seasons" && item.kind === "season") {
    await loadEpisodes(item.data.season_number);
    return;
  }

  if (state.mode === "episodes" && item.kind === "episode") {
    await playEpisode(state.showId, state.seasonNumber, item.data.episode_number);
    setContext(`S${state.seasonNumber} E${item.data.episode_number}`, item.data.name);
  }
};

const moveSelection = (delta) => {
  if (!state.items.length) return;
  const nextIndex = Math.min(Math.max(state.selection + delta, 0), state.items.length - 1);
  setSelection(nextIndex);
};

const handleBack = () => {
  if (cmdk.classList.contains("active")) {
    closeCmdk();
    return;
  }
  if (state.mode === "episodes") {
    loadSeasons(state.showId, state.showName);
    return;
  }
  if (state.mode === "seasons") {
    renderResults();
    return;
  }
  if (state.mode === "results") {
    setContext("Search to begin", "Cmd+K to open the command bar.");
  }
};

const handleSearchSubmit = async () => {
  const value = cmdkInput.value.trim();
  if (!value) return;
  state.query = value;
  closeCmdk();
  await loadResults(1);
};

const listIndexFromEvent = (event) => {
  // avoid per-item listeners for snappy pointer handling
  const target = event.target;
  if (!(target instanceof HTMLElement)) return null;
  const li = target.closest(".list-item");
  if (!li) return null;
  const index = Number(li.dataset.index);
  if (Number.isNaN(index)) return null;
  return index;
};

cmdkButton.addEventListener("click", () => {
  openCmdk();
});

cmdkInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    handleSearchSubmit();
  }
  if (event.key === "Escape") {
    event.preventDefault();
    closeCmdk();
  }
});

window.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    openCmdk();
    return;
  }

  if (cmdk.classList.contains("active")) return;

  if (event.key === "ArrowDown") {
    event.preventDefault();
    moveSelection(1);
  }
  if (event.key === "ArrowUp") {
    event.preventDefault();
    moveSelection(-1);
  }
  if (event.key === "Enter") {
    event.preventDefault();
    selectItem();
  }
  if (event.key === "Escape") {
    event.preventDefault();
    handleBack();
  }
  if (event.key.toLowerCase() === "a") {
    applyFilter("all");
  }
  if (event.key.toLowerCase() === "m") {
    applyFilter("movie");
  }
  if (event.key.toLowerCase() === "t") {
    applyFilter("tv");
  }
  if (event.key.toLowerCase() === "n" && state.page < state.totalPages) {
    loadResults(state.page + 1);
  }
  if (event.key.toLowerCase() === "p" && state.page > 1) {
    loadResults(state.page - 1);
  }
});

listEl.addEventListener("click", (event) => {
  const index = listIndexFromEvent(event);
  if (index === null) return;
  setSelection(index);
});

listEl.addEventListener("dblclick", (event) => {
  const index = listIndexFromEvent(event);
  if (index === null) return;
  setSelection(index);
  selectItem();
});

setContext("Search to begin", "Cmd+K to open the command bar.");
