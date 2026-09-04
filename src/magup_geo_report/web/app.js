const I18N = {
  zh: {
    eyebrow: "开源 · magup.ai",
    lede: "开源版需自行配置 LLM 与搜索密钥。",
    ctaFree: "免费生成",
    tabCustomer: "品牌信息",
    tabLanguage: "语言",
    tabPlatforms: "平台选择",
    tabPrompts: "提示词",
    tabKeys: "可选密钥",
    site: "站点 URL",
    siteHint: "填写官网即可。",
    brand: "品牌名称",
    brandPh: "请输入品牌名称",
    intro: "品牌简介",
    introPh: "留空则自动抓取官网并填入",
    introHint: "留空则自动抓取官网并填入。",
    competitors: "竞品（最多 4 个）",
    competitorPh: "竞品名",
    add: "添加",
    langHint: "最终报告语言。提示词语言可在「提示词」里另选。",
    platformHint: "选择要覆盖的 AI 平台，可多选。",
    totalQ: "问题数量",
    categoryTerm: "品类词",
    brandTerm: "品牌词",
    ratioHint: "品类词不出现品牌名，用来看品类推荐；品牌词带上品牌名，用来看品牌是否被提及。",
    promptLangs: "提示词语言",
    notes: "补充说明",
    notesPh: "可选，生成提示词时参考",
    useLlm: "用官方 API 生成（需自行配置密钥；否则用模板）",
    genPrompts: "生成提示词",
    genPromptsBusy: "正在生成…",
    genPromptsWait: "正在根据品牌信息生成问题…",
    crawlWait: "正在抓取官网并生成简介…",
    promptList: "提示词列表",
    addPrompt: "+ 手动添加",
    bulkPrompt: "批量添加",
    bulkTitle: "批量添加提示词",
    bulkHint: "一行一条。空行会自动忽略。",
    bulkPh: "把提示词粘贴到这里，每行一条",
    cancel: "取消",
    promptEmpty: "还没有提示词。点左侧生成，或批量添加。",
    fetchAnswers: "生成时拉取提示词原始问答（DataForSEO Live 并发；已配置则默认开启）",
    keysEnvBoth: "已从 .env 填入 LLM 与 DataForSEO。密钥中间已打码，保持即可；改写后会优先用页面上的值。",
    keysEnvLlm: "已从 .env 填入 LLM 配置。密钥中间已打码，保持即可。",
    keysEnvDfs: "已从 .env 填入 DataForSEO。账号与密码中间已打码，保持即可。",
    barTitle: "生成报告",
    run: "生成报告",
    runBusy: "生成中…",
    confirmTitle: "确认生成报告",
    confirmHint: "请核对以下信息，确认后再生成。",
    confirmRun: "确认生成",
    confirmPrompts: "{n} 条提示词",
    preview: "报告",
    missing: "未填写",
    progressQueued: "排队中",
    progressAudit: "检测站点",
    progressAnswers: "拉取问答",
    progressSearch: "拉取搜索与站外信源",
    progressAssemble: "整理报告",
    progressDone: "完成",
    progressError: "生成失败",
  },
  en: {
    eyebrow: "Open source · magup.ai",
    lede: "The open-source run needs your own LLM and search keys.",
    ctaFree: "Generate for free",
    tabCustomer: "Customer",
    tabLanguage: "Language",
    tabPlatforms: "Platforms",
    tabPrompts: "Prompts",
    tabKeys: "Optional keys",
    site: "Site URL",
    siteHint: "Enter the official site URL.",
    brand: "Brand name",
    brandPh: "Enter brand name",
    intro: "Brand intro",
    introPh: "Leave blank to crawl the official site",
    introHint: "Leave blank to crawl the official site automatically.",
    competitors: "Competitors (max 4)",
    competitorPh: "Competitor name",
    add: "Add",
    langHint: "Report language. Prompt languages can differ in the Prompts tab.",
    platformHint: "Select the AI platforms to cover. Multiple allowed.",
    totalQ: "Number of questions",
    categoryTerm: "Category terms",
    brandTerm: "Brand terms",
    ratioHint: "Category terms omit the brand name (category/use-case questions). Brand terms mention the brand.",
    promptLangs: "Prompt languages",
    notes: "Extra notes",
    notesPh: "Optional context for prompt generation",
    useLlm: "Generate with official API (needs your key; otherwise templates)",
    genPrompts: "Generate prompts",
    genPromptsBusy: "Generating…",
    genPromptsWait: "Generating questions from brand info…",
    crawlWait: "Crawling the site to draft an intro…",
    promptList: "Prompt list",
    addPrompt: "+ Add manually",
    bulkPrompt: "Bulk add",
    bulkTitle: "Bulk add prompts",
    bulkHint: "One prompt per line. Empty lines are ignored.",
    bulkPh: "Paste prompts here, one per line",
    cancel: "Cancel",
    promptEmpty: "No prompts yet. Generate on the left, or bulk add.",
    fetchAnswers: "Fetch raw prompt answers when generating (DataForSEO live, concurrent; on by default if keys are set)",
    keysEnvBoth: "LLM and DataForSEO are filled from .env. Secrets are masked in the middle; keep them or overwrite to use page values.",
    keysEnvLlm: "LLM settings are filled from .env. The key is masked in the middle; keep it or overwrite.",
    keysEnvDfs: "DataForSEO is filled from .env. Login and password are masked in the middle; keep them or overwrite.",
    barTitle: "Generate report",
    run: "Generate report",
    runBusy: "Generating…",
    confirmTitle: "Confirm report",
    confirmHint: "Review these details, then confirm to generate.",
    confirmRun: "Confirm and generate",
    confirmPrompts: "{n} prompts",
    preview: "Report",
    missing: "Not set",
    progressQueued: "Queued",
    progressAudit: "Checking the site",
    progressAnswers: "Fetching answers",
    progressSearch: "Fetching search and off-site sources",
    progressAssemble: "Assembling the report",
    progressDone: "Done",
    progressError: "Generation failed",
  },
};

