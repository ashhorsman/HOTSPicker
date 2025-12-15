/* =======================
   STATE
======================= */
const state = {
  heroes: [],
  draft: {
    firstBanSide: "ally",
    history: [] // { hero_id, side: "ally"|"enemy", type: "ban"|"pick", skipped?: true }
  },
  settings: {
    rankPreset: "Silver",
    simpleComps: true,
    mapName: ""
  }
};

/* =======================
   DRAFT SEQUENCE
======================= */
const SEQUENCE_FIRST_SECOND = [
  { type: "ban", team: "first" },
  { type: "ban", team: "second" },
  { type: "ban", team: "first" },
  { type: "ban", team: "second" },

  { type: "pick", team: "first" },
  { type: "pick", team: "second" },
  { type: "pick", team: "second" },
  { type: "pick", team: "first" },
  { type: "pick", team: "first" },

  { type: "ban", team: "second" },
  { type: "ban", team: "first" },

  { type: "pick", team: "second" },
  { type: "pick", team: "second" },
  { type: "pick", team: "first" },
  { type: "pick", team: "first" },
  { type: "pick", team: "second" }
];

/* =======================
   ROLE FILTERS
======================= */

const ROLE_FILTERS = [
  { key: "ALL", label: "All" },
  { key: "Tank", label: "Tank" },
  { key: "Healer", label: "Healer" },
  { key: "Ranged", label: "Ranged DPS" },
  { key: "Melee", label: "Melee DPS" },
  { key: "Support", label: "Support" }
];

let activeRoleFilter = "ALL";


let heroScores = {};


/* =======================
   ROLE LIMITS (ANTI DOUBLE ROLE)
======================= */
const ROLE_LIMITS = {
  Healer: 1,
  Tank: 1,
  Offlane: 1
};

const FLEX_ROLE_HEROES = new Set([
  "uther",
  "tyrande",
  "rehgar",
  "kharazim",
  "medivh",
  "abathur",
  "zarya"
]);

/* =======================
   LABELS
======================= */
const WC_LABEL = { L: "Low", M: "Med", H: "High" };
const ENG_LABEL = { N: "None", S: "Soft", H: "Hard" };

/* =======================
   HOVER HELP TEXT
======================= */
const HELP = {
  AA: "AA means Basic Attack damage. This is steady damage from auto attacks (Raynor, Valla, Greymane AA builds).",
  SPELL: "Spell damage comes from abilities (Kael'thas, Jaina, Li-Ming). Often bursty and cooldown-based.",
  PEEL: "Peel means protecting your backline by stopping divers (CC, zoning, body blocks, slows, knockbacks).",
  ENGAGE: "Engage means starting fights on your terms (hard CC, gap close, reliable setup).",
  WAVECLEAR: "Waveclear is how fast you clear minion waves. Good waveclear protects soak, enables rotations, and frees you for objectives.",
  REVEAL: "Reveal is reliable anti-stealth. It removes invisibility so your team can target stealth heroes.",

  WARN_NO_WAVECLEAR: "No waveclear means you struggle to clear lanes quickly. You will lose soak, get shoved in, and arrive late to objectives unless you rotate very cleanly.",
  WARN_NO_ENGAGE: "No engage means you cannot force fights. You often must poke, wait for mistakes, or get picks rather than clean 5v5 starts.",
  WARN_NO_PEEL: "No peel means your backline is exposed. Divers and hard engage reach your DPS/healer more easily.",
  WARN_NO_TANK: "No tank usually means no reliable frontline, no safe vision control, and weaker fight starts.",
  WARN_NO_HEALER: "No healer means no sustain. You must win through picks/burst and avoid long fights.",
  WARN_NO_OFFLANE: "No offlane often means no stable solo lane holder. Side soak and camp timing can collapse.",

  WARN_BACKLINE_LOW_MOBILITY_NO_PEEL: "Low mobility backline plus no peel means divers reach them easily and you have limited tools to stop it.",
  WARN_ENEMY_STEALTH_NO_REVEAL: "Enemy stealth plus no reveal means they can scout/flank and get picks much more safely.",

  WARN_DAMAGE_SKEW_SPELL: "Damage skew: mostly Spell means your damage is ability-based. Strong burst, but you rely on cooldown windows and can struggle into Spell Armor or heavy sustain.",
  WARN_DAMAGE_SKEW_AA: "Damage skew: mostly AA means your damage is auto-attack based. Strong sustained DPS, but blinds and disruption can punish it.",

  TAG_SAFE_EARLY: "Safe early means low dependency and hard to punish early in draft.",
  TAG_MUST_LOCK_NOW: "Must lock now means highly contested. If you want it, delaying risks losing it.",
  TAG_HIGH_PRIORITY: "High priority means strong ban target or it exploits current weaknesses.",
  TAG_STEALTH_THREAT: "Stealth threat means stealth is hard to answer without reliable reveal.",
  TAG_ENEMY_TURN: "Enemy turn means recommendations are being generated for the enemy side because it is currently their draft step.",

  TAG_NON_STANDARD: "Non-standard comp means this hero fills a role you already have. Usually not recommended unless you are drafting intentionally (flex, double support, niche strategy)."
};

