const concepts = {
  "deliberate-planning": {
    title: "Deliberate Planning",
    oneLiner: "先想清楚“要完成什么、分几步、哪里可能失败”，再开始行动。",
    why: "普通模型容易在长任务中被眼前一步带偏。任务越长，局部正确但整体失败的概率越高，因此需要一个显式的计划层持续校准方向。",
    analogy: "以前像拿到宜家家具就直接拧螺丝；现在会先看完整说明书、清点零件，再按顺序组装。",
    flow: ["理解目标", "拆解步骤", "识别风险", "调用工具", "检查结果"],
    impact: "Agent 可以承担更长、更少人工盯守的流程，但仍需为高风险动作设置确认边界。"
  },
  "tool-recovery": {
    title: "Tool Recovery",
    oneLiner: "工具报错不是任务终点，而是模型下一步决策的新信息。",
    why: "真实系统里接口超时、参数错误和权限不足很常见。只会调用工具，却不会处理失败，Agent 就无法稳定工作。",
    analogy: "像一个熟练外卖员发现正门关闭后，会看提示、联系客户并改走侧门，而不是把订单直接取消。",
    flow: ["收到错误", "判断原因", "调整方案", "再次调用", "确认完成"],
    impact: "提升端到端任务完成率，并减少为每一种错误单独编写流程分支的工作量。"
  },
  "working-memory": {
    title: "Structured Working Memory",
    oneLiner: "把长任务中的目标、约束和进度整理成一张持续更新的工作便签。",
    why: "上下文很长不等于模型能始终抓住重点。关键信息混在大量历史消息中，容易被忽视或错误覆盖。",
    analogy: "像主厨在繁忙晚餐时段使用出餐看板：谁点了什么、做到哪一步、有哪些忌口，一眼可见。",
    flow: ["提取目标", "记录约束", "更新状态", "检索重点", "完成核对"],
    impact: "更适合跨多轮、多工具的工作流，也让任务状态更容易被产品界面展示和人工接管。"
  },
  "adaptive-compute": {
    title: "Adaptive Compute",
    oneLiner: "把更多思考时间留给真正困难的问题，简单问题则快速回答。",
    why: "所有请求都使用相同推理预算会造成浪费：简单任务变慢，复杂任务又可能思考不足。",
    analogy: "像医院分诊：普通感冒快速处理，复杂病例才进入专家会诊，不让所有患者都走同一套流程。",
    flow: ["判断难度", "分配预算", "执行推理", "检查信心", "必要时加码"],
    impact: "产品可以在响应速度、成本和质量之间取得更细粒度的平衡。"
  }
};

const reportSections = {
  1: {
    title: "Abstract",
    html: `<p>We introduce Aster 1, a model designed for reliable completion of long-horizon, tool-mediated tasks. The system combines deliberate task planning, structured working memory, and recovery-aware tool use.</p><p>Across a suite of simulated enterprise workflows, <mark>Aster 1 improves end-to-end task completion while keeping human intervention bounded and observable</mark>. We report both capability gains and the failure modes that remain unresolved.</p><div class="formula">Success = Planning × Execution × Recovery</div><p>This report describes the model architecture, post-training process, evaluation methodology, and deployment constraints. All figures in this demo are illustrative.</p>`,
    question: "这个模型最核心的变化是什么？",
    answer: "Aster 1 的重点不是增加知识，而是提高长任务中的规划与恢复能力。",
    tip: "先看任务完成率，再看单步准确率；这是理解本报告的关键。"
  },
  2: {
    title: "Executive Summary",
    html: `<h2>From response quality to task completion</h2><p>Most current evaluations isolate a single turn. Real work does not. A useful agent must preserve intent across steps, choose tools, observe outcomes, and recover from errors.</p><p><mark>We therefore optimize for completed outcomes rather than plausible intermediate responses.</mark> This change affects both training data and evaluation design.</p><h2>What changed</h2><p>Aster 1 introduces a planning stage before external actions, a compact state representation for active constraints, and a recovery policy trained on realistic tool failures.</p>`,
    question: "为什么传统准确率不够用了？",
    answer: "单步回答正确，不代表十步任务能完成。长流程中的小错误会累积。",
    tip: "这一节适合所有角色阅读，能在 2 分钟内建立全局判断。"
  },
  3: {
    title: "Model Overview",
    html: `<h2>System components</h2><p>The model operates within an execution loop that separates intent, plan, action, and observation. The separation is logical rather than a claim of independent neural modules.</p><p>At each step, the system updates a structured task state containing the objective, active constraints, completed work, unresolved errors, and the next candidate action.</p><div class="formula">stateₜ₊₁ = update(stateₜ, actionₜ, observationₜ)</div><p>This representation is intentionally compact. It supplements—rather than replaces—the full conversation context.</p>`,
    question: "Structured Memory 是新的数据库吗？",
    answer: "不是。它是模型在任务执行过程中维护的一份紧凑状态表示。",
    tip: "不要把逻辑组件误解成已公开的独立神经网络模块。"
  },
  4: {
    title: "Agent Architecture",
    html: `<h2>Plan before action</h2><p>Before invoking an external tool, the model produces an internal task decomposition and checks whether the proposed action is necessary, reversible, and permitted.</p><p><mark>The plan is treated as a working hypothesis, not a rigid script.</mark> New observations can invalidate assumptions and trigger replanning.</p><h2>Recovery-aware execution</h2><p>Tool errors are categorized into transient, correctable, permission-related, and terminal failures. The policy selects among retrying, changing parameters, choosing another tool, requesting clarification, or stopping safely.</p>`,
    question: "规划会不会让 Agent 变得僵化？",
    answer: "不会。计划是可修正的假设；新信息出现时，模型会重新规划。",
    tip: "重点看错误分类和停止条件，它们决定产品是否可控。"
  },
  5: {
    title: "Evaluation",
    html: `<h2>End-to-end workflow suite</h2><p>We evaluate on multi-step tasks spanning research, data transformation, scheduling, and support operations. Each task includes hidden constraints and injected tool failures.</p><p>Success requires a valid final state, not merely a well-formed answer. We separately report completion, intervention, unsafe-action, and latency metrics.</p><h2>Interpreting the results</h2><p><mark>No single benchmark captures production reliability.</mark> Results should be read as directional evidence under the stated environment and tool set.</p>`,
    question: "应该看哪个指标？",
    answer: "优先看端到端完成率和人工介入率，再结合延迟与风险指标。",
    tip: "Benchmark 是验证，不是事实全貌；注意环境和工具集是否接近你的场景。"
  },
  6: {
    title: "Limitations",
    html: `<h2>Known failure modes</h2><p>Aster 1 can still pursue an incorrect high-level assumption for multiple steps, especially when feedback from tools appears internally consistent.</p><p>The system may also over-recover: repeated retries can increase cost without improving the probability of success. Product-level budgets and stop conditions remain necessary.</p><h2>Deployment boundaries</h2><p><mark>Higher autonomy should not be interpreted as permission for unbounded action.</mark> Irreversible or high-impact operations require explicit confirmation and external policy enforcement.</p>`,
    question: "更强的 Agent 可以完全放手吗？",
    answer: "不可以。高影响、不可逆操作仍需产品层权限和人工确认。",
    tip: "如果你准备接入生产系统，这一节比排行榜更重要。"
  }
};