const state = {
  ui: "zh",
  languages: [
    { value: "zh-Hans", label: "简体中文" },
    { value: "en", label: "English" },
    { value: "pt-PT", label: "Português (PT)" },
    { value: "pt-BR", label: "Português (BR)" },
    { value: "fr", label: "Français" },
    { value: "ar", label: "العربية" },
    { value: "ja", label: "日本語" },
  ],
  reportLanguage: "zh-Hans",
  promptLangs: ["zh-Hans"],
  platformOptions: [
    { value: "chatgpt", label: "ChatGPT" },
    { value: "gemini", label: "Gemini" },
    { value: "claude", label: "Claude" },
    { value: "perplexity", label: "Perplexity" },
  ],
  platforms: ["chatgpt", "gemini", "claude", "perplexity"],
  competitors: [],
  prompts: [],
  env: { llm: false, dataforseo: false },
};

function t(key) {
  return I18N[state.ui][key] || I18N.en[key] || key;
}

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.documentElement.lang = state.ui === "zh" ? "zh-Hans" : "en";
  document.getElementById("ui-zh").classList.toggle("is-on", state.ui === "zh");
  document.getElementById("ui-en").classList.toggle("is-on", state.ui === "en");
  renderRatio();
  renderSummary();
  renderEnvHint();
}

function renderEnvHint() {
  const el = document.getElementById("keys-env-hint");
  if (!el) return;
  if (state.env.llm && state.env.dataforseo) el.textContent = t("keysEnvBoth");
  else if (state.env.llm) el.textContent = t("keysEnvLlm");
  else if (state.env.dataforseo) el.textContent = t("keysEnvDfs");
  else el.textContent = "";
  el.hidden = !el.textContent;
}

