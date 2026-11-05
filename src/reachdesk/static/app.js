"use strict";
const FA = {
  "Today": "امروز", "Saved posts": "پست‌های ذخیره‌شده", "Jobs": "آگهی‌ها", "People": "افراد", "Find": "جستجو", "Add": "افزودن", "Templates": "متن‌ها", "Insights": "نتایج", "Settings": "تنظیمات",
  "Ready to send": "آمادهٔ ارسال", "Prepare today's messages": "آماده‌سازی پیام‌های امروز", "Copy & open": "کپی و باز کردن", "I sent it": "فرستادم", "Skip": "رد کردن", "Copy text": "کپی متن",
  "Connection request": "درخواست کانکت", "Message": "پیام", "Follow-up": "پیگیری", "Email (automatic)": "ایمیل (خودکار)", "Waiting for acceptance": "در انتظار قبول کانکت", "They accepted": "قبول کرد",
  "Sent, awaiting a reply": "ارسال‌شده، در انتظار پاسخ", "Replied": "پاسخ داد", "Interested": "علاقه‌مند", "Opted out": "لغو تماس", "Send permitted email now": "ارسال ایمیل‌های مجاز",
  "No messages are ready. Prepare today's messages, or add people first.": "پیامی آماده نیست. پیام‌های امروز را آماده کنید یا اول افراد را اضافه کنید.",
  "Open": "باز کردن", "Done": "انجام شد", "Archive": "بایگانی", "Why this rating?": "دلیل امتیاز؟", "Delete data": "حذف داده", "Search": "جستجو", "Fetch new jobs": "دریافت آگهی‌های جدید", "Export CSV": "خروجی CSV",
  "Nothing here yet.": "هنوز چیزی اینجا نیست.", "Copied. Paste it, send it, then press \"I sent it\".": "کپی شد. جای‌گذاری و ارسال کنید، بعد «فرستادم» را بزنید.", "Saved": "ذخیره شد",
  "Paste a post or profile": "متن پست یا پروفایل را جای‌گذاری کنید", "Page link (optional)": "لینک صفحه (اختیاری)", "Location (optional)": "مکان (اختیاری)", "Save": "ذخیره", "Import a CSV file": "وارد کردن فایل CSV",
  "Use LinkedIn's official Connections.csv export, or any CSV with name, title, company, location, URL and email columns. Importing a fresh Connections.csv also detects who accepted your requests.": "فایل رسمی Connections.csv لینکدین یا هر CSV دارای نام، عنوان، شرکت، مکان، لینک و ایمیل را بدهید. وارد کردن Connections.csv تازه، قبول‌شدن درخواست‌ها را هم تشخیص می‌دهد.",
  "Quick capture": "ذخیرهٔ سریع", "Drag this code into a new bookmark. Select text on any page, then click the bookmark to review it here. It reads only your selection.": "این کد را به‌عنوان بوکمارک ذخیره کنید. متنی را انتخاب کنید و بوکمارک را بزنید تا اینجا بررسی شود. فقط متن انتخابی خوانده می‌شود.",
  "Open these searches yourself, then save the results you want. The app never browses LinkedIn for you.": "این جستجوها را خودتان باز کنید و نتیجه‌های دلخواه را ذخیره کنید. برنامه هرگز به‌جای شما در لینکدین نمی‌گردد.",
  "Campaign": "کمپین", "Website": "وبسایت", "Sender name": "نام فرستنده", "Sender contact (email or phone)": "راه تماس فرستنده", "Daily limit": "سقف روزانه", "Connection note limit": "سقف طول یادداشت کانکت", "Minimum score": "حداقل امتیاز", "Commercial campaign (adds Canadian anti-spam checks)": "کمپین تجاری (بررسی‌های ضد اسپم کانادا)", "Send permitted email automatically": "ارسال خودکار ایمیل‌های مجاز", "Email subject": "موضوع ایمیل",
  "Email account (SMTP)": "حساب ایمیل (SMTP)", "Server": "سرور", "Port": "پورت", "Username": "نام کاربری", "From address": "آدرس فرستنده", "File to attach to career emails": "فایل پیوست ایمیل‌های شغلی", "Set the password in the REACHDESK_SMTP_PASSWORD environment variable. It is never stored.": "رمز را در متغیر محیطی REACHDESK_SMTP_PASSWORD بگذارید. هرگز ذخیره نمی‌شود.",
  "License": "لایسنس", "Activate": "فعال‌سازی", "Plan": "پلن", "Saved items": "موردها", "Requests sent": "کانکت ارسالی", "Accepted": "قبول‌شده", "Messages sent": "پیام ارسالی", "Replies": "پاسخ‌ها", "Positive": "مثبت", "Ready": "آماده",
  "Learning": "یادگیری", "Ratings": "امتیازها", "Early accuracy": "دقت اولیه", "Recent accuracy": "دقت اخیر", "Model influence": "اثر مدل", "Learned likes": "ترجیح‌های یادگرفته", "Learned dislikes": "موارد نامطلوب یادگرفته", "Rejection reasons": "دلیل‌های رد",
  "Add a variant": "افزودن نسخه", "Name": "نام", "Step": "مرحله", "Text": "متن", "Available fields": "فیلدها", "Sent": "ارسال", "Consent basis": "مبنای تماس", "Delete everything stored about this contact and never contact them again?": "همهٔ اطلاعات این مخاطب حذف شود و دیگر با او تماس گرفته نشود؟",
  "Rate at least 6 items, with both likes and dislikes, and the ranking starts learning.": "حداقل ۶ مورد را با ترکیبی از پسند و ناپسند امتیاز بدهید تا رتبه‌بندی یاد بگیرد.",
};
let lang = localStorage.getItem("lang") || "en";
const t = (s) => (lang === "fa" && FA[s]) || s;