const views = document.querySelectorAll(".view");
const navItems = document.querySelectorAll(".nav-item");
const drawer = document.getElementById("conceptDrawer");
const backdrop = document.getElementById("drawerBackdrop");
const searchOverlay = document.getElementById("searchOverlay");

function showView(name) {
  views.forEach((view) => view.classList.toggle("active", view.id === `${name}-view`));
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  const breadcrumbLabels = { brief: "模型发布", report: "原始证据", sources: "证据库", monitor: "官方来源" };
  document.querySelector(".breadcrumb span").textContent = breadcrumbLabels[name] || "FrontierLens";
  window.scrollTo({ top: 0, behavior: "smooth" });
  closeDrawer();
  if (name === "monitor") loadMonitor();
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.view));
});

document.querySelectorAll("[data-jump]").forEach((button) => {
  button.addEventListener("click", () => document.getElementById(button.dataset.jump)?.scrollIntoView({ behavior: "smooth" }));
});

function openConcept(key) {
  const concept = concepts[key];
  if (!concept) return;
  document.getElementById("conceptTitle").textContent = concept.title;
  document.getElementById("conceptOneLiner").textContent = concept.oneLiner;
  document.getElementById("conceptWhy").textContent = concept.why;
  document.getElementById("conceptAnalogy").textContent = concept.analogy;
  document.getElementById("conceptImpact").textContent = concept.impact;
  document.getElementById("conceptFlow").innerHTML = concept.flow.map((step, index) => `${index ? "<i>→</i>" : ""}<span>${step}</span>`).join("");
  drawer.classList.add("open");
  backdrop.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  drawer.classList.remove("open");
  backdrop.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
}

document.querySelectorAll(".change-card").forEach((card) => {
  card.addEventListener("click", () => openConcept(card.dataset.concept));
  card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") openConcept(card.dataset.concept); });
});
document.getElementById("drawerClose").addEventListener("click", closeDrawer);
backdrop.addEventListener("click", closeDrawer);

function loadReportSection(section) {
  const data = reportSections[section];
  if (!data) return;
  document.getElementById("paperTitle").textContent = data.title;
  document.getElementById("paperContent").innerHTML = data.html;
  document.getElementById("noteQuestion").textContent = data.question;
  document.getElementById("noteAnswer").textContent = data.answer;
  document.getElementById("noteTip").textContent = data.tip;
  document.querySelectorAll(".report-toc button").forEach((button) => button.classList.toggle("active", button.dataset.section === String(section)));
}

document.querySelectorAll(".report-toc button").forEach((button) => button.addEventListener("click", () => loadReportSection(button.dataset.section)));
document.querySelectorAll("[data-report-section]").forEach((button) => button.addEventListener("click", () => { showView("report"); loadReportSection(button.dataset.reportSection); }));
loadReportSection(1);

