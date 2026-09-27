const state = { books: [], activeShelf: "saved", preferences: null, toastTimer: null, pendingAccountAction: null };
const storageKey = "कHaniya-v1";
const previousStorageKeys = ["kahaniya-v1", "bookipedia-v1", "bookverse-v1"];
const defaultData = { saved: [], reading: {}, history: [], feedback: {} };
const offlineBooks = [
  { id: "small-things", title: "Small Things Like These", author: "Claire Keegan", isbn: "9780802158741", kind: "fiction", genres: ["Literary fiction", "Historical"], themes: ["kindness", "courage", "community"], moods: ["reflective", "overwhelmed", "tender"], intents: ["make sense of things", "feel hopeful", "slow down"], intensity: 2, complexity: 2, minutes: 95, pace: "Quietly absorbing", description: "A coal merchant in a small Irish town must choose between silence and courage.", tone: "Spare, humane, and quietly luminous", rating: 4.2, year: 2021, badge: "A quiet kind of courage", color: "#9a5b45" },
  { id: "legends-lattes", title: "Legends & Lattes", author: "Travis Baldree", isbn: "9781250886088", kind: "fiction", genres: ["Cozy fantasy", "Romance"], themes: ["fresh starts", "friendship", "community"], moods: ["tender", "lonely", "comforted"], intents: ["escape for a while", "feel comforted", "feel hopeful"], intensity: 1, complexity: 1, minutes: 270, pace: "Cozy", description: "An orc adventurer opens a coffee shop and builds a softer kind of life.", tone: "Low-stakes fantasy with a very good cup of coffee", rating: 4.2, year: 2022, badge: "A soft place to land", color: "#a36b49" },
  { id: "four-thousand-weeks", title: "Four Thousand Weeks", author: "Oliver Burkeman", isbn: "9780374159122", kind: "nonfiction", genres: ["Personal growth", "Philosophy"], themes: ["time", "attention", "meaning"], moods: ["overwhelmed", "restless", "reflective"], intents: ["feel grounded", "make sense of things", "slow down"], intensity: 2, complexity: 3, minutes: 240, pace: "Thoughtful", description: "A practical book about making peace with our limited time and choosing what matters.", tone: "Witty, clear-eyed, and unexpectedly freeing", rating: 4.2, year: 2021, badge: "Permission to do less", color: "#c8a85e" },
  { id: "braiding-sweetgrass", title: "Braiding Sweetgrass", author: "Robin Wall Kimmerer", isbn: "9781571313560", kind: "nonfiction", genres: ["Nature writing", "Essays"], themes: ["nature", "gratitude", "connection"], moods: ["overwhelmed", "reflective", "curious"], intents: ["slow down", "learn something new", "feel grounded"], intensity: 1, complexity: 3, minutes: 510, pace: "Unhurried", description: "A botanist explores what plants can teach us about reciprocity and living well together.", tone: "Restorative, generous, and deeply attentive", rating: 4.6, year: 2013, badge: "A slower way of seeing", color: "#5f7c4f" },
  { id: "project-hail-mary", title: "Project Hail Mary", author: "Andy Weir", isbn: "9780593135204", kind: "fiction", genres: ["Science fiction", "Adventure"], themes: ["friendship", "ingenuity", "survival"], moods: ["restless", "curious", "hopeful"], intents: ["escape for a while", "feel excited", "learn something new"], intensity: 2, complexity: 3, minutes: 510, pace: "Page-turning", description: "A lone astronaut wakes light-years from home with one impossible mission: save humanity.", tone: "High-stakes, clever, and surprisingly warm", rating: 4.7, year: 2021, badge: "One very big problem", color: "#d38a52" },
  { id: "midnight-library", title: "The Midnight Library", author: "Matt Haig", isbn: "9780525559474", kind: "fiction", genres: ["Literary fiction", "Fantasy"], themes: ["second chances", "belonging", "possibility"], moods: ["hopeful", "reflective", "comforted"], intents: ["feel hopeful", "make sense of things", "escape for a while"], intensity: 2, complexity: 2, minutes: 300, pace: "Steady", description: "A library between life and death offers the chance to try another life you could have lived.", tone: "A gentle, hopeful thought experiment", rating: 4.3, year: 2020, badge: "A little perspective", color: "#487d68" },
];