const REASON_FA = { wrong_location: "مکان اشتباه", wrong_role: "نقش اشتباه", wrong_seniority: "سطح اشتباه", wrong_company: "شرکت نامناسب", spam_or_bait: "اسپم یا جلب تعامل", not_hiring: "استخدام نمی‌کند", great_role: "نقش عالی", great_company: "شرکت عالی", great_location: "مکان عالی" };
const REASON_EN = { wrong_location: "Wrong location", wrong_role: "Wrong role", wrong_seniority: "Wrong seniority", wrong_company: "Wrong company", spam_or_bait: "Spam or bait", not_hiring: "Not hiring", great_role: "Great role", great_company: "Great company", great_location: "Great location" };
const reasonLabel = (r) => (lang === "fa" ? REASON_FA : REASON_EN)[r] || r;
const INTENT = { cta_comment: ["Asks for a comment", "کامنت می‌خواهد"], cta_dm: ["Asks for a DM", "دایرکت می‌خواهد"], cta_cv: ["Asks for a CV", "رزومه می‌خواهد"], hiring: ["Hiring", "استخدام"], no_contact: ["Do not contact", "تماس نگیرید"], seeker: ["Job seeker", "کارجو"], engagement_bait: ["Possible bait", "شاید جلب تعامل"] };
const intentLabel = (k) => (INTENT[k] ? INTENT[k][lang === "fa" ? 1 : 0] : k);

/** Builds DOM nodes. Text always goes through textContent, so imported data cannot inject markup. */
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k === "value") el.value = v;
    else if (k === "checked" || k === "disabled" || k === "selected") el[k] = !!v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) if (kid !== null && kid !== undefined && kid !== false) el.append(kid.nodeType ? kid : String(kid));
  return el;
}
const safeHref = (u) => (/^https?:\/\//i.test(u || "") ? u : null);

async function api(path, body) {
  const options = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json", "X-ReachDesk": "1" }, body: JSON.stringify(body) };
  const res = await fetch(path, options);
  const type = res.headers.get("content-type") || "";
  const data = type.includes("json") ? await res.json() : await res.text();
  if (!res.ok) { toast(data.error || "Error"); throw new Error(data.error || "request failed"); }
  return data;
}
function toast(text) {
  const el = document.getElementById("toast");
  el.textContent = text; el.classList.add("show");
  clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove("show"), 3200);
}