/* =======================
   HOVER HELP SYSTEM
======================= */
let hoverTimer = null;
let spinnerTimer = null;
let hideTimer = null;

function getHelpText(key) {
  if (!key) return null;
  return HELP[key] || null;
}

function positionHelpBox(x, y) {
  const box = document.getElementById("hoverHelp");
  if (!box) return;

  const pad = 14;

  let left = x + pad;
  let top = y + pad;

  const rect = box.getBoundingClientRect();
  const maxLeft = window.innerWidth - rect.width - 10;
  const maxTop = window.innerHeight - rect.height - 10;

  left = Math.min(left, maxLeft);
  top = Math.min(top, maxTop);

  box.style.left = `${left}px`;
  box.style.top = `${top}px`;
}

function showSpinnerAt(x, y) {
  const box = document.getElementById("hoverHelp");
  const spinner = document.getElementById("hoverHelpSpinner");
  const text = document.getElementById("hoverHelpText");
  if (!box || !spinner || !text) return;

  text.textContent = "";
  spinner.classList.remove("hidden");

  box.classList.remove("hidden");
  box.setAttribute("aria-hidden", "false");
  positionHelpBox(x, y);
}

function showHelpTextAt(x, y, message) {
  const box = document.getElementById("hoverHelp");
  const spinner = document.getElementById("hoverHelpSpinner");
  const text = document.getElementById("hoverHelpText");
  if (!box || !spinner || !text) return;

  spinner.classList.add("hidden");
  text.textContent = message;

  box.classList.remove("hidden");
  box.setAttribute("aria-hidden", "false");
  positionHelpBox(x, y);
}

function hideHelp() {
  const box = document.getElementById("hoverHelp");
  if (!box) return;
  box.classList.add("hidden");
  box.setAttribute("aria-hidden", "true");
}

function clearHoverTimers() {
  if (hoverTimer) clearTimeout(hoverTimer);
  if (spinnerTimer) clearTimeout(spinnerTimer);
  if (hideTimer) clearTimeout(hideTimer);
  hoverTimer = null;
  spinnerTimer = null;
  hideTimer = null;
}

function attachHoverHelp(el, helpKey) {
  if (!el) return;
  const msg = getHelpText(helpKey);
  if (!msg) return;

  el.classList.add("helpTerm");

  el.addEventListener("mouseenter", (e) => {
    clearHoverTimers();
    const x = e.clientX;
    const y = e.clientY;

    spinnerTimer = setTimeout(() => {
      showSpinnerAt(x, y);
    }, 250);

    hoverTimer = setTimeout(() => {
      showHelpTextAt(x, y, msg);
    }, 2000);
  });

  el.addEventListener("mousemove", (e) => {
    const box = document.getElementById("hoverHelp");
    if (box && !box.classList.contains("hidden")) {
      positionHelpBox(e.clientX, e.clientY);
    }
  });

  el.addEventListener("mouseleave", () => {
    clearHoverTimers();
    hideTimer = setTimeout(() => {
      const box = document.getElementById("hoverHelp");
      if (!box) return;
      if (!box.matches(":hover")) hideHelp();
    }, 150);
  });
}