document.getElementById("toggleHighlights").addEventListener("click", (event) => {
  const notes = document.querySelector(".atlas-notes");
  notes.style.display = notes.style.display === "none" ? "grid" : "none";
  event.currentTarget.textContent = notes.style.display === "none" ? "显示 FrontierLens 解读" : "隐藏 FrontierLens 解读";
});

function openSearch() {
  searchOverlay.classList.add("open");
  searchOverlay.setAttribute("aria-hidden", "false");
  setTimeout(() => document.getElementById("searchInput").focus(), 100);
}
function closeSearch() {
  searchOverlay.classList.remove("open");
  searchOverlay.setAttribute("aria-hidden", "true");
}
document.getElementById("searchButton").addEventListener("click", openSearch);
searchOverlay.addEventListener("click", (event) => { if (event.target === searchOverlay) closeSearch(); });
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); openSearch(); }
  if (event.key === "Escape") { closeSearch(); closeDrawer(); }
});
document.querySelectorAll("[data-search]").forEach((button) => button.addEventListener("click", () => { document.getElementById("searchInput").value = button.dataset.search; }));
document.getElementById("searchResult").addEventListener("click", () => { closeSearch(); showView("brief"); });

const mobileMenu = document.querySelector(".mobile-menu");
mobileMenu.addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("open"));
navItems.forEach((item) => item.addEventListener("click", () => document.querySelector(".sidebar").classList.remove("open")));

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}

function formatTime(value) {
  if (!value) return "尚未扫描";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
}

function statusLabel(status) {
  return ({ ok: "正常", completed: "完成", completed_with_errors: "部分异常", not_modified: "无变化", error: "异常", never: "待扫描", parsed: "已解析", pending: "待处理", saved: "已保存" })[status] || status || "待扫描";
}

async function loadMonitor() {
  const notice = document.getElementById("monitorNotice");
  if (!notice) return;
  try {
    const response = await fetch("/api/monitor/summary", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const counts = data.counts || {};
    document.getElementById("providerCount").textContent = data.sources?.length ?? 0;
    document.getElementById("reportCount").textContent = counts.reports ?? 0;
    document.getElementById("parsedCount").textContent = counts.parsed ?? 0;
    document.getElementById("lastScanTime").textContent = formatTime(data.latest_run?.finished_at || data.latest_run?.started_at);
    document.getElementById("lastScanStatus").textContent = data.latest_run ? statusLabel(data.latest_run.status) : "等待首次运行";
    notice.className = "monitor-notice";
    notice.querySelector("p").textContent = data.latest_run ? `自动监控已启动 · 最近一次扫描${statusLabel(data.latest_run.status)}` : "数据服务已连接 · 等待首次自动扫描";
    const sourceTable = document.getElementById("sourceMonitorTable");
    sourceTable.innerHTML = data.sources?.length ? data.sources.map((source) => {
      const abbreviation = source.provider.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
      const stateClass = source.last_status === "error" ? "error" : source.last_status === "never" ? "never" : "";
      return `<div class="source-row"><span class="provider-badge">${escapeHtml(abbreviation)}</span><div><strong>${escapeHtml(source.provider)}</strong><small>${escapeHtml(source.name)} · ${escapeHtml(formatTime(source.last_checked_at))}</small></div><span class="source-status ${stateClass}">${escapeHtml(statusLabel(source.last_status))}</span></div>`;
    }).join("") : '<div class="empty-monitor">尚未配置来源</div>';
    const reportTable = document.getElementById("recentReportTable");
    reportTable.innerHTML = data.recent_reports?.length ? data.recent_reports.map((report) => `<div class="report-row"><div><strong>${escapeHtml(report.title)}</strong><small>${escapeHtml(report.provider)} · ${escapeHtml(report.page_count ? `${report.page_count} 页` : statusLabel(report.parse_status))}</small></div><span>${escapeHtml(report.report_type.replaceAll("_", " "))}</span></div>`).join("") : '<div class="empty-monitor">首次扫描后，新报告会出现在这里</div>';
  } catch (error) {
    notice.className = "monitor-notice error";
    notice.querySelector("p").textContent = "数据服务未启动。请使用 run.py serve 启动 FrontierLens 后端。";
    ["providerCount", "reportCount", "parsedCount", "lastScanTime"].forEach((id) => { document.getElementById(id).textContent = "—"; });
  }
}

document.getElementById("scanNowButton")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const notice = document.getElementById("monitorNotice");
  button.disabled = true;
  button.textContent = "扫描中…";
  notice.className = "monitor-notice scanning";
  notice.querySelector("p").textContent = "正在检查官方来源并保存新报告，请稍候…";
  try {
    const response = await fetch("/api/scan", { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    notice.querySelector("p").textContent = `扫描完成：发现 ${result.candidate_count} 个候选，新增 ${result.new_report_count} 份报告，解析 ${result.parsed_count} 份 PDF。`;
    await loadMonitor();
  } catch (error) {
    notice.className = "monitor-notice error";
    notice.querySelector("p").textContent = "扫描失败，请检查网络或后台日志。";
  } finally {
    button.disabled = false;
    button.innerHTML = '立即扫描 <span>↻</span>';
  }
});