let boot = null;
let campaignId = Number(localStorage.getItem("campaign")) || 0;
let tab = "Today";
const TABS = ["Today", "Saved posts", "Jobs", "People", "Find", "Add", "Templates", "Insights", "Settings"];
const view = () => document.getElementById("view");
const campaign = () => boot.campaigns.find((c) => c.id === campaignId);
const q = (extra) => new URLSearchParams({ campaign: campaignId, ...extra }).toString();

async function start() {
  boot = await api("/api/bootstrap");
  if (!campaign()) campaignId = boot.campaigns[0] ? boot.campaigns[0].id : 0;
  chrome();
  const hash = location.hash;
  if (hash.startsWith("#capture=")) { tab = "Add"; }
  await render();
}
function chrome() {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "fa" ? "rtl" : "ltr";
  document.getElementById("lang").textContent = lang === "fa" ? "English" : "فارسی";
  const select = document.getElementById("campaign");
  select.replaceChildren(...boot.campaigns.map((c) => h("option", { value: c.id, selected: c.id === campaignId }, c.name)));
  document.getElementById("tabs").replaceChildren(...TABS.map((name) => h("button", { type: "button", role: "tab", "aria-selected": String(name === tab), onclick: () => { tab = name; chrome(); render(); } }, t(name))));
  document.getElementById("planBadge").textContent = `${t("Plan")}: ${boot.plan.label}`;
}
document.getElementById("lang").addEventListener("click", () => { lang = lang === "fa" ? "en" : "fa"; localStorage.setItem("lang", lang); chrome(); render(); });
document.getElementById("campaign").addEventListener("change", (e) => { campaignId = Number(e.target.value); localStorage.setItem("campaign", campaignId); render(); });

async function render() {
  const pages = { "Today": pageToday, "Saved posts": pagePosts, "Jobs": pageJobs, "People": pagePeople, "Find": pageFind, "Add": pageAdd, "Templates": pageTemplates, "Insights": pageInsights, "Settings": pageSettings };
  if (!campaignId) { view().replaceChildren(h("div", { class: "empty" }, t("Nothing here yet."))); return; }
  const node = await pages[tab]();
  view().replaceChildren(node);
}

const STEP = { connect: "Connection request", message: "Message", followup: "Follow-up", email: "Email (automatic)" };