function wireHelpBoxHoverBehavior() {
  const box = document.getElementById("hoverHelp");
  if (!box) return;

  box.addEventListener("mouseenter", () => {
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
  });

  box.addEventListener("mouseleave", () => {
    hideHelp();
  });
}

/* =======================
   UTILS
======================= */
function prettyWC(v) {
  if (!v) return "-";
  return WC_LABEL[v] || v;
}

function prettyENG(v) {
  if (!v) return "-";
  return ENG_LABEL[v] || v;
}

function gradeClass(g) {
  const safe = (g || "").toUpperCase();
  return ["S","A","B","C","D","E"].includes(safe) ? safe : "E";
}

function sideForTeam(firstBanSide, team) {
  const first = firstBanSide;
  const second = firstBanSide === "ally" ? "enemy" : "ally";
  return team === "first" ? first : second;
}

function getSequence() {
  return SEQUENCE_FIRST_SECOND.map((s) => ({
    type: s.type,
    side: sideForTeam(state.draft.firstBanSide, s.team)
  }));
}

function currentStep() {
  const seq = getSequence();
  const idx = state.draft.history.length;
  return {
    idx,
    total: seq.length,
    step: seq[idx] || null,
    done: idx >= seq.length
  };
}

function earlyPickWindow() {
  const picksDone = state.draft.history.filter(a => a.type === "pick").length;
  return picksDone < 5;
}

function heroPortraitUrl(heroId) {
  return `/assets/heroes/ui_targetportrait_hero_${heroId}.png`;
}

function primaryRole(roleArr) {
  if (!Array.isArray(roleArr) || roleArr.length === 0) return "Unknown";
  const priority = ["Tank", "Healer", "Offlane", "Melee", "Ranged", "Support"];
  for (const p of priority) {
    if (roleArr.includes(p)) return p;
  }
  return roleArr[0];
}

function heroMatchesRoleFilter(hero, filter) {
  if (filter === "ALL") return true;

  const roles = hero.role || [];

  if (filter === "Tank") return roles.includes("Tank");
  if (filter === "Healer") return roles.includes("Healer");
  if (filter === "Support") return roles.includes("Support");

  if (filter === "Ranged") {
    return roles.includes("Ranged");
  }

  if (filter === "Melee") {
    return roles.includes("Melee") || roles.includes("Bruiser");
  }

  return true;
}

function renderRoleFilters() {
  const el = document.getElementById("roleFilters");
  if (!el) return;

  el.innerHTML = "";

  ROLE_FILTERS.forEach(r => {
    const btn = document.createElement("button");
    btn.className = "roleFilterBtn";
    if (activeRoleFilter === r.key) btn.classList.add("active");

    btn.textContent = r.label;

    btn.addEventListener("click", () => {
      activeRoleFilter = r.key;
      renderHeroList(document.getElementById("searchBox")?.value || "");
    });

    el.appendChild(btn);
  });
}



function countPrimaryRoles(heroIds) {
  const counts = {
    Tank: 0,
    Healer: 0,
    Offlane: 0,
    Ranged: 0,
    Melee: 0,
    Support: 0
  };

  heroIds.forEach(id => {
    const h = state.heroes.find(x => x.hero_id === id);
    if (!h) return;
    const role = primaryRole(h.role);
    if (counts[role] !== undefined) counts[role]++;
  });

  return counts;
}

/* =======================
   ROLE SATURATION LOGIC
   Change: treat "2nd healer" as non-standard even for flex healers.
======================= */
function roleIsOverfilled(hero, roleCounts) {
  const role = primaryRole(hero.role);

  if (!ROLE_LIMITS[role]) return false;

  // Special rule: if we already have a healer, any further healer is non-standard.
  // This prevents "recommended healers when a healer is picked" from dominating.
  if (role === "Healer" && roleCounts.Healer >= ROLE_LIMITS.Healer) {
    return true;
  }

  // Otherwise keep your existing flex behavior for Tank/Offlane etc.
  if (FLEX_ROLE_HEROES.has(hero.hero_id)) return false;

  return roleCounts[role] >= ROLE_LIMITS[role];
}