function renderRatio() {
  const ratio = Number(document.getElementById("ratio").value);
  const label = document.getElementById("ratio-label");
  label.textContent = `${t("categoryTerm")} ${ratio}% / ${t("brandTerm")} ${100 - ratio}%`;
}

function renderSummary() {
  const brand = document.getElementById("brand").value.trim() || t("missing");
  const url = document.getElementById("url").value.trim() || t("missing");
  document.getElementById("summary").textContent = `${brand} · ${url} · ${state.reportLanguage} · ${state.platforms.length} platforms · ${state.prompts.length} prompts`;
}

function renderCompetitors() {
  const box = document.getElementById("competitor-list");
  box.innerHTML = "";
  state.competitors.forEach((name, index) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.innerHTML = `<span></span><button type="button" aria-label="remove">×</button>`;
    chip.querySelector("span").textContent = name;
    chip.querySelector("button").onclick = () => {
      state.competitors.splice(index, 1);
      renderCompetitors();
      renderSummary();
    };
    box.appendChild(chip);
  });
}

function renderLangs() {
  const box = document.getElementById("lang-list");
  box.innerHTML = "";
  state.languages.forEach((item) => {
    const label = document.createElement("label");
    label.className = "lang-opt" + (item.value === state.reportLanguage ? " is-on" : "");
    label.innerHTML = `<input type="radio" name="report-lang" value="${item.value}"> <span></span>`;
    label.querySelector("span").textContent = item.label;
    const input = label.querySelector("input");
    input.checked = item.value === state.reportLanguage;
    input.onchange = () => {
      state.reportLanguage = item.value;
      renderLangs();
      renderSummary();
    };
    box.appendChild(label);
  });
}

