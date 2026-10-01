const $ = id => document.getElementById(id);
let token = localStorage.getItem("ps_token");
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

async function api(path, method = "GET", body) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Please check your input");
  return data;
}

function show(loggedIn) {
  $("auth").hidden = loggedIn; $("dash").hidden = !loggedIn; $("logout").hidden = !loggedIn;
}

async function auth(kind) {
  try {
    const d = await api("/api/auth/" + kind, "POST",
      { name: $("name").value, email: $("email").value, password: $("password").value });
    token = d.token; localStorage.setItem("ps_token", token); $("who").textContent = d.name;
    show(true); refresh();
  } catch (e) { $("authMsg").textContent = e.message; }
}

async function refresh() {
  const [sum, exps] = await Promise.all([api("/api/summary"), api("/api/expenses")]);
  $("summary").innerHTML = sum.length ? sum.map(s => `
    <div><b>${esc(s.category)}</b> - spent ${s.spent} of ${s.limit} (${s.remaining} left)
    <div class="bar"><i class="${s.pct > 100 ? "over" : ""}" style="width:${Math.min(s.pct, 100)}%"></i></div></div>`).join("")
    : "<p>No budgets yet. Set one above.</p>";
  $("expenses").innerHTML = exps.length ? exps.map(e => `
    <li><span>${esc(e.title)} (${esc(e.category)}) - ${e.amount}</span>
    <button data-id="${e.id}" aria-label="Delete expense">Delete</button></li>`).join("")
    : "<li>No expenses yet.</li>";
}

$("login").onclick = () => auth("login");
$("register").onclick = () => auth("register");
$("logout").onclick = () => { localStorage.removeItem("ps_token"); token = null; show(false); };
$("saveBudget").onclick = async () => {
  try {
    await api("/api/budgets", "POST", { category: $("bCat").value, limit: +$("bLimit").value });
    $("rCat").value = $("bCat").value; $("rBudget").value = $("bLimit").value;
    refresh(); recommend();
  } catch (e) { alert(e.message); }
};
$("addExp").onclick = async () => {
  await api("/api/expenses", "POST", { category: $("eCat").value, title: $("eTitle").value, amount: +$("eAmt").value }).catch(e => alert(e.message));
  refresh();
};
$("expenses").onclick = async e => {
  if (e.target.dataset.id) { await api("/api/expenses/" + e.target.dataset.id, "DELETE"); refresh(); }
};
async function recommend() {
  $("answer").innerHTML = "Finding products in your budget...";
  try {
    const d = await api("/api/ai/recommend", "POST",
      { category: $("rCat").value, budget: +$("rBudget").value, details: $("rDet").value });
    $("answer").innerHTML =
      "<h4>Budget split</h4><ul>" + d.plan.map(p => `<li><span>${esc(p.item)}</span><b>${Math.round(p.amount)}</b></li>`).join("") + "</ul>" +
      "<h4>Products to buy</h4>" + d.products.map(p => `
        <div class="prod"><b>${esc(p.name)}</b> - about ${Math.round(p.price)}<br><small>${esc(p.reason)}</small><br>
        <a href="${p.links.amazon}" target="_blank" rel="noopener">Amazon</a>
        <a href="${p.links.flipkart}" target="_blank" rel="noopener">Flipkart</a></div>`).join("") +
      "<h4>Saving tips</h4><ul>" + d.tips.map(t => `<li>${esc(t)}</li>`).join("") + "</ul>";
  } catch (e) { $("answer").textContent = e.message; }
}
$("ask").onclick = recommend;

if (token) api("/api/auth/me").then(u => { $("who").textContent = u.name; show(true); refresh(); })
  .catch(() => { localStorage.removeItem("ps_token"); show(false); });