function loadData() {
  try {
    const savedData = localStorage.getItem(storageKey) || previousStorageKeys.map((key) => localStorage.getItem(key)).find(Boolean) || "{}";
    return { ...defaultData, ...JSON.parse(savedData) };
  }
  catch { return { ...defaultData }; }
}
let data = loadData();
function persist() { localStorage.setItem(storageKey, JSON.stringify(data)); updateCounts(); }
function updateCounts() { document.querySelector("#saved-count").textContent = data.saved.length; }
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]); }
function bookCoverUrl(book) { return book.cover_url || (book.isbn ? `https://covers.openlibrary.org/b/isbn/${book.isbn}-L.jpg` : ""); }

function coverMarkup(book, badge = "") {
  const saved = data.saved.includes(book.id);
  const imageUrl = bookCoverUrl(book);
  return `<div class="book-cover-wrap" style="--cover:${book.color}">${badge ? `<span class="cover-badge">${badge}</span>` : ""}${imageUrl ? `<img class="book-cover" loading="lazy" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(book.title)} cover" onerror="this.classList.add('failed')">` : ""}<span class="cover-placeholder">${escapeHtml(book.title)}</span><button class="save-button ${saved ? "saved" : ""}" data-save="${book.id}" type="button" aria-label="${saved ? "Remove from" : "Add to"} reading list">${saved ? "♥" : "♡"}</button></div>`;
}
function cardMarkup(book, reason = "") {
  return `<article class="book-card" data-book="${book.id}" tabindex="0" role="button" aria-label="View ${escapeHtml(book.title)} by ${escapeHtml(book.author)}">${coverMarkup(book, book.badge)}<div class="book-meta"><p class="book-title">${escapeHtml(book.title)}</p><p class="book-author">${escapeHtml(book.author)}</p>${reason ? `<p class="book-reason">${escapeHtml(reason)}</p>` : `<div class="book-foot"><span>${escapeHtml(book.genres[0])}</span><span class="book-rating">★ ${book.rating}</span></div>`}</div></article>`;
}
function featuredBooks() {
  const preferredIds = ["small-things", "legends-lattes", "four-thousand-weeks", "ocean-at-the-end", "atomic-habits", "braiding-sweetgrass"];
  const preferred = preferredIds.map((id) => state.books.find((book) => book.id === id)).filter(Boolean);
  const selectedIds = new Set(preferred.map((book) => book.id));
  const highestRated = [...state.books].sort((a, b) => b.rating - a.rating).filter((book) => !selectedIds.has(book.id));
  return [...preferred, ...highestRated].slice(0, 6);
}
function resultMarkup(book) {
  return `<article class="result-card" data-book="${book.id}" tabindex="0" role="button" aria-label="View ${escapeHtml(book.title)} details">${coverMarkup(book)}<div class="book-meta"><p class="book-title">${escapeHtml(book.title)}</p><p class="book-author">${escapeHtml(book.author)}</p><p class="book-reason">${escapeHtml(book.reasons?.[0] || "A thoughtful match for right now.")}</p></div></article>`;
}
function showToast(message) {
  const toast = document.querySelector("#toast"); toast.textContent = message; toast.classList.add("visible"); clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("visible"), 2100);
}
function renderBooks() {
  document.querySelector("#mood-row").innerHTML = featuredBooks().map((book) => cardMarkup(book)).join("");
  document.querySelector("#popular-row").innerHTML = [...state.books].sort((a, b) => b.rating - a.rating).slice(0, 7).map((book) => cardMarkup(book)).join("");
  document.querySelector("#short-row").innerHTML = [...state.books].sort((a, b) => a.minutes - b.minutes).slice(0, 7).map((book) => cardMarkup(book, `${book.minutes} min · ${book.tone}`)).join("");
  document.querySelector("#catalog-count").textContent = state.books.length;
  renderContinue();
}
function renderContinue() {
  const entries = Object.entries(data.reading).filter(([, progress]) => progress > 0 && progress < 100);
  document.querySelector("#continue-section").classList.toggle("is-hidden", entries.length === 0);
  document.querySelector("#continue-row").innerHTML = entries.map(([id]) => state.books.find((book) => book.id === id)).filter(Boolean).map((book) => cardMarkup(book, `${data.reading[book.id]}% complete`)).join("");
}
async function showRecommendations(preferences) {
  state.preferences = preferences;
  const section = document.querySelector("#recommendation-result"); section.classList.remove("is-hidden");
  document.querySelector("#result-grid").innerHTML = `<p class="section-subtitle">Finding a few books for you…</p>`;
  section.scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    const response = await fetch("/api/recommendations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(preferences) });
    if (!response.ok) throw new Error("Recommendation request failed");
    document.querySelector("#result-grid").innerHTML = (await response.json()).slice(0, 5).map(resultMarkup).join("");
  } catch {
    const matches = state.books.map((book) => {
      let score = (book.moods.includes(preferences.mood) ? 5 : 0) + (book.intents.includes(preferences.intent) ? 4 : 0);
      if (preferences.kind !== "any") score += book.kind === preferences.kind ? 3 : -2;
      if (preferences.depth === "light") score += Math.max(0, 4 - book.complexity) - Math.max(0, book.intensity - 2);
      if (preferences.depth === "deep") score += book.complexity + (book.intensity >= 3 ? 1 : 0);
      score += book.minutes <= preferences.minutes ? 2 : -Math.min(5, Math.floor((book.minutes - preferences.minutes) / 90) + 1);
      const reasons = [];
      if (book.moods.includes(preferences.mood)) reasons.push(`It meets your ${preferences.mood} mood with a ${book.tone.toLowerCase()} feel.`);
      if (book.intents.includes(preferences.intent)) reasons.push(`It fits your wish to ${preferences.intent}.`);
      return { ...book, score, reasons: reasons.length ? reasons : [`A ${book.pace.toLowerCase()} read with themes of ${book.themes.slice(0, 2).join(", ")}.`] };
    }).sort((a, b) => b.score - a.score || b.rating - a.rating);
    document.querySelector("#result-grid").innerHTML = matches.slice(0, 5).map(resultMarkup).join("");
  }
}
function openDetails(bookId) {
  const book = state.books.find((entry) => entry.id === bookId); if (!book) return;
  data.history = [book.id, ...data.history.filter((id) => id !== book.id)].slice(0, 30); persist();
  const progress = data.reading[book.id] || 0; const feedback = data.feedback[book.id];
  document.querySelector("#detail-content").innerHTML = `<div class="detail-layout" style="--cover:${book.color}"><div class="detail-cover"><img src="https://covers.openlibrary.org/b/isbn/${book.isbn}-L.jpg" alt="${escapeHtml(book.title)} cover" onerror="this.style.display='none'"></div><div class="detail-copy"><form method="dialog"><button class="icon-button modal-close" aria-label="Close book details">×</button></form><p class="eyebrow">${escapeHtml(book.badge.toUpperCase())}</p><h2>${escapeHtml(book.title)}</h2><p class="detail-byline">${escapeHtml(book.author)} · ${book.year} · ★ ${book.rating}</p><p>${escapeHtml(book.description)}</p><p>${escapeHtml(book.tone)}. A ${escapeHtml(book.pace.toLowerCase())} ${book.minutes}-minute read.</p><div class="detail-tags">${[...book.genres, ...book.themes.slice(0, 2)].map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div><div class="detail-read"><span>${book.minutes} min read</span><span>${book.kind === "nonfiction" ? "Non-fiction" : "Fiction"} · ${book.complexity <= 1 ? "Easy" : book.complexity === 2 ? "Balanced" : "Layered"}</span></div><div class="detail-actions"><button class="button button-lime" data-detail-reading="${book.id}" type="button">${progress ? "Update progress" : "Start reading"} <span>↗</span></button><button class="button button-outline" data-detail-save="${book.id}" type="button">${data.saved.includes(book.id) ? "♥ Saved" : "♡ Save for later"}</button></div><div class="detail-actions feedback-actions"><button class="button button-outline" data-feedback="like" data-id="${book.id}" type="button">${feedback === "like" ? "♥ Liked" : "♡ Like this"}</button><button class="button button-outline" data-feedback="dislike" data-id="${book.id}" type="button">${feedback === "dislike" ? "Not for me ✓" : "Not for me"}</button></div><div class="progress-control"><label for="progress-range"><span>Reading progress</span><span id="progress-value">${progress}%</span></label><input id="progress-range" type="range" min="0" max="100" step="5" value="${progress}" data-progress="${book.id}" aria-label="Reading progress"></div></div></div>`;
  const detailImage = document.querySelector("#detail-content .detail-cover img");
  const imageUrl = bookCoverUrl(book);
  if (imageUrl) detailImage.src = imageUrl; else detailImage.remove();
  const detailModal = document.querySelector("#detail-modal");
  if (!detailModal.open) detailModal.showModal();
}
function toggleSaved(bookId) {
  if (data.saved.includes(bookId)) { data.saved = data.saved.filter((id) => id !== bookId); showToast("Removed from your shelf"); }
  else { data.saved = [bookId, ...data.saved]; showToast("Saved for a quieter moment"); }
  persist();
  document.querySelectorAll(`[data-save="${bookId}"]`).forEach((button) => { const saved = data.saved.includes(bookId); button.classList.toggle("saved", saved); button.textContent = saved ? "♥" : "♡"; button.setAttribute("aria-label", `${saved ? "Remove from" : "Add to"} reading list`); });
  if (document.querySelector("#detail-modal").open) openDetails(bookId);
  if (document.querySelector("#shelf-modal").open) renderShelf();
}
function updateProgress(bookId, progress) {
  if (progress > 0) data.reading[bookId] = progress; else delete data.reading[bookId];
  if (progress >= 100) { data.reading[bookId] = 100; showToast("Finished. A story well spent."); }
  persist(); renderContinue(); const value = document.querySelector("#progress-value"); if (value) value.textContent = `${progress}%`;
}
function requireAccount(action) {
  if (window.KahaniyaAuth?.user) return true;
  state.pendingAccountAction = action;
  window.KahaniyaAuth?.open("login");
  return false;
}
function openShelf(tab = "saved") {
  if (!requireAccount({ type: "shelf", tab })) return;
  state.activeShelf = tab; document.querySelector("#shelf-modal").showModal(); renderShelf();
}
function renderShelf() {
  document.querySelectorAll("[data-shelf-tab]").forEach((button) => button.classList.toggle("active", button.dataset.shelfTab === state.activeShelf));
  const ids = state.activeShelf === "saved" ? data.saved : state.activeShelf === "reading" ? Object.keys(data.reading).filter((id) => data.reading[id] < 100) : data.history;
  const books = ids.map((id) => state.books.find((book) => book.id === id)).filter(Boolean);
  document.querySelector("#shelf-content").innerHTML = books.length ? `<div class="shelf-grid">${books.map((book) => cardMarkup(book, state.activeShelf === "reading" ? `${data.reading[book.id]}% complete` : "")).join("")}</div>` : `<div class="shelf-empty">${state.activeShelf === "saved" ? "Your next favorite has room here." : state.activeShelf === "reading" ? "Your next chapter starts whenever you do." : "Every story begins somewhere."}</div>`;
}
function openProfile() {
  if (!requireAccount({ type: "profile" })) return;
  const user = window.KahaniyaAuth.user;
  document.querySelector("#profile-title").textContent = `Hello, ${user.name.split(" ")[0]}.`;
  document.querySelector("#profile-copy").textContent = `${user.email} · @${user.username}`;
  document.querySelector("#profile-avatar").textContent = user.name.charAt(0).toUpperCase();
  const finished = Object.values(data.reading).filter((progress) => progress >= 100).length;
  const inProgress = Object.values(data.reading).filter((progress) => progress > 0 && progress < 100).length;
  document.querySelector("#profile-stats").innerHTML = `<div class="profile-stat"><strong>${data.saved.length}</strong><span>Saved</span></div><div class="profile-stat"><strong>${inProgress}</strong><span>Reading</span></div><div class="profile-stat"><strong>${finished}</strong><span>Finished</span></div>`;
  document.querySelector("#profile-modal").showModal();
}
function openQuiz(mood = "overwhelmed") { const moodInput = document.querySelector(`input[name="mood"][value="${mood}"]`); if (moodInput) moodInput.checked = true; document.querySelector("#quiz-modal").showModal(); }