function renderPlatforms() {
  const box = document.getElementById("platform-list");
  box.innerHTML = "";
  state.platformOptions.forEach((item) => {
    const label = document.createElement("label");
    const checked = state.platforms.includes(item.value);
    label.className = "lang-opt" + (checked ? " is-on" : "");
    label.innerHTML = `<input type="checkbox"> <span></span>`;
    label.querySelector("span").textContent = item.label;
    const input = label.querySelector("input");
    input.checked = checked;
    input.onchange = () => {
      if (input.checked) state.platforms.push(item.value);
      else state.platforms = state.platforms.filter((code) => code !== item.value);
      if (!state.platforms.length) state.platforms = [item.value];
      renderPlatforms();
      renderSummary();
    };
    box.appendChild(label);
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function pill(status, labels) {
  const text = labels[status] || status;
  return `<span class="pill ${escapeHtml(status)}">${escapeHtml(text)}</span>`;
}

function platformLabel(value) {
  const found = state.platformOptions.find((item) => item.value === value);
  return found ? found.label : value;
}

function renderReport(result) {
  const view = document.getElementById("report-view");
  if (!result) {
    view.innerHTML = "";
    return;
  }
  if (result.report_html) {
    const frame = document.createElement("iframe");
    frame.className = "report-frame";
    frame.title = "GEO report";
    view.innerHTML = "";
    view.appendChild(frame);
    frame.srcdoc = result.report_html;
    frame.setAttribute("scrolling", "yes");
    return;
  }
  const s = (result.meta && result.meta.strings) || {};
  const audit = result.audit;
  const answers = result.answers;
  const searchRaw = result.search_raw;
  const platforms = result.platforms || [];
  const intro = (result.meta && result.meta.brand_intro) || "";
  const competitors = (result.meta && result.meta.competitors) || [];
  const prompts = (result.meta && result.meta.prompts) || [];
  const missing = s.missing || t("missing");
  const none = s.none || "—";
  const parts = [];
  view.setAttribute("dir", result.language === "ar" ? "rtl" : "ltr");

  parts.push(`
    <section class="report-block">
      <h3>${escapeHtml(result.brand || "")}</h3>
      <p class="report-meta">${escapeHtml(result.url || "")} · ${escapeHtml(result.domain || "")} · ${escapeHtml(result.language || "")}</p>
      <div class="chips">${platforms.map((code) => `<span class="chip"><span>${escapeHtml(platformLabel(code))}</span></span>`).join("")}</div>
      ${intro ? `<p>${escapeHtml(intro)}</p>` : ""}
      ${competitors.length ? `<p>${escapeHtml(s.competitors || "Competitors")}: ${escapeHtml(competitors.join(", "))}</p>` : ""}
    </section>
  `);

  if (audit) {
    const checks = audit.checks || [];
    const bots = audit.bot_rules || [];
    const onpage = audit.onpage || {};
    parts.push(`
      <section class="report-block">
        <h3>${escapeHtml(s.hygiene || "GEO")}</h3>
        <table class="report-table">
          <thead><tr><th>${escapeHtml(s.check || "")}</th><th>${escapeHtml(s.status || "")}</th><th>${escapeHtml(s.detail || "")}</th></tr></thead>
          <tbody>
            ${checks.map((check) => `<tr><td>${escapeHtml(check.title)}</td><td>${pill(check.status, s)}</td><td>${escapeHtml(check.detail)}</td></tr>`).join("")}
          </tbody>
        </table>
      </section>
      <section class="report-block">
        <h3>${escapeHtml(s.ai_bots || "")}</h3>
        <table class="report-table">
          <thead><tr><th>${escapeHtml(s.bot || "")}</th><th>${escapeHtml(s.status || "")}</th><th>${escapeHtml(s.detail || "")}</th></tr></thead>
          <tbody>
            ${bots.map((row) => `<tr><td>${escapeHtml(row.bot)}</td><td>${pill(row.status, s)}</td><td>${escapeHtml(row.detail)}</td></tr>`).join("")}
          </tbody>
        </table>
      </section>
      <section class="report-block">
        <h3>${escapeHtml(s.onpage || "")}</h3>
        <p>${escapeHtml(s.title || "Title")}: ${escapeHtml(onpage.title || missing)}</p>
        <p>${escapeHtml(s.description || "Description")}: ${escapeHtml(onpage.description || missing)}</p>
        <p>${escapeHtml(s.canonical || "Canonical")}: ${escapeHtml(onpage.canonical || missing)}</p>
        <p>${escapeHtml(s.h1 || "H1")}: ${escapeHtml((onpage.h1 || []).join(", ") || none)}</p>
        <p>${escapeHtml(s.jsonld || "JSON-LD")}: ${escapeHtml((audit.json_ld_types || []).join(", ") || none)}</p>
      </section>
    `);
  }

  if (answers && (answers.items || []).length) {
    parts.push(`
      <section class="report-block">
        <h3>${escapeHtml(s.raw_answers || "Q&A")}</h3>
        <div class="qa">
          ${(answers.items || []).map((item, index) => {
            const n = item.prompt_index || index + 1;
            const platform = item.platform ? ` · ${platformLabel(item.platform)}` : "";
            return `
            <article>
              <p class="prompt">${escapeHtml(`${(s.question || "Q{n}").replace("{n}", String(n))}${platform}. ${item.prompt || ""}`)}</p>
              <pre>${escapeHtml(item.answer || item.error || "")}</pre>
            </article>`;
          }).join("")}
        </div>
      </section>
    `);
  } else if (prompts.length) {
    parts.push(`
      <section class="report-block">
        <h3>${escapeHtml(s.prompts || t("promptList"))}</h3>
        <ol>${prompts.map((text) => `<li>${escapeHtml(text)}</li>`).join("")}</ol>
      </section>
    `);
  }

  if (searchRaw) {
    parts.push(`
      <section class="report-block">
        <h3>${escapeHtml(s.raw_search || "Search")}</h3>
        <pre>${escapeHtml(JSON.stringify(searchRaw, null, 2).slice(0, 4000))}</pre>
      </section>
    `);
  }

  view.innerHTML = parts.join("");
}

function renderPromptLangs() {
  const box = document.getElementById("prompt-langs");
  box.innerHTML = "";
  state.languages.forEach((item) => {
    const chip = document.createElement("label");
    chip.className = "chip";
    const checked = state.promptLangs.includes(item.value);
    chip.innerHTML = `<input type="checkbox"> <span></span>`;
    chip.querySelector("span").textContent = item.label;
    const input = chip.querySelector("input");
    input.checked = checked;
    input.onchange = () => {
      if (input.checked) state.promptLangs.push(item.value);
      else state.promptLangs = state.promptLangs.filter((code) => code !== item.value);
      if (!state.promptLangs.length) state.promptLangs = [item.value];
    };
    box.appendChild(chip);
  });
}

function renderPrompts() {
  const list = document.getElementById("prompt-list");
  const empty = document.getElementById("prompt-empty");
  list.innerHTML = "";
  empty.hidden = state.prompts.length > 0;
  state.prompts.forEach((item, index) => {
    const li = document.createElement("li");
    const kind = item.kind === "unbranded" ? t("categoryTerm") : t("brandTerm");
    li.innerHTML = `<div class="row between"><small>${kind} · ${item.language || ""}</small><button type="button" class="ghost">×</button></div><textarea></textarea>`;
    li.querySelector("textarea").value = item.text;
    li.querySelector("textarea").oninput = (event) => {
      state.prompts[index].text = event.target.value;
    };
    li.querySelector("button").onclick = () => {
      state.prompts.splice(index, 1);
      renderPrompts();
      renderSummary();
    };
    list.appendChild(li);
  });
  renderSummary();
}

function fieldValue(id, masked) {
  const value = document.getElementById(id).value.trim();
  if (!value || (masked && value === masked)) return null;
  if (value.includes("•")) return null;
  return value;
}

function keys() {
  return {
    llm_api_key: fieldValue("llm-key", state.env.llm_api_key),
    llm_base_url: document.getElementById("llm-base").value.trim() || null,
    llm_model: document.getElementById("llm-model").value.trim() || null,
    dataforseo_login: fieldValue("dfs-login", state.env.dataforseo_login),
    dataforseo_password: fieldValue("dfs-password", state.env.dataforseo_password),
  };
}

function fillEnvFields() {
  const env = state.env || {};
  const setMasked = (id, value) => {
    const el = document.getElementById(id);
    if (!el || !value || el.dataset.envFilled === "1") return;
    el.value = value;
    el.classList.add("is-masked");
    el.dataset.envFilled = "1";
    el.addEventListener("focus", () => {
      if (el.value === value) el.select();
    });
    el.addEventListener("input", () => {
      el.classList.toggle("is-masked", el.value === value || el.value.includes("•"));
      applyFetchAnswersDefault();
    });
  };
  if (env.llm_api_key) setMasked("llm-key", env.llm_api_key);
  if (env.llm_model) document.getElementById("llm-model").value = env.llm_model;
  if (env.llm_base_url) document.getElementById("llm-base").value = env.llm_base_url;
  if (env.dataforseo_login) setMasked("dfs-login", env.dataforseo_login);
  if (env.dataforseo_password) setMasked("dfs-password", env.dataforseo_password);
  applyFetchAnswersDefault();
}

function hasDfsKeys() {
  return Boolean(
    document.getElementById("dfs-login").value.trim()
    && document.getElementById("dfs-password").value.trim()
  );
}

function applyFetchAnswersDefault() {
  const box = document.getElementById("fetch-answers");
  if (!box || box.dataset.userSet === "1") return;
  const hasKey = Boolean(document.getElementById("llm-key").value.trim()) || hasDfsKeys();
  box.checked = hasKey;
}

function setBusy(button, busy) {
  button.disabled = busy;
  button.classList.toggle("is-busy", busy);
}

function setPromptLoading(busy, waitKey) {
  const overlay = document.getElementById("prompt-loading");
  const empty = document.getElementById("prompt-empty");
  const wait = overlay.querySelector("p");
  overlay.hidden = !busy;
  document.getElementById("prompt-stage").setAttribute("aria-busy", busy ? "true" : "false");
  setBusy(document.getElementById("gen-prompts"), busy);
  document.getElementById("bulk-prompt").disabled = busy;
  document.getElementById("add-prompt").disabled = busy;
  empty.hidden = busy || state.prompts.length > 0;
  if (wait) wait.textContent = t(busy && waitKey ? waitKey : "genPromptsWait");
}

const STEP_ORDER = ["queued", "audit", "answers", "search", "assemble", "done"];

function plannedReportSteps() {
  const steps = [{ id: "audit", label: t("progressAudit") }];
  const fetchAnswers = document.getElementById("fetch-answers").checked
    && (
      document.getElementById("llm-key").value.trim()
      || hasDfsKeys()
    )
    && state.prompts.some((item) => item.text && item.text.trim());
  const search = hasDfsKeys();
  if (fetchAnswers) steps.push({ id: "answers", label: t("progressAnswers") });
  if (search) steps.push({ id: "search", label: t("progressSearch") });
  steps.push({ id: "assemble", label: t("progressAssemble") });
  return steps;
}

function progressLabel(job) {
  if (!job) return "";
  if (job.status === "error") return job.error || t("progressError");
  if (job.status === "done") return t("progressDone");
  const step = job.step || job.message || "queued";
  const labels = {
    queued: t("progressQueued"),
    audit: t("progressAudit"),
    answers: t("progressAnswers"),
    search: t("progressSearch"),
    assemble: t("progressAssemble"),
    done: t("progressDone"),
  };
  let text = labels[step] || t("runBusy");
  if (step === "answers" && job.step_current && job.step_total) {
    text = `${t("progressAnswers")} ${job.step_current}/${job.step_total}`;
  }
  return text;
}

function renderJobProgress(job) {
  const panel = document.getElementById("job-progress");
  const bar = document.getElementById("progress-bar");
  const pct = document.getElementById("progress-pct");
  const label = document.getElementById("progress-label");
  const list = document.getElementById("progress-steps");
  const track = document.getElementById("progress-track");
  const status = document.getElementById("job-status");
  if (!job || job.status === "done") {
    panel.hidden = true;
    status.textContent = "";
    return;
  }
  panel.hidden = false;
  const percent = Math.max(0, Math.min(100, Number(job.progress) || 0));
  bar.style.width = `${percent}%`;
  pct.textContent = `${percent}%`;
  track.setAttribute("aria-valuenow", String(percent));
  const text = progressLabel(job);
  label.textContent = text;
  status.textContent = job.status === "error" ? text : "";
  const steps = state.jobSteps || plannedReportSteps();
  const current = job.step === "queued" ? "audit" : (job.step || "audit");
  const currentIndex = STEP_ORDER.indexOf(current);
  list.innerHTML = steps.map((step) => {
    const index = STEP_ORDER.indexOf(step.id);
    let cls = "is-pending";
    if (job.status === "error" && step.id === current) cls = "is-error";
    else if (index < currentIndex || job.status === "done") cls = "is-done";
    else if (index === currentIndex) cls = "is-current";
    let title = step.label;
    if (step.id === "answers" && current === "answers" && job.step_current && job.step_total) {
      title = `${step.label} ${job.step_current}/${job.step_total}`;
    }
    return `<li class="${cls}"><span class="step-mark" aria-hidden="true"></span><span>${escapeHtml(title)}</span></li>`;
  }).join("");
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach((el) => el.classList.toggle("is-active", el === tab));
    document.querySelectorAll(".pane").forEach((pane) => {
      pane.classList.toggle("is-active", pane.dataset.pane === tab.dataset.tab);
    });
  };
});

document.getElementById("ui-zh").onclick = () => {
  state.ui = "zh";
  applyI18n();
};
document.getElementById("ui-en").onclick = () => {
  state.ui = "en";
  applyI18n();
};
document.getElementById("ratio").oninput = renderRatio;
document.getElementById("brand").oninput = renderSummary;
document.getElementById("url").oninput = renderSummary;

document.getElementById("add-competitor").onclick = () => {
  const value = document.getElementById("competitor-draft").value.trim();
  if (!value || state.competitors.length >= 4) return;
  state.competitors.push(value);
  document.getElementById("competitor-draft").value = "";
  renderCompetitors();
  renderSummary();
};

document.getElementById("add-prompt").onclick = () => {
  state.prompts.push({
    id: `p${state.prompts.length + 1}`,
    language: state.promptLangs[0] || "zh-Hans",
    kind: "branded",
    text: "",
  });
  renderPrompts();
};

function closeBulkDialog() {
  document.getElementById("bulk-dialog").close();
}

document.getElementById("bulk-prompt").onclick = () => {
  document.getElementById("bulk-text").value = "";
  document.getElementById("bulk-dialog").showModal();
  document.getElementById("bulk-text").focus();
};
document.getElementById("bulk-cancel").onclick = closeBulkDialog;
document.getElementById("bulk-dialog").addEventListener("cancel", (event) => {
  event.preventDefault();
  closeBulkDialog();
});
document.getElementById("bulk-confirm").onclick = () => {
  const lines = document.getElementById("bulk-text").value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) {
    alert(state.ui === "zh" ? "请先粘贴提示词，一行一条" : "Paste prompts first, one per line");
    return;
  }
  const language = state.promptLangs[0] || "zh-Hans";
  lines.forEach((text, index) => {
    state.prompts.push({
      id: `p${Date.now()}-${index}`,
      language,
      kind: "branded",
      text,
    });
  });
  renderPrompts();
  closeBulkDialog();
};

