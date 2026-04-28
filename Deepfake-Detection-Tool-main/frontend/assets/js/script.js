console.log("DeepDetect JS loaded ✅");

// ── Shared state ──────────────────────────────────────────────────────────────
let selectedFile = null;

// ── Feedback / star rating ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const stars       = document.querySelectorAll(".star");
  const feedbackText = document.getElementById("feedbackText");
  const submitBtn   = document.getElementById("submitFeedback");
  const reviewsList = document.getElementById("reviewsList");

  if (stars.length && submitBtn) {
    let selectedRating = 0;

    stars.forEach(star => {
      star.addEventListener("click", () => {
        selectedRating = parseInt(star.getAttribute("data-rating"));
        stars.forEach(s => s.classList.remove("selected"));
        for (let s of stars) {
          s.classList.add("selected");
          if (s === star) break;
        }
      });
    });

    submitBtn.addEventListener("click", () => {
      const feedback = feedbackText.value.trim();
      if (!selectedRating) return alert("Please select a star rating.");
      if (!feedback)       return alert("Please write some feedback.");

      const li = document.createElement("li");
      li.innerHTML = `<strong>★${selectedRating}</strong> — ${feedback}`;
      reviewsList.prepend(li);

      feedbackText.value = "";
      stars.forEach(s => s.classList.remove("selected"));
      selectedRating = 0;
    });
  }
});

// ── Animate a single progress bar ─────────────────────────────────────────────
function animateProgress(barId, txtId, targetPct, delayMs) {
  return new Promise(resolve => {
    setTimeout(() => {
      let val  = 0;
      const step = targetPct / 30;
      const iv = setInterval(() => {
        val = Math.min(val + step, targetPct);
        const bar = document.getElementById(barId);
        const txt = document.getElementById(txtId);
        if (bar) bar.style.width = val + "%";
        if (txt) txt.textContent = Math.round(val) + "%";
        if (val >= targetPct) { clearInterval(iv); resolve(); }
      }, 40);
    }, delayMs);
  });
}

// ── Main detection function ───────────────────────────────────────────────────
async function runDetection() {
  if (!selectedFile) {
    alert("Please upload an image first!");
    return;
  }

  // ── Show the results panel in "scanning" state ────────────────────────────
  const placeholder  = document.getElementById("resultsPlaceholder");
  const content      = document.getElementById("resultsContent");
  const progressSec  = document.getElementById("analysisProgress");
  const detailGrid   = document.getElementById("detailGrid");
  const reportActs   = document.getElementById("reportActions");
  const verdictCard  = document.getElementById("verdictCard");
  const verdictIcon  = document.getElementById("verdictIcon");
  const verdictValue = document.getElementById("verdictValue");
  const verdictConf  = document.getElementById("verdictConf");
  const verdictScore = document.getElementById("verdictScore");

  if (placeholder)  placeholder.classList.add("hidden");
  if (content)      content.classList.remove("hidden");
  if (progressSec)  progressSec.classList.remove("hidden");
  if (detailGrid)   detailGrid.classList.add("hidden");
  if (reportActs)   reportActs.classList.add("hidden");

  if (verdictCard)  verdictCard.className = "verdict-card";
  if (verdictIcon)  verdictIcon.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  if (verdictValue) verdictValue.textContent = "Analyzing…";
  if (verdictConf)  verdictConf.textContent  = "";
  if (verdictScore) verdictScore.textContent  = "";

  // Reset progress bars
  ["p1","p2","p3","p4"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.width = "0%";
  });
  ["p1t","p2t","p3t","p4t"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = "0%";
  });

  // ── Send image to Flask backend ───────────────────────────────────────────
  const formData = new FormData();
  formData.append("image", selectedFile);

  let data;
  try {
    // Animate the first two progress bars while waiting for the response
    const p1Promise = animateProgress("p1","p1t", 85, 0);
    const p2Promise = animateProgress("p2","p2t", 72, 300);

    const BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
      ? "http://localhost:5000" 
      : "https://your-backend-url.onrender.com"; // Change this after deploying backend

    const res = await fetch(`${BASE_URL}/predict`, {
      method: "POST",
      body:   formData
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.error || `Server returned HTTP ${res.status}`);
    }

    data = await res.json();
    console.log("Backend response:", data);

    if (data.error) {
      throw new Error(data.error);
    }

    await Promise.all([p1Promise, p2Promise]);

  } catch (err) {
    console.error("Detection error:", err);

    if (progressSec)  progressSec.classList.add("hidden");
    if (verdictCard)  verdictCard.className   = "verdict-card fake";
    if (verdictIcon)  verdictIcon.innerHTML   = '<i class="fas fa-exclamation-triangle"></i>';
    if (verdictValue) verdictValue.textContent = "⚠ Connection Error";
    if (verdictConf)  verdictConf.textContent  =
        err.message.includes("Failed to fetch")
          ? "Cannot reach backend — make sure Flask is running on port 5000."
          : err.message;
    return;
  }

  // ── Animate remaining progress bars ───────────────────────────────────────
  await Promise.all([
    animateProgress("p3","p3t", 91, 0),
    animateProgress("p4","p4t", 68, 200),
  ]);

  if (progressSec) progressSec.classList.add("hidden");

  // ── Show verdict ──────────────────────────────────────────────────────────
  showResults(data);
}

// ── Render results to the UI ──────────────────────────────────────────────────
function showResults(data) {
  const isFake     = data.result === "Deepfake";
  const confidence = data.confidence;

  const verdictCard  = document.getElementById("verdictCard");
  const verdictIcon  = document.getElementById("verdictIcon");
  const verdictValue = document.getElementById("verdictValue");
  const verdictConf  = document.getElementById("verdictConf");
  const verdictScore = document.getElementById("verdictScore");
  const detailGrid   = document.getElementById("detailGrid");
  const reportActs   = document.getElementById("reportActions");
  const content      = document.getElementById("resultsContent");
  const placeholder  = document.getElementById("resultsPlaceholder");

  if (placeholder) placeholder.classList.add("hidden");
  if (content)     content.classList.remove("hidden");

  if (isFake) {
    if (verdictCard)  verdictCard.className   = "verdict-card fake";
    if (verdictIcon)  verdictIcon.innerHTML   = '<i class="fas fa-times-circle"></i>';
    if (verdictValue) verdictValue.textContent = "⚠ DEEPFAKE DETECTED";
  } else {
    if (verdictCard)  verdictCard.className   = "verdict-card authentic";
    if (verdictIcon)  verdictIcon.innerHTML   = '<i class="fas fa-check-circle"></i>';
    if (verdictValue) verdictValue.textContent = "✓ AUTHENTIC";
  }

  if (verdictConf)  verdictConf.textContent  = `Confidence: ${confidence}%`;
  if (verdictScore) verdictScore.textContent  = `${Math.round(confidence)}%`;

  // ── Fill detail cards ─────────────────────────────────────────────────────
  const set = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };

  if (isFake) {
    set("ganVal",   "Artifacts detected");
    set("pixelVal", "Inconsistent");
    set("faceVal",  "Anomalies found");
    set("metaVal",  "Missing / stripped");
    set("lightVal", "Mismatch");
    set("compVal",  "Abnormal");
  } else {
    set("ganVal",   "Clean");
    set("pixelVal", "Consistent");
    set("faceVal",  "Normal");
    set("metaVal",  "Valid");
    set("lightVal", "Correct");
    set("compVal",  "Normal");
  }

  if (detailGrid) detailGrid.classList.remove("hidden");
  if (reportActs) reportActs.classList.remove("hidden");
}