function updateAuthControls(user) {
  document.querySelector("#login-button").hidden = Boolean(user);
  const avatar = document.querySelector("#profile-button");
  avatar.hidden = !user;
  if (user) avatar.textContent = user.name.charAt(0).toUpperCase();
}

window.addEventListener("kahaniya:auth-change", (event) => {
  const user = event.detail.user;
  updateAuthControls(user);
  if (!user || !state.pendingAccountAction) return;
  const action = state.pendingAccountAction;
  state.pendingAccountAction = null;
  if (action.type === "shelf") openShelf(action.tab);
  if (action.type === "profile") openProfile();
  if (action.type === "save") toggleSaved(action.bookId);
  if (action.type === "reading") {
    data.reading[action.bookId] = Math.max(data.reading[action.bookId] || 0, 5);
    persist(); renderContinue(); openDetails(action.bookId);
  }
  if (action.type === "progress") updateProgress(action.bookId, action.progress);
  if (action.type === "feedback") {
    data.feedback[action.bookId] = action.value; persist(); openDetails(action.bookId);
  }
});

document.addEventListener("click", (event) => {
  const target = event.target; if (!(target instanceof HTMLElement)) return;
  const save = target.closest("[data-save]"); if (save) { event.stopPropagation(); if (requireAccount({ type: "save", bookId: save.dataset.save })) toggleSaved(save.dataset.save); return; }
  const card = target.closest("[data-book]"); if (card) { openDetails(card.dataset.book); return; }
  if (target.closest("#start-quiz")) openQuiz();
  if (target.closest("#edit-preferences")) openQuiz(state.preferences?.mood || "overwhelmed");
  const shelfButton = target.closest("[data-open-shelf]"); if (shelfButton) openShelf(shelfButton.dataset.openShelf);
  if (target.closest("#profile-button")) openProfile();
  if (target.closest("#profile-shelf")) { document.querySelector("#profile-modal").close(); openShelf(); }
  if (target.closest("#history-button")) openShelf("history");
  const mood = target.closest("[data-mood]"); if (mood) openQuiz(mood.dataset.mood);
  const scroll = target.closest("[data-scroll]"); if (scroll) document.querySelector(`#${scroll.dataset.scroll}`).scrollBy({ left: 520, behavior: "smooth" });
  const tab = target.closest("[data-shelf-tab]"); if (tab) { state.activeShelf = tab.dataset.shelfTab; renderShelf(); }
  const detailSave = target.closest("[data-detail-save]"); if (detailSave && requireAccount({ type: "save", bookId: detailSave.dataset.detailSave })) toggleSaved(detailSave.dataset.detailSave);
  const startReading = target.closest("[data-detail-reading]"); if (startReading) { const id = startReading.dataset.detailReading; if (requireAccount({ type: "reading", bookId: id })) { data.reading[id] = Math.max(data.reading[id] || 0, 5); persist(); renderContinue(); openDetails(id); showToast("Added to your current reads"); } }
  const feedback = target.closest("[data-feedback]"); if (feedback && requireAccount({ type: "feedback", bookId: feedback.dataset.id, value: feedback.dataset.feedback })) { const id = feedback.dataset.id; data.feedback[id] = feedback.dataset.feedback; persist(); openDetails(id); showToast(feedback.dataset.feedback === "like" ? "We’ll remember what you enjoy" : "Got it. We’ll tune your picks."); }
  if (target.closest("#logout-button")) window.KahaniyaAuth.logout().then(() => { document.querySelector("#profile-modal").close(); showToast("You are signed out"); }).catch((error) => showToast(error.message));
});
document.addEventListener("keydown", (event) => { if ((event.key === "Enter" || event.key === " ") && event.target.matches("[data-book]")) { event.preventDefault(); openDetails(event.target.dataset.book); } if (event.key === "Escape") document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close()); });
document.querySelector("#preferences-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = new FormData(event.currentTarget);
  const preferences = { mood: form.get("mood"), intent: form.get("intent"), kind: form.get("kind"), minutes: Number(form.get("minutes")), depth: form.get("depth") };
  document.querySelector("#quiz-modal").close(); await showRecommendations(preferences);
});
document.addEventListener("input", (event) => {
  if (!event.target.matches("[data-progress]")) return;
  const bookId = event.target.dataset.progress;
  const progress = Number(event.target.value);
  if (requireAccount({ type: "progress", bookId, progress })) updateProgress(bookId, progress);
});
document.querySelector("#search-input").addEventListener("input", (event) => {
  const query = event.target.value.trim().toLowerCase();
  if (!query) {
    document.querySelector("#discover .section-heading h2").textContent = "For your kind of day";
    document.querySelector("#discover .section-subtitle").textContent = "A few thoughtful picks, ready when you are.";
    document.querySelector("#mood-row").innerHTML = featuredBooks().map((book) => cardMarkup(book)).join("");
    document.querySelector("#discover").scrollIntoView({ behavior: "smooth" });
    return;
  }
  const matches = state.books.filter((book) => [book.title, book.author, ...book.genres, ...book.themes, ...book.moods].some((value) => value.toLowerCase().includes(query)));
  document.querySelector("#discover .section-heading h2").textContent = matches.length ? `A few ${query} kind of reads` : "Nothing on this shelf yet";
  document.querySelector("#discover .section-subtitle").textContent = matches.length ? `${matches.length} book${matches.length === 1 ? "" : "s"} found. Maybe one is yours.` : "Try a mood, theme, author, or title.";
  document.querySelector("#mood-row").innerHTML = matches.map((book) => cardMarkup(book)).join(""); document.querySelector("#discover").scrollIntoView({ behavior: "smooth", block: "start" });
});
async function initialize() {
  try { const response = await fetch("/api/books"); if (!response.ok) throw new Error("Catalog unavailable"); state.books = await response.json(); renderBooks(); updateCounts(); }
  catch { state.books = offlineBooks; renderBooks(); updateCounts(); }
}
initialize();