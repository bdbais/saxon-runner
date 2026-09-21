// Numero e data dell'ultima versione, letti dalla release di GitHub.
// Se la richiesta non riesce la riga resta nascosta: i link funzionano comunque.
fetch("https://api.github.com/repos/bdbais/saxon-runner/releases/latest",
      { headers: { Accept: "application/vnd.github+json" } })
  .then((r) => (r.ok ? r.json() : null))
  .then((d) => {
    if (!d || !d.tag_name) return;
    const el = document.getElementById("version");
    const when = new Date(d.published_at).toLocaleDateString("it-IT",
      { day: "numeric", month: "long", year: "numeric" });
    el.textContent = `Versione ${d.tag_name.replace(/^v/i, "")} · ${when}`;
    el.hidden = false;
  })
  .catch(() => {});