document.getElementById("gen-prompts").onclick = async () => {
  const url = document.getElementById("url").value.trim();
  const brand = document.getElementById("brand").value.trim();
  if (!url || !brand) {
    alert(state.ui === "zh" ? "请先填写站点和品牌" : "Enter site URL and brand first");
    return;
  }
  const waitKey = document.getElementById("intro").value.trim() ? "genPromptsWait" : "crawlWait";
  document.querySelector('[data-tab="prompts"]').click();
  setPromptLoading(true, waitKey);
  try {
    const response = await fetch("/api/prompts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        brand,
        brand_intro: document.getElementById("intro").value,
        competitors: state.competitors,
        languages: state.promptLangs,
        total: Number(document.getElementById("total").value),
        unbranded_ratio: Number(document.getElementById("ratio").value),
        extra_notes: document.getElementById("notes").value,
        use_llm: document.getElementById("use-llm").checked,
        ...keys(),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "prompt generation failed");
    if (data.brand_intro && !document.getElementById("intro").value.trim()) {
      document.getElementById("intro").value = data.brand_intro;
    }
    state.prompts = data.prompts || [];
    renderPrompts();
  } catch (error) {
    alert(error.message);
  } finally {
    setPromptLoading(false);
  }
};

async function ensureIntro() {
  const introEl = document.getElementById("intro");
  if (introEl.value.trim()) return introEl.value.trim();
  const url = document.getElementById("url").value.trim();
  const brand = document.getElementById("brand").value.trim();
  const response = await fetch("/api/site-brief", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, brand, ...keys() }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "site crawl failed");
  if (data.intro) introEl.value = data.intro;
  return introEl.value.trim();
}