/* =======================
   PILL SYSTEM
======================= */
function levelClassFromValue(val) {
  const v = (val || "").toString().trim().toLowerCase();

  if (v === "h" || v === "high" || v === "hard") return "level-high";
  if (v === "m" || v === "med" || v === "medium" || v === "soft") return "level-med";
  if (v === "l" || v === "low") return "level-low";
  if (v === "n" || v === "none") return "level-none";

  if (v === "y" || v === "yes") return "level-high";

  return "level-med";
}

function prettyValue(val) {
  const v = (val || "").toString().trim().toUpperCase();
  if (v === "H") return "High";
  if (v === "M") return "Med";
  if (v === "L") return "Low";
  if (v === "N") return "None";
  if (v === "S") return "Soft";
  if (v === "Y") return "Yes";
  return (val || "-").toString();
}

function makePill(label, value) {
  const pill = document.createElement("div");
  pill.className = `pill ${levelClassFromValue(value)}`;
  pill.title = `${label}: ${prettyValue(value)}`;
  pill.textContent = label;
  return pill;
}

/* =======================
   Change: CC pill strength is now L/M/H based on number of CC types
======================= */
function ccStrengthFromList(ccList) {
  if (!Array.isArray(ccList)) return null;
  const n = ccList.length;

  if (n <= 0) return null;
  if (n === 1) return "L";
  if (n === 2) return "M";
  return "H";
}

function buildHeroPills(h) {
  const pills = document.createElement("div");
  pills.className = "heroPills";

  if (h.wc) pills.appendChild(makePill("Waveclear", h.wc));
  if (h.eng) pills.appendChild(makePill("Engage", h.eng));

  if (h.peel && h.peel !== "N") pills.appendChild(makePill("Peel", h.peel));
  if (h.macro && h.macro !== "N") pills.appendChild(makePill("Macro", h.macro));
  if (h.sustain && h.sustain !== "N") pills.appendChild(makePill("Sustain", h.sustain));
  if (h.burst && h.burst !== "N") pills.appendChild(makePill("Burst", h.burst));

  const ccStrength = ccStrengthFromList(h.cc);
  if (ccStrength) pills.appendChild(makePill("CC", ccStrength));

  if (h.stealth === "Y") pills.appendChild(makePill("Stealth", "H"));
  if (h.reveal === "Y") pills.appendChild(makePill("Reveal", "H"));

  return pills;
}

/* =======================
   PREFS
======================= */
function savePrefs() {
  localStorage.setItem("hotsDraftAssistant_prefs", JSON.stringify({
    settings: state.settings,
    firstBanSide: state.draft.firstBanSide
  }));
}

function loadPrefs() {
  try {
    const raw = localStorage.getItem("hotsDraftAssistant_prefs");
    if (!raw) return;
    const obj = JSON.parse(raw);
    if (obj.settings) state.settings = obj.settings;
    if (obj.firstBanSide) state.draft.firstBanSide = obj.firstBanSide;
  } catch (e) {}
}

/* =======================
   API
======================= */
async function apiGetHeroes() {
  const res = await fetch("/api/heroes");
  return res.json();
}

async function apiGetMaps() {
  const res = await fetch("/api/maps");
  return res.json();
}

async function apiPostRecs(draftPayload) {
  const res = await fetch("/api/recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft: draftPayload, settings: state.settings })
  });
  return res.json();
}

