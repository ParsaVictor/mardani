// Send desk. Live mode talks to the local ReachDesk server; a standalone file carries
// its data in window.DESK_DATA and remembers what was sent in this browser.
(function () {
  "use strict";
  const LIVE = !window.DESK_DATA;
  const STEP = { connect: "درخواست کانکت", message: "پیام" };
  const $ = (id) => document.getElementById(id);
  let data = window.DESK_DATA || null;
  let done = {};
  const storeKey = () => "reachdesk-desk-" + (data ? data.campaign.slug : "");

  function toast(text) {
    const t = $("toast");
    t.textContent = text;
    t.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => t.classList.remove("show"), 2600);
  }

  async function api(path, body) {
    const res = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json", "X-ReachDesk": "1" }, body: JSON.stringify(body) });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || res.status);
    return json;
  }

  async function copy(text, area) {
    try { await navigator.clipboard.writeText(text); return true; }
    catch (e) { area.focus(); area.select(); try { return document.execCommand("copy"); } catch (e2) { return false; } }
  }

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") node.className = v; else if (k.startsWith("on")) node.addEventListener(k.slice(2), v); else node.setAttribute(k, v);
    }
    for (const kid of kids) if (kid !== null && kid !== undefined && kid !== "") node.append(kid);
    return node;
  }

  function counts() {
    const left = data.cards.filter((c) => !done[c.id]).length;
    $("left").textContent = left;
    $("today").textContent = data.sent_today + Object.values(done).filter((v) => v === "sent").length + " / " + data.daily_cap;
    $("empty").hidden = left > 0;
  }

  async function finish(card, node, how) {
    if (LIVE) {
      try { await api(`/api/outreach/${card.id}/${how === "sent" ? "sent" : "skip"}`, {}); }
      catch (e) { return toast("ثبت نشد: " + e.message); }
    }
    done[card.id] = how;
    try { localStorage.setItem(storeKey(), JSON.stringify(done)); } catch (e) { /* private window */ }
    node.classList.add("done");
    node.querySelector(".tag").textContent = how === "sent" ? "فرستاده شد" : "رد شد";
    counts();
    const next = node.parentElement.querySelector(".card:not(.done)");
    if (next) next.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function card(c) {
    const limit = c.step === "connect" ? data.campaign.note_limit : 0;
    const area = el("textarea", { class: "text", rows: c.step === "connect" ? "3" : "8", "aria-label": "Message" });
    area.value = c.text;
    const count = el("div", { class: "count" });
    const recount = () => { count.textContent = limit ? `${area.value.length} / ${limit}` : `${area.value.length} chars`; count.classList.toggle("over", !!limit && area.value.length > limit); };
    area.addEventListener("input", recount);
    recount();
    const node = el("li", { class: "card" + (done[c.id] ? " done" : "") });
    const open = el("a", { class: "b go", href: c.url || "#", target: "_blank", rel: "noopener", onclick: async (e) => {
      if (!c.url) e.preventDefault();
      if (limit && area.value.length > limit) { e.preventDefault(); return toast("یادداشت کانکت از " + limit + " کاراکتر بیشتر است."); }
      const ok = await copy(area.value, area);
      toast(ok ? (c.step === "connect" ? "کپی شد. در لینکدین: Connect ← Add a note ← بچسبان ← Send" : "کپی شد. در لینکدین: Message ← بچسبان ← Send") : "Ctrl+C بزن تا کپی شود.");
    } }, c.url ? "کپی متن و باز کردن پروفایل" : "کپی متن");
    node.append(
      el("div", { class: "head" }, el("h2", { class: "name" }, c.name),
        el("span", { class: "tag" }, done[c.id] ? (done[c.id] === "sent" ? "فرستاده شد" : "رد شد") : STEP[c.step] || c.step)),
      el("div", { class: "meta" }, [c.title, c.company, c.location].filter(Boolean).join(" · ")),
      el("div", { class: "link" }, c.url ? el("a", { href: c.url, target: "_blank", rel: "noopener" }, c.url.replace(/^https:\/\/(www\.)?/, "")) : "لینک پروفایل ندارد"),
      c.why && c.why.length ? el("div", { class: "why" }, "امتیاز " + Math.round(c.score * 100) + " · " + c.why.join(" · ")) : "",
      area, count,
      el("div", { class: "acts" }, open,
        el("button", { class: "b", type: "button", onclick: () => finish(c, node, "sent") }, "فرستادم"),
        el("button", { class: "b", type: "button", onclick: () => finish(c, node, "skip") }, "رد کن")));
    return node;
  }

  function render() {
    try { done = JSON.parse(localStorage.getItem(storeKey()) || "{}"); } catch (e) { done = {}; }
    if (LIVE) done = {};
    $("title").textContent = "ارسال امروز: " + data.campaign.name;
    document.title = "ReachDesk · " + data.campaign.name;
    const list = $("cards");
    list.replaceChildren(...data.cards.map(card));
    if (data.sent_today >= data.daily_cap) { $("note").hidden = false; $("note").textContent = "سقف امروز پر شده است. برای امنیت حساب، بقیه را فردا بفرست."; }
    counts();
  }

  async function start() {
    if (!LIVE) return render();
    const params = new URLSearchParams(location.search);
    try { data = await api("/api/desk?campaign=" + encodeURIComponent(params.get("campaign") || "")); render(); }
    catch (e) { $("note").hidden = false; $("note").textContent = "خطا: " + e.message; }
  }
  start();
})();