async function pageToday() {
  const [ready, sent] = await Promise.all([api("/api/queue?" + q({ status: "ready" })), api("/api/queue?" + q({ status: "sent" }))]);
  const c = campaign();
  const header = h("div", { class: "row between" },
    h("div", {}, h("h2", {}, `${t("Ready to send")} (${ready.length})`)),
    h("div", { class: "row" },
      c.auto_email ? h("button", { class: "btn", type: "button", onclick: async () => { const r = await api(`/api/campaigns/${campaignId}/dispatch`, {}); toast(r.reason || `${r.sent} ${t("Sent")}`); render(); } }, t("Send permitted email now")) : null,
      h("button", { class: "btn primary", type: "button", onclick: buildQueue }, t("Prepare today's messages"))));
  const cards = ready.map(queueCard);
  const waiting = sent.filter((o) => o.step === "connect");
  const open = sent.filter((o) => o.step !== "connect");
  return h("div", {}, header, h("p", { class: "sub" }),
    cards.length ? cards : h("div", { class: "empty" }, t("No messages are ready. Prepare today's messages, or add people first.")),
    waiting.length ? [h("h3", {}, `${t("Waiting for acceptance")} (${waiting.length})`), waiting.map(waitingCard)] : null,
    open.length ? [h("h3", {}, `${t("Sent, awaiting a reply")} (${open.length})`), open.map(sentCard)] : null);
}
async function buildQueue() {
  const r = await api(`/api/campaigns/${campaignId}/queue`, {});
  const skipped = Object.entries(r.skipped).map(([k, v]) => `${k}: ${v}`).join(", ");
  const problem = r.template_problems[0] ? ` | ${r.template_problems[0]}` : "";
  toast(`+${r.created}${skipped ? " | " + skipped : ""}${problem}`);
  render();
}
function queueCard(o) {
  const text = h("textarea", { value: o.body, "aria-label": t("Text"), onchange: (e) => api(`/api/outreach/${o.id}/edit`, { body: e.target.value }) });
  const href = safeHref(o.url);
  const copy = async () => { await navigator.clipboard.writeText(text.value); };
  return h("article", { class: "card" },
    h("div", { class: "row between" },
      h("div", {}, h("span", { class: "name" }, o.full_name || o.company || "—"), " ", h("span", { class: "badge" }, t(STEP[o.step])),
        h("div", { class: "meta" }, [o.title, o.company, o.location].filter(Boolean).join(" · "))),
      h("div", { class: "score" }, Math.round(o.score * 100))),
    h("p", {}), text,
    h("div", { class: "row" },
      o.step === "email" ? null : h("button", { class: "btn primary", type: "button", disabled: !href, onclick: async () => { await copy(); window.open(href, "_blank", "noopener"); toast(t("Copied. Paste it, send it, then press \"I sent it\".")); } }, t("Copy & open")),
      o.step === "email" ? null : h("button", { class: "btn", type: "button", onclick: async () => { await api(`/api/outreach/${o.id}/sent`, {}); render(); } }, t("I sent it")),
      h("button", { class: "btn", type: "button", onclick: async () => { await api(`/api/outreach/${o.id}/skip`, {}); render(); } }, t("Skip"))));
}
function waitingCard(o) {
  return h("article", { class: "card row between" },
    h("div", {}, h("span", { class: "name" }, o.full_name || "—"), h("div", { class: "meta" }, [o.title, o.company].filter(Boolean).join(" · "))),
    h("button", { class: "btn primary", type: "button", onclick: async () => { await api(`/api/items/${o.item_id}/accepted`, {}); render(); } }, t("They accepted")));
}
function sentCard(o) {
  const reply = (body) => async () => { await api(`/api/outreach/${o.id}/reply`, body); render(); };
  return h("article", { class: "card row between" },
    h("div", {}, h("span", { class: "name" }, o.full_name || "—"), " ", h("span", { class: "badge" }, t(STEP[o.step])), h("div", { class: "meta" }, o.sent_at)),
    h("div", { class: "row" },
      h("button", { class: "btn", type: "button", onclick: reply({}) }, t("Replied")),
      h("button", { class: "btn", type: "button", onclick: reply({ positive: true }) }, t("Interested")),
      h("button", { class: "btn", type: "button", onclick: reply({ opt_out: true }) }, t("Opted out"))));
}

function stars(item, after) {
  const reason = h("select", { "aria-label": t("Why this rating?") }, h("option", { value: "" }, t("Why this rating?")), boot.reasons.map((r) => h("option", { value: r, selected: item.reason === r }, reasonLabel(r))));
  const rate = async (n) => { await api(`/api/items/${item.id}/rate`, { stars: n, reason: reason.value }); toast(t("Saved")); after(); };
  reason.addEventListener("change", () => { if (item.stars) rate(item.stars); });
  return h("div", { class: "row" },
    h("div", { class: "stars" }, [1, 2, 3, 4, 5].map((n) => h("button", { type: "button", class: item.stars >= n ? "on" : "", "aria-label": `${n} / 5`, onclick: () => rate(n) }, "★"))),
    reason);
}
function itemCard(item, actions) {
  const href = safeHref(item.url);
  const labels = [...(item.intents || []), ...(item.flags || [])];
  return h("article", { class: "card" },
    h("div", { class: "row between" },
      h("div", {}, h("span", { class: "name" }, item.kind === "job" ? item.title : (item.full_name || item.company || "—")),
        h("div", { class: "meta" }, (item.kind === "job" ? [item.company, item.location] : [item.title, item.company, item.location]).filter(Boolean).join(" · "))),
      h("div", { class: "score", title: (item.explain || []).join("\n") }, Math.round(item.score * 100))),
    labels.length ? h("div", { class: "row" }, labels.map((k) => h("span", { class: "badge" + (k === "no_contact" ? " bad" : k === "engagement_bait" || k === "seeker" ? " warn" : "") }, intentLabel(k)))) : null,
    item.body ? h("div", { class: "body", dir: "auto" }, item.body.slice(0, 900)) : null,
    (item.explain || []).length ? h("div", { class: "meta" }, item.explain.slice(0, 5).join(" · ")) : null,
    h("p", {}),
    h("div", { class: "row between" }, stars(item, render), h("div", { class: "row" },
      href ? h("a", { class: "btn", href, target: "_blank", rel: "noopener noreferrer" }, t("Open")) : null,
      actions)));
}
const statusButton = (item, status, label) => h("button", { class: "btn", type: "button", onclick: async () => { await api(`/api/items/${item.id}/status`, { status }); render(); } }, t(label));