/* =======================
   DRAFT LIST DERIVATION
======================= */
function deriveDraftLists() {
  const ourPicks = [];
  const enemyPicks = [];
  const allyBans = [];
  const enemyBans = [];
  const bans = [];

  const ourPicksUI = [];
  const enemyPicksUI = [];
  const allyBansUI = [];
  const enemyBansUI = [];

  for (const a of state.draft.history) {
    const isSkipped = !!a.skipped || !a.hero_id;

    if (a.type === "pick") {
      if (a.side === "ally") {
        if (!isSkipped) ourPicks.push(a.hero_id);
        ourPicksUI.push(isSkipped ? { skipped: true } : a.hero_id);
      } else {
        if (!isSkipped) enemyPicks.push(a.hero_id);
        enemyPicksUI.push(isSkipped ? { skipped: true } : a.hero_id);
      }
    } else {
      if (a.side === "ally") {
        if (!isSkipped) allyBans.push(a.hero_id);
        allyBansUI.push(isSkipped ? { skipped: true } : a.hero_id);
      } else {
        if (!isSkipped) enemyBans.push(a.hero_id);
        enemyBansUI.push(isSkipped ? { skipped: true } : a.hero_id);
      }
      if (!isSkipped) bans.push(a.hero_id);
    }
  }

  return {
    ourPicks,
    enemyPicks,
    allyBans,
    enemyBans,
    bans,
    ui: {
      ourPicks: ourPicksUI,
      enemyPicks: enemyPicksUI,
      allyBans: allyBansUI,
      enemyBans: enemyBansUI
    }
  };
}

/* =======================
   RENDER: TIMELINE + STATUS
======================= */
function renderTimeline() {
  const el = document.getElementById("timeline");
  el.innerHTML = "";

  const seq = getSequence();
  const idx = state.draft.history.length;

  seq.forEach((s, i) => {
    const box = document.createElement("div");
    box.className = "stepBox";
    if (i < idx) box.classList.add("done");
    if (i === idx) box.classList.add("current");

    const sideLabel = s.side === "ally" ? "A" : "E";
    const typeLabel = s.type === "ban" ? "BAN" : "PICK";
    box.textContent = `${sideLabel} ${typeLabel}`;

    el.appendChild(box);
  });
}

function renderCurrentAction() {
  const el = document.getElementById("currentAction");
  const cs = currentStep();

  if (cs.done) {
    el.textContent = "Draft complete";
    return;
  }

  const sideLabel = cs.step.side === "ally" ? "Allies" : "Enemies";
  const typeLabel = cs.step.type === "ban" ? "Ban" : "Pick";
  el.textContent = `Step ${cs.idx + 1}/${cs.total}: ${sideLabel} ${typeLabel}`;
}

/* =======================
   RENDER: CHIPS (PICKS/BANS)
======================= */
function renderChips(id, arr, type = "pick") {
  const el = document.getElementById(id);
  el.innerHTML = "";

  arr.forEach((item) => {
    const chip = document.createElement("div");
    chip.className = `chip ${type}`;

    if (item && typeof item === "object" && item.skipped) {
      chip.classList.add("chipSkip");
      chip.textContent = "Skipped";
      chip.title = "Skipped (no hero selected)";
      el.appendChild(chip);
      return;
    }

    const heroId = item;
    const hero = state.heroes.find(h => h.hero_id === heroId);
    if (!hero) return;

    const img = document.createElement("img");
    img.src = heroPortraitUrl(hero.hero_id);
    img.alt = hero.hero_name;
    img.title = hero.hero_name;

    chip.appendChild(img);
    el.appendChild(chip);
  });
}

/* =======================
   RENDER: HERO LIST
======================= */
function renderHeroList(filterText) {
  const list = document.getElementById("heroList");
  list.innerHTML = "";

  const t = (filterText || "").trim().toLowerCase();
  const { ourPicks, enemyPicks, bans } = deriveDraftLists();

  const unavailable = new Set([...ourPicks, ...enemyPicks, ...bans]);

  const cs = currentStep();
  const draftLocked = cs.done;

  const heroes = state.heroes
    .filter(h => !t || h.hero_name.toLowerCase().includes(t))
    .filter(h => !unavailable.has(h.hero_id))
    .filter(h => heroMatchesRoleFilter(h, activeRoleFilter))

    .sort((a, b) => {
      const sa = heroScores[a.hero_id];
      const sb = heroScores[b.hero_id];

      if (sa === undefined && sb === undefined) return 0;
      if (sa === undefined) return 1;
      if (sb === undefined) return -1;

      return sb - sa;
    });

  heroes.forEach((h) => {
    const card = document.createElement("div");
    card.className = "heroCard";

    card.addEventListener("click", () => {
      if (draftLocked) return;
      assignHeroToCurrentSlot(h.hero_id);
    });

    const img = document.createElement("img");
    img.className = "heroPortrait";
    img.src = heroPortraitUrl(h.hero_id);
    img.alt = h.hero_name;

    const pills = buildHeroPills(h);

    const role = document.createElement("div");
    role.className = "heroRole";
    role.textContent = primaryRole(h.role);

    // ✅ SCORE BADGE (correct place)
    const score = heroScores[h.hero_id];
    if (score !== undefined) {
      const badge = document.createElement("div");
      badge.className = "heroScoreBadge";
      badge.textContent = Math.round(score);
      card.appendChild(badge);
    }

    card.appendChild(img);
    card.appendChild(pills);
    card.appendChild(role);

    list.appendChild(card);
  });
}