function languageLabel(value) {
  const found = state.languages.find((item) => item.value === value);
  return found ? found.label : value;
}

function fillConfirmDialog() {
  const promptCount = state.prompts.filter((item) => item.text && item.text.trim()).length;
  document.getElementById("confirm-url").textContent = document.getElementById("url").value.trim() || t("missing");
  document.getElementById("confirm-brand").textContent = document.getElementById("brand").value.trim() || t("missing");
  document.getElementById("confirm-lang").textContent = languageLabel(state.reportLanguage);
  document.getElementById("confirm-platforms").textContent = state.platforms.map(platformLabel).join(" · ") || t("missing");
  document.getElementById("confirm-prompts").textContent = t("confirmPrompts").replace("{n}", String(promptCount));
  document.getElementById("confirm-intro").textContent = document.getElementById("intro").value.trim() || t("missing");
}

function closeConfirmDialog() {
  document.getElementById("confirm-dialog").close();
}

function openConfirmDialog() {
  fillConfirmDialog();
  document.getElementById("confirm-dialog").showModal();
}

async function startReportJob() {
  const button = document.getElementById("run");
  const url = document.getElementById("url").value.trim();
  const brand = document.getElementById("brand").value.trim();
  state.jobSteps = plannedReportSteps();
  setBusy(button, true);
  document.getElementById("result").hidden = false;
  document.getElementById("report-view").innerHTML = "";
  renderJobProgress({ status: "running", step: "queued", progress: 4 });
  document.getElementById("result").scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        brand,
        brand_intro: document.getElementById("intro").value,
        competitors: state.competitors,
        language: state.reportLanguage,
        platforms: state.platforms,
        prompts: state.prompts.map((item) => item.text).filter(Boolean),
        fetch_answers: document.getElementById("fetch-answers").checked,
        ...keys(),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "job failed");
    await pollJob(data.job.id);
  } catch (error) {
    renderJobProgress({ status: "error", step: "audit", progress: 0, error: error.message });
    document.getElementById("job-status").textContent = error.message;
  } finally {
    setBusy(button, false);
  }
}