async function listPage(title, params, extraHeader, actions) {
  const items = await api("/api/items?" + q({ limit: 100, ...params }));
  return h("div", {}, h("div", { class: "row between" }, h("h2", {}, `${t(title)} (${items.length})`), extraHeader), h("p", { class: "sub" }),
    items.length ? items.map((i) => itemCard(i, actions(i))) : h("div", { class: "empty" }, t("Nothing here yet.")));
}
const pagePosts = () => listPage("Saved posts", { kind: "post", status: "saved" }, null, (i) => [statusButton(i, "done", "Done"), statusButton(i, "archived", "Archive")]);
const pageJobs = () => listPage("Jobs", { kind: "job", status: "new" },
  h("button", { class: "btn primary", type: "button", onclick: async (e) => { e.target.disabled = true; try { const r = await api(`/api/campaigns/${campaignId}/fetch`, {}); toast(`+${r.created}${r.errors.length ? " | " + r.errors[0] : ""}`); render(); } finally { e.target.disabled = false; } } }, t("Fetch new jobs")),
  (i) => [statusButton(i, "done", "Done"), statusButton(i, "archived", "Archive")]);
const pagePeople = () => listPage("People", { kind: "person" },
  boot.plan.export ? h("a", { class: "btn", href: `/api/export?campaign=${campaignId}` }, t("Export CSV")) : null,
  (i) => [
    h("select", { "aria-label": t("Consent basis"), onchange: (e) => api(`/api/items/${i.id}/update`, { consent_basis: e.target.value }) }, boot.consent_bases.map((b) => h("option", { value: b, selected: b === i.consent_basis }, b))),
    h("button", { class: "btn", type: "button", onclick: async () => { if (confirm(t("Delete everything stored about this contact and never contact them again?"))) { await api(`/api/items/${i.id}/forget`, {}); render(); } } }, t("Delete data"))]);

async function pageFind() {
  const links = await api("/api/searches?" + q());
  return h("div", {}, h("h2", {}, t("Find")), h("p", { class: "sub" }, t("Open these searches yourself, then save the results you want. The app never browses LinkedIn for you.")),
    links.length ? links.map((l) => h("div", { class: "card row between" }, h("div", {}, h("span", { class: "name" }, l.label), " ", h("span", { class: "badge" }, l.type)), h("a", { class: "btn", href: l.url, target: "_blank", rel: "noopener noreferrer" }, t("Open")))) : h("div", { class: "empty" }, t("Nothing here yet.")));
}

