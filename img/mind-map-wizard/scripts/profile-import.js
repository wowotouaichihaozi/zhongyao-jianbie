(function () {
  const MAX_PROFILE_TEXT = 7000;

  const elements = {
    button: null,
    overlay: null,
    close: null,
    list: null,
    status: null,
    prompt: null,
  };

  function init() {
    elements.button = document.getElementById("import-learning-profile-btn");
    elements.overlay = document.getElementById("profile-import-overlay");
    elements.close = document.getElementById("profile-import-close");
    elements.list = document.getElementById("profile-import-list");
    elements.status = document.getElementById("profile-import-status");
    elements.prompt = document.getElementById("prompt");

    if (!elements.button || !elements.overlay || !elements.list || !elements.status) {
      return;
    }

    elements.button.addEventListener("click", openDialog);
    elements.close?.addEventListener("click", closeDialog);
    elements.overlay.addEventListener("click", (event) => {
      if (event.target === elements.overlay) {
        closeDialog();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && elements.overlay.classList.contains("show")) {
        closeDialog();
      }
    });
  }

  async function openDialog() {
    elements.overlay.classList.add("show");
    elements.overlay.setAttribute("aria-hidden", "false");
    elements.list.innerHTML = "";
    setStatus("正在读取已保存的学习画像...");

    try {
      const reports = await fetchLearningProfiles();
      renderReports(reports);
    } catch (error) {
      console.error("Failed to load learning profiles:", error);
      setStatus(error.message || "学习画像读取失败，请确认已登录后重试。");
    }
  }

  function closeDialog() {
    elements.overlay.classList.remove("show");
    elements.overlay.setAttribute("aria-hidden", "true");
  }

  async function fetchLearningProfiles() {
    const headers = {};
    const token = localStorage.getItem("authToken");
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch("/api/learning-profile/history", {
      method: "GET",
      credentials: "include",
      headers,
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(payload.msg || "学习画像读取失败，请稍后重试。");
    }

    if (Array.isArray(payload.reports)) {
      return payload.reports;
    }
    if (Array.isArray(payload.data)) {
      return payload.data;
    }
    if (Array.isArray(payload)) {
      return payload;
    }
    return [];
  }

  function renderReports(reports) {
    elements.list.innerHTML = "";

    if (!reports.length) {
      setStatus("项目数据库中还没有保存的学习画像。");
      return;
    }

    setStatus("");
    reports.forEach((report, index) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "profile-import-card";
      card.innerHTML = `
        <div class="profile-import-card-title">
          <span>${escapeHtml(getReportTitle(report, index))}</span>
          <span class="profile-import-card-date">${escapeHtml(formatDate(report.timestamp || report.created_at))}</span>
        </div>
        <div class="profile-import-card-summary">${escapeHtml(getReportSummary(report))}</div>
      `;
      card.addEventListener("click", () => importReport(report));
      elements.list.appendChild(card);
    });
  }

  function importReport(report) {
    const prompt = buildPrompt(report);
    if (!elements.prompt) {
      return;
    }

    elements.prompt.value = prompt;
    elements.prompt.dispatchEvent(new Event("input", { bubbles: true }));
    elements.prompt.focus();
    closeDialog();
    showToast("学习画像已导入输入框");
  }

  function buildPrompt(report) {
    const text = collectReportText(report);
    return [
      "请根据以下学习画像生成一张结构清晰的思维导图。",
      "重点覆盖：学习优势、薄弱环节、知识结构、学习习惯、推荐资源、下一步行动计划。",
      "",
      "学习画像内容：",
      text || "暂无可解析的画像内容。",
    ].join("\n");
  }

  function getReportTitle(report, index) {
    return report.title || report.name || report.subject || `学习画像 ${index + 1}`;
  }

  function getReportSummary(report) {
    const analysis = report.aiAnalysis || report.analysis || report.report || {};
    const directSummary =
      analysis.summary ||
      analysis.overview ||
      analysis.conclusion ||
      report.summary ||
      report.description;

    if (typeof directSummary === "string" && directSummary.trim()) {
      return trimText(directSummary.trim(), 150);
    }

    return trimText(collectReportText(report).replace(/\s+/g, " "), 150) || "点击导入该学习画像";
  }

  function collectReportText(value, depth = 0, seen = new Set()) {
    if (value == null || depth > 5) {
      return "";
    }

    if (typeof value === "string") {
      const normalized = value.trim();
      if (!normalized || normalized.length > 20000 || normalized.startsWith("data:")) {
        return "";
      }
      return normalized;
    }

    if (typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }

    if (seen.has(value)) {
      return "";
    }
    seen.add(value);

    if (Array.isArray(value)) {
      return trimText(
        value
          .map((item) => collectReportText(item, depth + 1, seen))
          .filter(Boolean)
          .join("\n"),
        MAX_PROFILE_TEXT,
      );
    }

    if (typeof value === "object") {
      const skipKeys = new Set(["id", "user_id", "avatar", "image", "base64", "fileContent"]);
      const priorityKeys = [
        "aiAnalysis",
        "summary",
        "overview",
        "strengths",
        "weaknesses",
        "recommendations",
        "learningStyle",
        "scaleScores",
        "chatBackground",
        "uploadFiles",
        "questionnaire",
      ];
      const keys = Object.keys(value).sort((a, b) => {
        const ai = priorityKeys.indexOf(a);
        const bi = priorityKeys.indexOf(b);
        return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
      });

      const parts = [];
      for (const key of keys) {
        if (skipKeys.has(key)) {
          continue;
        }
        const text = collectReportText(value[key], depth + 1, seen);
        if (text) {
          parts.push(`${labelKey(key)}：${text}`);
        }
        if (parts.join("\n").length >= MAX_PROFILE_TEXT) {
          break;
        }
      }
      return trimText(parts.join("\n"), MAX_PROFILE_TEXT);
    }

    return "";
  }

  function labelKey(key) {
    const labels = {
      aiAnalysis: "AI 分析",
      summary: "摘要",
      overview: "概览",
      strengths: "优势",
      weaknesses: "薄弱点",
      recommendations: "建议",
      learningStyle: "学习风格",
      scaleScores: "量表分数",
      chatBackground: "对话背景",
      uploadFiles: "上传资料",
      questionnaire: "问卷",
      timestamp: "生成时间",
    };
    return labels[key] || key;
  }

  function trimText(text, maxLength) {
    if (!text || text.length <= maxLength) {
      return text || "";
    }
    return `${text.slice(0, maxLength)}...`;
  }

  function formatDate(value) {
    if (!value) {
      return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value).slice(0, 16);
    }
    return date.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function setStatus(message) {
    elements.status.textContent = message;
  }

  function showToast(message) {
    const snackbar = document.getElementById("snackbar");
    if (!snackbar) {
      return;
    }
    snackbar.textContent = message;
    snackbar.style.display = "block";
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      snackbar.style.display = "none";
    }, 1800);
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