/* =======================
   ACTIONS: ASSIGN, SKIP, UNDO, RESET
======================= */
function assignHeroToCurrentSlot(hero_id) {
  const cs = currentStep();
  if (cs.done || !cs.step) return;

  const { ourPicks, enemyPicks, bans } = deriveDraftLists();
  const used = new Set([...ourPicks, ...enemyPicks, ...bans]);
  if (!hero_id || used.has(hero_id)) return;

  state.draft.history.push({
    hero_id,
    side: cs.step.side,
    type: cs.step.type
  });

  update();
}

function skipCurrentSlot() {
  const cs = currentStep();
  if (cs.done || !cs.step) return;
  if (cs.step.type !== "ban") return;

  state.draft.history.push({
    hero_id: null,
    side: cs.step.side,
    type: cs.step.type,
    skipped: true
  });

  update();
}

function undo() {
  if (state.draft.history.length === 0) return;
  state.draft.history.pop();
  update();
}

function resetDraft() {
  state.draft.history = [];
  update();
}

/* =======================
   WARNINGS HELP KEY
======================= */
function warningToHelpKey(w) {
  const s = (w || "").toLowerCase();

  if (s.includes("no waveclear")) return "WARN_NO_WAVECLEAR";
  if (s.includes("no engage")) return "WARN_NO_ENGAGE";
  if (s.includes("no peel")) return "WARN_NO_PEEL";
  if (s.includes("no tank")) return "WARN_NO_TANK";
  if (s.includes("no healer")) return "WARN_NO_HEALER";
  if (s.includes("no offlane")) return "WARN_NO_OFFLANE";

  if (s.includes("backline low mobility") && s.includes("no peel")) return "WARN_BACKLINE_LOW_MOBILITY_NO_PEEL";
  if (s.includes("stealth") && s.includes("no reveal")) return "WARN_ENEMY_STEALTH_NO_REVEAL";

  if (s.includes("damage skew") && s.includes("spell")) return "WARN_DAMAGE_SKEW_SPELL";
  if (s.includes("damage skew") && (s.includes("aa") || s.includes("basic"))) return "WARN_DAMAGE_SKEW_AA";

  return null;
}



/* =======================
   RENDER: WARNINGS + PLAN
======================= */
function renderWarnings(data) {
  const el = document.getElementById("warnings");
  el.innerHTML = "";

  (data.warnings || []).forEach((w) => {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.textContent = w;

    const key = warningToHelpKey(w);
    if (key) attachHoverHelp(span, key);

    li.appendChild(span);
    el.appendChild(li);
  });
}

function renderPlan(data) {
  const el = document.getElementById("plan");
  el.innerHTML = "";
  (data.endPlan || []).forEach((p) => {
    const li = document.createElement("li");
    li.textContent = p;
    el.appendChild(li);
  });
}