function pageAdd() {
  let captured = {};
  if (location.hash.startsWith("#capture=")) {
    try { captured = JSON.parse(decodeURIComponent(location.hash.slice(9))); } catch (e) { captured = {}; }
    history.replaceState(null, "", location.pathname);
  }
  const text = h("textarea", { value: captured.s || "", dir: "auto" });
  const url = h("input", { value: captured.u || "", class: "ltr" });
  const loc = h("input", {});
  const file = h("input", { type: "file", accept: ".csv,text/csv" });
  const code = `javascript:(()=>{const d={u:location.href,s:String(getSelection()).slice(0,8000)};window.open('${location.origin}/#capture='+encodeURIComponent(JSON.stringify(d)))})()`;
  return h("div", {},
    h("h2", {}, t("Add")), h("p", { class: "sub" }),
    h("section", { class: "card" },
      h("label", { class: "field" }, h("span", {}, t("Paste a post or profile")), text),
      h("label", { class: "field" }, h("span", {}, t("Page link (optional)")), url),
      h("label", { class: "field" }, h("span", {}, t("Location (optional)")), loc),
      h("button", { class: "btn primary", type: "button", onclick: async () => {
        const r = await api(`/api/campaigns/${campaignId}/paste`, { text: text.value, url: url.value, location: loc.value });
        toast(`${t("Saved")}: ${r.item.full_name || r.item.kind} (${Math.round(r.item.score * 100)})`);
        text.value = ""; url.value = ""; loc.value = "";
      } }, t("Save"))),
    h("section", { class: "card" },
      h("h3", {}, t("Import a CSV file")), h("p", { class: "meta" }, t("Use LinkedIn's official Connections.csv export, or any CSV with name, title, company, location, URL and email columns. Importing a fresh Connections.csv also detects who accepted your requests.")),
      file, " ", h("button", { class: "btn", type: "button", onclick: async () => {
        if (!file.files[0]) return;
        const r = await api(`/api/campaigns/${campaignId}/import`, { csv: await file.files[0].text() });
        toast(`+${r.created} / ${r.updated}`);
      } }, t("Save"))),
    h("section", { class: "card" }, h("h3", {}, t("Quick capture")), h("p", { class: "meta" }, t("Drag this code into a new bookmark. Select text on any page, then click the bookmark to review it here. It reads only your selection.")), h("code", { class: "bm" }, code)));
}

async function pageTemplates() {
  const variants = await api("/api/variants?" + q());
  const name = h("input", {}); const step = h("select", {}, ["connect", "message", "email"].map((s) => h("option", { value: s }, t(STEP[s]))));
  const body = h("textarea", { dir: "auto" });
  return h("div", {}, h("h2", {}, t("Templates")),
    h("p", { class: "sub" }, `${t("Available fields")}: {greeting} {first_name} {title} {company} {at_company} {role_hint} {role_hook} {website} {sender_name} {sender_contact} {opt_out}`),
    variants.map((v) => {
      const area = h("textarea", { value: v.body, dir: "auto" });
      return h("article", { class: "card" },
        h("div", { class: "row between" }, h("div", {}, h("span", { class: "name" }, v.name), " ", h("span", { class: "badge" }, t(STEP[v.step]))), h("div", { class: "meta" }, `${t("Sent")}: ${v.sent} · ${t("Replies")}: ${v.replies}`)),
        (v.problems || []).map((p) => h("div", { class: "notice" }, p)), h("p", {}), area,
        h("div", { class: "row" }, h("button", { class: "btn", type: "button", onclick: async () => { await api(`/api/campaigns/${campaignId}/variant`, { name: v.name, step: v.step, body: area.value }); toast(t("Saved")); render(); } }, t("Save"))));
    }),
    h("section", { class: "card" }, h("h3", {}, t("Add a variant")),
      h("label", { class: "field" }, h("span", {}, t("Name")), name), h("label", { class: "field" }, h("span", {}, t("Step")), step), h("label", { class: "field" }, h("span", {}, t("Text")), body),
      h("button", { class: "btn primary", type: "button", onclick: async () => { if (!name.value || !body.value) return; await api(`/api/campaigns/${campaignId}/variant`, { name: name.value, step: step.value, body: body.value }); render(); } }, t("Save"))));
}

async function pageInsights() {
  const d = await api("/api/insights?" + q());
  const f = d.funnel; const l = d.learning;
  const stat = (n, label) => h("div", { class: "stat" }, h("b", {}, n === null || n === undefined ? "—" : n), h("span", {}, t(label)));
  const pct = (x) => (x === null || x === undefined ? null : `${Math.round(x * 100)}%`);
  const chips = (list) => (list.length ? h("div", { class: "row" }, list.map((x) => h("span", { class: "badge" }, x.replace(/^[a-z]:/, "")))) : h("div", { class: "meta" }, "—"));
  return h("div", {}, h("h2", {}, t("Insights")), h("p", { class: "sub" }),
    h("div", { class: "grid" }, stat(f.items, "Saved items"), stat(f.ready, "Ready"), stat(f.connect_sent, "Requests sent"), stat(f.accepted, "Accepted"), stat(f.messages_sent, "Messages sent"), stat(f.replies, "Replies"), stat(f.positive, "Positive")),
    h("h3", {}, t("Learning")),
    l.alpha ? null : h("div", { class: "notice" }, t("Rate at least 6 items, with both likes and dislikes, and the ranking starts learning.")),
    h("div", { class: "grid" }, stat(l.ratings, "Ratings"), stat(pct(l.early_accuracy), "Early accuracy"), stat(pct(l.recent_accuracy), "Recent accuracy"), stat(pct(l.alpha), "Model influence")),
    h("h3", {}, t("Learned likes")), chips(l.likes), h("h3", {}, t("Learned dislikes")), chips(l.dislikes),
    h("h3", {}, t("Rejection reasons")), chips(Object.entries(l.reasons).map(([k, v]) => `${reasonLabel(k)}: ${v}`)));
}

