const state = {
  role: "worker",
  workerScreen: "home",
  status: "not_submitted",
  media: [],
  voice: false,
  submitted: false,
  aiReady: false,
  published: false,
  acknowledged: false
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => el.classList.remove("show"), 2400);
}

function setRole(role) {
  state.role = role;
  $$(".role-tab").forEach(tab => tab.classList.toggle("active", tab.dataset.role === role));
  $$(".role-view").forEach(view => view.classList.remove("active"));
  $(`#${role}View`).classList.add("active");
  $$(".journey-step").forEach(step => step.classList.toggle("active", step.dataset.journey === role));
  window.scrollTo({ top: 260, behavior: "smooth" });
}

function setWorkerScreen(screen) {
  state.workerScreen = screen;
  $$(".worker-screen").forEach(el => el.classList.toggle("active", el.dataset.workerScreen === screen));
}

function setSystemStatus(status) {
  state.status = status;
  const labels = {
    not_submitted: "ยังไม่ส่ง",
    processing: "กำลังสร้างร่าง",
    ready: "รอ PM ตรวจ",
    published: "เผยแพร่แล้ว"
  };
  $("#systemStatus").textContent = labels[status];
  $("#statusDot").className = `status-dot ${status === "not_submitted" ? "" : status}`;
}

function renderPM() {
  const hasReport = state.aiReady && !state.published;
  $("#pmEmpty").classList.toggle("hidden", hasReport || state.published);
  $("#pmReview").classList.toggle("hidden", !hasReport);
  $("#pmPublished").classList.toggle("hidden", !state.published);
  $("#queueCount").textContent = hasReport ? "1" : "0";
  $("#pmBadge").classList.toggle("hidden", !hasReport);
}

function renderClient() {
  $("#clientEmpty").classList.toggle("hidden", state.published);
  $("#clientReport").classList.toggle("hidden", !state.published);
  $("#clientBadge").classList.toggle("hidden", !state.published);
}

function renderMedia() {
  const grid = $("#mediaGrid");
  grid.innerHTML = "";
  state.media.forEach((item, index) => {
    const tile = document.createElement("div");
    tile.className = "media-thumb";
    const media = document.createElement(item.type.startsWith("video") ? "video" : "img");
    media.src = item.url;
    if (media.tagName === "VIDEO") media.muted = true;
    const tag = document.createElement("span");
    tag.textContent = item.type.startsWith("video") ? "VIDEO" : String(index + 1).padStart(2, "0");
    tile.append(media, tag);
    grid.append(tile);
  });
  $("#mediaCount").textContent = `${state.media.length} ไฟล์`;
}

function useDemoMedia() {
  state.media = [
    { type: "image/demo", url: svgTile("CEILING", "#555d57", "#b7b5a8") },
    { type: "image/demo", url: svgTile("FIRST-FIX", "#414741", "#d2af56") },
    { type: "image/demo", url: svgTile("MATERIAL", "#aaa598", "#e2ddd0") },
    { type: "video/demo", url: svgTile("VIDEO 00:12", "#386c59", "#a8c6b8") }
  ];
  renderMedia();
}

function svgTile(label, a, b) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs><rect width="200" height="200" fill="url(#g)"/><path d="M-10 150L100 50L220 140M-20 90L80 0L220 110" fill="none" stroke="white" stroke-opacity=".35" stroke-width="8"/><text x="100" y="110" text-anchor="middle" fill="white" font-family="sans-serif" font-size="18" font-weight="bold">${label}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function prepareReview() {
  if (!state.media.length) useDemoMedia();
  const photos = state.media.filter(x => !x.type.startsWith("video")).length;
  const videos = state.media.filter(x => x.type.startsWith("video")).length;
  $("#reviewMedia").textContent = `${photos} รูป${videos ? ` · ${videos} วิดีโอ` : ""}${state.voice ? " · 1 เสียง" : ""}`;
  $("#reviewNote").textContent = $("#siteNote").value.trim() || "งานฝ้า Level 2 ต่อเนื่อง ตรวจ first-fix แล้ว ไม่มีผลต่อแผนหลัก";
  const selectedIssues = $$("[data-issue]:checked").map(input => input.dataset.issue);
  $("#reviewIssues").textContent = selectedIssues.length
    ? `${selectedIssues.map(x => x[0].toUpperCase() + x.slice(1)).join(", ")} · ${$("#issueNote").value.trim() || "มีประเด็นที่ PM ต้องตรวจเพิ่มเติม"}`
    : "ไม่พบประเด็นที่ต้องติดตามจาก checklist";
  $("#reviewTomorrow").textContent = $("#tomorrowPlan").value;
}

function runAIProcessing() {
  setSystemStatus("processing");
  setTimeout(() => {
    state.aiReady = true;
    setSystemStatus("ready");
    $("#aiProcessRow").innerHTML = '<span class="done">✓</span><b>AI สร้างร่างรายงาน</b><small>Ready</small>';
    $("#pmProcessRow").classList.remove("muted");
    $("#pmProcessRow").innerHTML = '<span>4</span><b>PM ตรวจและอนุมัติ</b><small>Action required</small>';
    $("#goToPM").classList.remove("hidden");
    renderPM();
    toast("ร่างรายงานพร้อมให้ PM ตรวจแล้ว");
  }, 1800);
}