/* =======================
   RENDER: SCORE SUMMARY (TWO BUTTON CARDS)
======================= */
function renderScoreSummary(data) {
  const el = document.getElementById("scoreSummary");
  if (!el) return;

  el.classList.add("scoreSummary");

  const a = Number(data.ourTeamScore ?? 0);
  const e = Number(data.enemyTeamScore ?? 0);

  el.innerHTML = "";

  const diff = a - e;
  const absDiff = Math.abs(diff);

  function scoreClass(isAlly) {
    if (absDiff <= 3) return "score-even";
    if ((diff > 0 && isAlly) || (diff < 0 && !isAlly)) return "score-win";
    return "score-lose";
  }

  const allies = document.createElement("div");
  allies.className = `scoreCard ${scoreClass(true)}`;
  allies.innerHTML = `
    <div class="scoreValue">${a}</div>
    <div class="scoreLabel">Allies</div>
  `;

  const enemies = document.createElement("div");
  enemies.className = `scoreCard ${scoreClass(false)}`;
  enemies.innerHTML = `
    <div class="scoreValue">${e}</div>
    <div class="scoreLabel">Enemies</div>
  `;

  el.appendChild(allies);
  el.appendChild(enemies);
}

/* =======================
   MAPS
======================= */
async function loadMaps() {
  const sel = document.getElementById("mapSelect");
  if (!sel) return;

  const data = await apiGetMaps();

  sel.innerHTML = "";

  const opt0 = document.createElement("option");
  opt0.value = "";
  opt0.textContent = "No map selected";
  sel.appendChild(opt0);

  (data.maps || []).forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    sel.appendChild(opt);
  });

  sel.value = state.settings.mapName || "";
}

/* =======================
   UPDATE LOOP
======================= */
async function update() {
  const lists = deriveDraftLists();

  renderTimeline();
  renderCurrentAction();
  renderRoleFilters();


  renderChips("allyBans", lists.ui.allyBans, "ban");
  renderChips("enemyBans", lists.ui.enemyBans, "ban");
  renderChips("ourPicks", lists.ui.ourPicks, "pick");
  renderChips("enemyPicks", lists.ui.enemyPicks, "pick");

  const qEl = document.getElementById("searchBox");
  const q = qEl ? qEl.value : "";
  renderHeroList(q);

  const cs = currentStep();
  const draftPayload = {
    phase: cs.step ? cs.step.type : "pick",
    sideToAct: cs.step ? cs.step.side : "ally",
    earlyPickWindow: earlyPickWindow(),
    ourPicks: lists.ourPicks,
    enemyPicks: lists.enemyPicks,
    bans: lists.bans
  };

  const data = await apiPostRecs(draftPayload);
  // Store hero scores for sorting the hero list
  heroScores = {};
  (data.recommendations || []).forEach(r => {
    heroScores[r.hero_id] = r.score;
  });


  renderScoreSummary(data);

  renderWarnings(data);
  renderPlan(data);

  savePrefs();
}

/* =======================
   UI WIRING
======================= */
function wireUI() {
  document.getElementById("firstBanSelect").addEventListener("change", (e) => {
    state.draft.firstBanSide = e.target.value;
    state.draft.history = [];
    update();
  });

  document.getElementById("skipBtn").addEventListener("click", () => {
    skipCurrentSlot();
  });

  document.getElementById("rankSelect").addEventListener("change", (e) => {
    state.settings.rankPreset = e.target.value;
    update();
  });

  document.getElementById("simpleToggle").addEventListener("change", (e) => {
    state.settings.simpleComps = e.target.checked;
    update();
  });

  const mapSel = document.getElementById("mapSelect");
  if (mapSel) {
    mapSel.addEventListener("change", (e) => {
      state.settings.mapName = e.target.value;
      update();
    });
  }

  document.getElementById("undoBtn").addEventListener("click", () => {
    undo();
  });

  document.getElementById("resetBtn").addEventListener("click", () => {
    resetDraft();
  });

  document.getElementById("searchBox").addEventListener("input", (e) => {
    renderHeroList(e.target.value);
  });
}

/* =======================
   INIT
======================= */
async function init() {
  loadPrefs();

  const rankSel = document.getElementById("rankSelect");
  const simp = document.getElementById("simpleToggle");
  const first = document.getElementById("firstBanSelect");

  if (rankSel) rankSel.value = state.settings.rankPreset || "Silver";
  if (simp) simp.checked = !!state.settings.simpleComps;
  if (first) first.value = state.draft.firstBanSide || "ally";

  state.heroes = await apiGetHeroes();
  await loadMaps();

  wireHelpBoxHoverBehavior();
  wireUI();
  renderRoleFilters();
  renderHeroList("");
  update();
}

init();