function pageSettings() {
  const c = campaign();
  const input = (label, value, type) => { const el = h("input", { value: value ?? "", type: type || "text" }); return [el, h("label", { class: "field" }, h("span", {}, t(label)), el)]; };
  const [site, siteF] = input("Website", c.website); const [sName, nameF] = input("Sender name", c.sender_name); const [contact, contactF] = input("Sender contact (email or phone)", c.sender_contact);
  const [cap, capF] = input("Daily limit", c.daily_cap, "number"); const [limit, limitF] = input("Connection note limit", c.note_limit, "number"); const [min, minF] = input("Minimum score", c.min_score, "number");
  const [subject, subjectF] = input("Email subject", c.email_subject);
  const commercial = h("input", { type: "checkbox", checked: !!c.commercial }); const auto = h("input", { type: "checkbox", checked: !!c.auto_email, disabled: !boot.plan.auto_email });
  const s = boot.smtp;
  const [host, hostF] = input("Server", s.smtp_host); const [port, portF] = input("Port", s.smtp_port || "587"); const [user, userF] = input("Username", s.smtp_user); const [from, fromF] = input("From address", s.smtp_from); const [att, attF] = input("File to attach to career emails", s.email_attachment);
  const token = h("input", { class: "ltr" });
  return h("div", {}, h("h2", {}, t("Settings")), h("p", { class: "sub" }),
    h("section", { class: "card" }, h("h3", {}, `${t("Campaign")}: ${c.name}`), siteF, nameF, contactF, capF, limitF, minF, subjectF,
      h("label", { class: "row" }, commercial, t("Commercial campaign (adds Canadian anti-spam checks)")), h("p", {}),
      h("label", { class: "row" }, auto, t("Send permitted email automatically")), h("p", {}),
      h("button", { class: "btn primary", type: "button", onclick: async () => {
        await api(`/api/campaigns/${campaignId}`, { website: site.value, sender_name: sName.value, sender_contact: contact.value, daily_cap: Number(cap.value), note_limit: Number(limit.value), min_score: Number(min.value), email_subject: subject.value, commercial: commercial.checked ? 1 : 0, auto_email: auto.checked ? 1 : 0 });
        boot = await api("/api/bootstrap"); toast(t("Saved")); render();
      } }, t("Save"))),
    h("section", { class: "card" }, h("h3", {}, t("Email account (SMTP)")), h("p", { class: "meta" }, t("Set the password in the REACHDESK_SMTP_PASSWORD environment variable. It is never stored.")), hostF, portF, userF, fromF, attF,
      h("button", { class: "btn", type: "button", onclick: async () => { await api("/api/settings", { smtp_host: host.value, smtp_port: port.value, smtp_user: user.value, smtp_from: from.value, email_attachment: att.value }); boot = await api("/api/bootstrap"); toast(t("Saved")); } }, t("Save"))),
    h("section", { class: "card" }, h("h3", {}, t("License")), h("p", { class: "meta" }, `${t("Plan")}: ${boot.plan.label}${boot.plan.customer ? " · " + boot.plan.customer : ""}`), token, " ",
      h("button", { class: "btn", type: "button", onclick: async () => { await api("/api/license", { token: token.value }); boot = await api("/api/bootstrap"); chrome(); toast(t("Saved")); render(); } }, t("Activate"))));
}

start();