document.getElementById("run").onclick = async () => {
  const button = document.getElementById("run");
  const url = document.getElementById("url").value.trim();
  const brand = document.getElementById("brand").value.trim();
  if (!url || !brand) {
    alert(state.ui === "zh" ? "请先填写站点和品牌" : "Enter site URL and brand first");
    return;
  }
  try {
    if (!document.getElementById("intro").value.trim()) {
      setBusy(button, true);
      await ensureIntro();
    }
    setBusy(button, false);
    openConfirmDialog();
  } catch (error) {
    setBusy(button, false);
    alert(error.message);
  }
};

document.getElementById("confirm-cancel").onclick = closeConfirmDialog;
document.getElementById("confirm-dialog").addEventListener("cancel", (event) => {
  event.preventDefault();
  closeConfirmDialog();
});
document.getElementById("confirm-ok").onclick = () => {
  closeConfirmDialog();
  startReportJob();
};

async function pollJob(id) {
  for (let i = 0; i < 180; i += 1) {
    const response = await fetch(`/api/jobs/${id}`);
    const data = await response.json();
    const job = data.job;
    renderJobProgress(job);
    if (job.status === "done") {
      renderReport(job.result);
      document.getElementById("result").scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (job.status === "error") throw new Error(job.error || job.message);
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
  throw new Error("timeout");
}

fetch("/api/meta")
  .then((response) => response.json())
  .then((meta) => {
    if (meta.languages) state.languages = meta.languages;
    if (meta.platforms) state.platformOptions = meta.platforms;
    if (meta.env) state.env = meta.env;
    fillEnvFields();
    renderLangs();
    renderPromptLangs();
    renderPlatforms();
    renderEnvHint();
  })
  .catch(() => {
    renderLangs();
    renderPromptLangs();
    renderPlatforms();
  });

applyI18n();
renderCompetitors();
renderPrompts();
renderLangs();
renderPromptLangs();
renderPlatforms();

document.getElementById("fetch-answers").addEventListener("change", (event) => {
  event.currentTarget.dataset.userSet = "1";
});
document.getElementById("llm-key").addEventListener("input", applyFetchAnswersDefault);
document.getElementById("dfs-login").addEventListener("input", applyFetchAnswersDefault);
document.getElementById("dfs-password").addEventListener("input", applyFetchAnswersDefault);