function publishReport() {
  if (!$("#approvalCheck").checked) {
    toast("กรุณายืนยันว่าตรวจหลักฐานและปลายทางแล้ว");
    $("#approvalCheck").focus();
    return;
  }
  const progress = Math.max(0, Math.min(100, Number($("#progressValue").value) || 0));
  $("#clientSummary").textContent = $("#pmSummary").value.trim();
  $("#clientIssues").textContent = $("#pmIssues").value.trim();
  $("#clientTomorrow").textContent = $("#pmTomorrow").value.trim();
  $("#clientProgress").textContent = `${progress}%`;
  $("#progressBar").style.width = `${progress}%`;
  state.published = true;
  setSystemStatus("published");
  renderPM();
  renderClient();
  toast("เผยแพร่รายงานไปยัง Client LINE Group แล้ว");
}

function resetDemo() {
  state.role = "worker";
  state.workerScreen = "home";
  state.status = "not_submitted";
  state.media.forEach(item => { if (item.url.startsWith("blob:")) URL.revokeObjectURL(item.url); });
  state.media = [];
  state.voice = false;
  state.submitted = false;
  state.aiReady = false;
  state.published = false;
  state.acknowledged = false;
  $("#siteNote").value = "";
  $("#issueNote").value = "";
  $$("[data-issue]").forEach(i => i.checked = false);
  $("#approvalCheck").checked = false;
  $("#clientResponse").classList.add("hidden");
  $("#clientResponse").textContent = "";
  $("#acknowledge").textContent = "✓ รับทราบ";
  $("#aiProcessRow").innerHTML = '<span class="spinner"></span><b>AI สร้างร่างรายงาน</b><small>Processing</small>';
  $("#pmProcessRow").className = "muted";
  $("#pmProcessRow").innerHTML = '<span>4</span><b>PM ตรวจและอนุมัติ</b><small>Waiting</small>';
  $("#goToPM").classList.add("hidden");
  renderMedia();
  setSystemStatus("not_submitted");
  setWorkerScreen("home");
  renderPM();
  renderClient();
  setRole("worker");
  toast("รีเซ็ต mockup แล้ว");
}

$$(".role-tab").forEach(tab => tab.addEventListener("click", () => setRole(tab.dataset.role)));
$$(".switch-role").forEach(button => button.addEventListener("click", () => setRole(button.dataset.target)));
$("#resetDemo").addEventListener("click", resetDemo);
$("#startReport").addEventListener("click", () => setWorkerScreen("capture"));
$("#startReportMenu").addEventListener("click", () => setWorkerScreen("capture"));
$$(".worker-back").forEach(button => button.addEventListener("click", () => setWorkerScreen(button.dataset.back)));

$("#mediaInput").addEventListener("change", event => {
  state.media.forEach(item => { if (item.url.startsWith("blob:")) URL.revokeObjectURL(item.url); });
  state.media = [...event.target.files].slice(0, 12).map(file => ({ type: file.type, url: URL.createObjectURL(file) }));
  renderMedia();
  toast(`เลือก ${state.media.length} ไฟล์แล้ว`);
});

$("#voiceButton").addEventListener("click", () => {
  const button = $("#voiceButton");
  if (!button.classList.contains("recording") && !state.voice) {
    button.classList.add("recording");
    button.querySelector("b").textContent = "กำลังบันทึก... กดอีกครั้งเพื่อหยุด";
    $("#voiceStatus").textContent = "00:01 · บันทึกจำลอง ไม่มีการเปิดไมโครโฟน";
  } else {
    button.classList.remove("recording");
    state.voice = true;
    button.querySelector("b").textContent = "บันทึกเสียงแล้ว · 00:18";
    $("#voiceStatus").textContent = "AI จะถอดเสียงหลังส่งรายงาน";
    toast("เพิ่ม voice note จำลองแล้ว");
  }
});

$("#captureContinue").addEventListener("click", () => {
  if (!state.media.length) {
    useDemoMedia();
    toast("ใส่หลักฐานจำลอง 4 รายการให้ทดลองแล้ว");
  }
  setWorkerScreen("checklist");
});

$$('[data-issue]').forEach(input => input.addEventListener("change", () => {
  $("#issueDetail").classList.toggle("hidden", !$$('[data-issue]:checked').length);
}));

$("#checkContinue").addEventListener("click", () => {
  prepareReview();
  setWorkerScreen("review");
});

$("#submitReport").addEventListener("click", () => {
  state.submitted = true;
  setWorkerScreen("submitted");
  runAIProcessing();
});

$("#goToPM").addEventListener("click", () => setRole("pm"));
$("#rejectReport").addEventListener("click", () => {
  toast("ส่งคำขอข้อมูลเพิ่มกลับไปยัง Site Worker แล้ว");
  setRole("worker");
  setWorkerScreen("checklist");
});
$("#approveReport").addEventListener("click", publishReport);
$("#goToClient").addEventListener("click", () => setRole("client"));

$("#acknowledge").addEventListener("click", () => {
  state.acknowledged = true;
  $("#acknowledge").textContent = "✓ รับทราบแล้ว";
  $("#clientResponse").textContent = "รับทราบรายงานแล้ว · 17:10";
  $("#clientResponse").classList.remove("hidden");
  toast("บันทึกการรับทราบแล้ว — ไม่ใช่การรับรองงานตามสัญญา");
});

$("#askQuestion").addEventListener("click", () => $("#questionDialog").showModal());
$("#sendQuestion").addEventListener("click", event => {
  const text = $("#questionText").value.trim();
  if (!text) {
    event.preventDefault();
    toast("กรุณาพิมพ์คำถาม");
    return;
  }
  $("#clientResponse").textContent = text;
  $("#clientResponse").classList.remove("hidden");
  toast("ส่งคำถามและผูกกับรายงาน RD-024 แล้ว");
});

$("#openFullReport").addEventListener("click", () => toast("MVP จริงจะเปิดรายงานฉบับเต็มใน Rayadee Hub"));

renderPM();
renderClient();

