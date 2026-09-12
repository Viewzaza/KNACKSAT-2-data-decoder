const tbody = document.querySelector("#obs-table tbody");
const refreshBtn = document.getElementById("refresh");
const resultPanel = document.getElementById("result-panel");
const resultObsId = document.getElementById("result-obs-id");
const resultMeta = document.getElementById("result-meta");
const resultLog = document.getElementById("result-log");
const framesBody = document.querySelector("#frames-table tbody");

async function fetchObservations() {
  const status = document.getElementById("status").value;
  const limit = document.getElementById("limit").value;
  const params = new URLSearchParams({ limit });
  if (status) params.set("status", status);

  tbody.innerHTML = `<tr><td colspan="7">Loading…</td></tr>`;
  try {
    const resp = await fetch(`/api/observations?${params}`);
    if (!resp.ok) throw new Error(await resp.text());
    const obs = await resp.json();
    renderObservations(obs);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7">Error: ${escapeHtml(String(err))}</td></tr>`;
  }
}

function renderObservations(obs) {
  if (obs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7">No observations found for these filters.</td></tr>`;
    return;
  }
  tbody.innerHTML = "";
  for (const o of obs) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${o.id}</td>
      <td>${o.start ?? ""}</td>
      <td>${escapeHtml(o.station_name ?? "")}</td>
      <td>${escapeHtml(o.transmitter_description ?? o.transmitter_mode ?? "")}</td>
      <td><span class="tag">${escapeHtml(o.status ?? "")}</span></td>
      <td>${o.has_audio ? "yes" : "no"}</td>
      <td></td>
    `;
    const actionCell = tr.lastElementChild;
    const btn = document.createElement("button");
    btn.textContent = "Decode";
    btn.disabled = !o.has_audio;
    btn.onclick = () => decodeObservation(o.id, btn);
    actionCell.appendChild(btn);
    tbody.appendChild(tr);
  }
}

async function decodeObservation(id, btn) {
  btn.disabled = true;
  btn.textContent = "Starting…";
  try {
    const resp = await fetch(`/api/decode/${id}`, { method: "POST" });
    if (!resp.ok) throw new Error(await resp.text());
    const { job_id } = await resp.json();
    btn.textContent = "Decoding…";
    await pollJob(job_id, id);
  } catch (err) {
    alert(`Decode failed to start: ${err}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Decode";
  }
}

async function pollJob(jobId, obsId) {
  while (true) {
    const resp = await fetch(`/api/jobs/${jobId}`);
    const job = await resp.json();
    if (job.status === "done") {
      showResult(obsId, job.result);
      return;
    }
    if (job.status === "error") {
      alert(`Decode error: ${job.error}`);
      return;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
}

function showResult(obsId, result) {
  resultPanel.hidden = false;
  resultObsId.textContent = obsId;
  resultMeta.textContent = `${result.frame_count} AX.25 frame(s) decoded in ${result.duration_sec}s.`;
  resultLog.textContent = result.log_tail;

  framesBody.innerHTML = "";
  result.frames.forEach((f, i) => {
    const tr = document.createElement("tr");
    if (f.parsed) {
      tr.innerHTML = `
        <td>${i + 1}</td>
        <td>${escapeHtml(f.src)}</td>
        <td>${escapeHtml(f.dest)}</td>
        <td>0x${f.pid.toString(16)}</td>
        <td>${escapeHtml(f.info_hex)}</td>
        <td>${escapeHtml(f.info_ascii)}</td>
      `;
    } else {
      tr.innerHTML = `
        <td>${i + 1}</td>
        <td colspan="4">unparsed frame</td>
        <td>${escapeHtml(f.raw_hex)}</td>
      `;
    }
    framesBody.appendChild(tr);
  });

  resultPanel.scrollIntoView({ behavior: "smooth" });
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

refreshBtn.addEventListener("click", fetchObservations);
fetchObservations();
