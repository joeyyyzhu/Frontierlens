const concepts = {
  "hybrid-reasoning": {
    title: "Unified Thinking Modes",
    oneLiner: "同一个模型既能先深入思考再回答，也能跳过长推理直接快速响应。",
    why: "复杂数学、代码和规划任务受益于更多推理，但日常问答不值得付出同样的时间与成本。Qwen3 把两种模式放进同一个框架。",
    analogy: "像一辆车同时有普通模式和运动模式：通勤时轻快省油，需要超车时再释放更多性能。",
    flow: ["收到任务", "选择模式", "分配推理", "生成答案", "按需切换"],
    impact: "产品可以用一套模型同时覆盖即时问答和复杂推理，减少用户手动切换模型的负担。",
    prerequisites: ["Transformer", "推理模型", "推理时计算"],
    relations: ["Thinking Budget", "RL", "Agent"],
    evolution: ["单一 Chat 模式", "独立推理模型", "统一双模式"],
    compareQuestion: "为什么不继续使用两个独立模型？",
    comparison: "两个模型需要额外路由，也会让用户承担选择成本。统一模式让切换发生在同一个模型和对话中。"
  },
  "moe-architecture": {
    title: "Mixture-of-Experts",
    oneLiner: "模型拥有许多“专家”，但每次只激活最适合当前内容的一部分。",
    why: "如果每次生成都调用全部参数，大模型的计算成本会很高。MoE 让总参数规模继续增长，同时控制每个 token 实际使用的计算量。",
    analogy: "像综合医院有很多科室，但一位患者只会被分诊到最相关的几位医生，而不是让全院一起会诊。",
    flow: ["输入 Token", "路由判断", "选择专家", "专家处理", "合并输出"],
    impact: "团队可以在更大容量与可接受的推理成本之间寻找平衡，但部署复杂度也会提高。",
    prerequisites: ["Transformer", "FFN", "Sparse Activation"],
    relations: ["Router", "Expert", "Load Balancing"],
    evolution: ["Dense Transformer", "Sparse MoE", "Fine-grained Experts"],
    compareQuestion: "为什么不用 Dense Transformer？",
    comparison: "Dense 每次都会激活全部参数，训练和推理更简单稳定；MoE 只激活少数专家，在扩大总容量时能控制计算成本，但会增加路由与负载均衡难度。"
  },
  "thinking-budget": {
    title: "Thinking Budget",
    oneLiner: "允许用户决定模型在回答前最多投入多少推理计算。",
    why: "推理越久通常越可能解决难题，但也意味着更高延迟与成本。固定预算无法适配价值差异很大的任务。",
    analogy: "像给考试题设置答题时间：选择题快速作答，压轴题则预留更多草稿和检查时间。",
    flow: ["判断价值", "设置预算", "执行推理", "检查结果", "控制成本"],
    impact: "推理深度从模型内部行为变成可设计的产品参数，可按场景设置质量、延迟与费用。",
    prerequisites: ["Chain of Thought", "Token", "Inference Cost"],
    relations: ["Thinking Mode", "Latency", "Reasoning"],
    evolution: ["固定推理", "测试时扩展", "可控预算"],
    compareQuestion: "为什么不让模型一直深度思考？",
    comparison: "简单问题继续长时间推理会增加等待和成本，却不一定提高答案质量。预算控制让计算投入与任务价值匹配。"
  },
  "multilingual-scale": {
    title: "Multilingual Pretraining",
    oneLiner: "用约 36 万亿 token 的数据训练，并把覆盖范围扩展到 119 种语言和方言。",
    why: "跨语言产品不能只依赖英文能力迁移。更广泛的原生语料覆盖能为不同语言的理解和生成建立更直接的基础。",
    analogy: "像一位翻译不只读过英语教材，而是在 119 个语言环境里长期生活和阅读。",
    flow: ["收集语料", "质量过滤", "多语混合", "预训练", "能力评估"],
    impact: "全球化产品有了更广的模型基础，但具体语言效果仍应通过目标市场的真实任务验证。",
    prerequisites: ["Pre-training", "Tokenizer", "Data Mixture"],
    relations: ["Synthetic Data", "Cross-lingual", "Evaluation"],
    evolution: ["29 种语言", "扩大多语语料", "119 种语言"],
    compareQuestion: "语言数量增加就等于效果更好吗？",
    comparison: "不一定。覆盖数量只说明训练范围扩大；具体语言的理解、文化语境和专业任务仍需单独评测。"
  }
};

const modelVariants = {
  "0.6b": { name: "Qwen3 0.6B", architecture: "Dense · 全参数激活", badge: "超轻量", total: "0.6B", active: "0.6B", deployment: "低", summary: "家族中最轻量的变体，适合先验证交互和工作流，而不是承担最复杂的推理任务。", decision: "优先验证产品闭环，再决定是否升级模型。", tradeoff: "成本和响应速度更友好，但复杂推理、长链路 Agent 和高要求生成质量会更受限制。", uses: ["端侧实验", "意图分类", "轻量助手"] },
  "1.7b": { name: "Qwen3 1.7B", architecture: "Dense · 全参数激活", badge: "轻量", total: "1.7B", active: "1.7B", deployment: "低", summary: "在资源占用与基础语言能力之间取得更实用的平衡，适合低成本、高调用量场景。", decision: "适合把 AI 能力嵌入高频但容错空间较大的功能。", tradeoff: "比 0.6B 更稳健，但不应只凭参数量假设它能覆盖复杂业务判断。", uses: ["信息抽取", "内容改写", "批量处理"] },
  "4b": { name: "Qwen3 4B", architecture: "Dense · 全参数激活", badge: "轻中量", total: "4B", active: "4B", deployment: "中低", summary: "面向本地部署与质量要求同时存在的场景，是家族中较容易进入产品试点的规格。", decision: "可作为私有化与成本敏感产品的首个质量基线。", tradeoff: "部署仍相对可控，但复杂推理质量需要结合真实任务评测。", uses: ["企业知识库", "本地助手", "结构化生成"] },
  "8b": { name: "Qwen3 8B", architecture: "Dense · 全参数激活", badge: "通用型", total: "8B", active: "8B", deployment: "中", summary: "兼顾部署可行性与通用能力的中等规格，适合用于建立产品质量、延迟和成本的基准。", decision: "多数团队可以从它开始做真实业务评测。", tradeoff: "能力更完整，但高并发成本和显存需求需要进入容量规划。", uses: ["通用助手", "RAG", "轻量 Agent"] },
  "14b": { name: "Qwen3 14B", architecture: "Dense · 全参数激活", badge: "增强型", total: "14B", active: "14B", deployment: "中高", summary: "在语言质量、推理能力与部署成本之间进一步偏向能力，适合对回答稳定性更敏感的业务。", decision: "当 8B 已证明业务价值但质量仍不足时，再评估升级。", tradeoff: "更高质量通常伴随更高延迟与推理成本，需要用业务收益验证升级是否值得。", uses: ["专业问答", "内容生产", "复杂 RAG"] },
  "32b": { name: "Qwen3 32B", architecture: "Dense · 全参数激活", badge: "高能力", total: "32B", active: "32B", deployment: "高", summary: "Dense 路线中的高能力规格，更适合质量优先且具备较完整推理基础设施的团队。", decision: "用于对质量敏感的核心路径，而非默认覆盖所有请求。", tradeoff: "全参数参与计算，容量、延迟与成本压力都会明显高于中小规格。", uses: ["复杂推理", "代码任务", "高质量生成"] },
  "30b-a3b": { name: "Qwen3 30B-A3B", architecture: "MoE · 稀疏激活", badge: "效率型 MoE", total: "30B", active: "3B", deployment: "中高", summary: "拥有约 30B 总参数，但每次仅激活约 3B，用更大的知识容量换取可控的单次计算量。", decision: "适合希望提升能力、又不能接受 Dense 30B 计算成本的团队。", tradeoff: "单次激活参数较少不等于部署简单；专家路由、显存和服务框架仍会增加工程复杂度。", uses: ["高并发助手", "Agent", "成本敏感推理"], concept: "moe-architecture" },
  "235b-a22b": { name: "Qwen3 235B-A22B", architecture: "MoE · 稀疏激活", badge: "旗舰 MoE", total: "235B", active: "22B", deployment: "很高", summary: "家族旗舰变体，以更大的总容量和约 22B 激活参数面向复杂推理与高质量任务。", decision: "只有当旗舰能力能直接改善核心业务指标时才值得进入选型。", tradeoff: "即使采用稀疏激活，总权重规模、服务复杂度和基础设施要求仍然很高。", uses: ["复杂 Agent", "高级推理", "高价值任务"], concept: "moe-architecture" }
};

let reportSections = [];
let featuredReport = null;
let personalizedFeedPayload = null;
let activeFeedFilter = "all";
let activeFeedModel = "all";
let currentReleaseItem = null;
let currentKnowledgeGraph = null;
let releaseWorkspaceVersion = 0;

const modelLogoPaths = {
  qwen: "assets/logos/alibaba-cloud.svg",
  gpt: "assets/logos/openai.svg",
  claude: "assets/logos/anthropic.svg",
  gemini: "assets/logos/gemini.svg",
  deepseek: "assets/logos/deepseek.svg",
  kimi: "assets/logos/moonshot.svg",
};

const views = document.querySelectorAll(".view");
const navItems = document.querySelectorAll(".nav-item");
const drawer = document.getElementById("conceptDrawer");
const backdrop = document.getElementById("drawerBackdrop");

function showView(name) {
  if (name === "report" && document.getElementById("releaseReportTab")?.disabled) name = "sources";
  views.forEach((view) => view.classList.toggle("active", view.id === `${name}-view`));
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  const breadcrumbLabels = { feed: "我的追踪", brief: "发布速览", report: "技术原文", sources: "证据与来源", monitor: "官方来源" };
  document.querySelector(".breadcrumb span").textContent = breadcrumbLabels[name] || "FrontierLens";
  document.querySelector(".breadcrumb strong").textContent = name === "feed" ? "为你筛选" : name === "monitor" ? "采集状态" : (currentReleaseItem?.title || "Qwen3");
  const releaseContextBar = document.getElementById("releaseContextBar");
  const inRelease = ["brief", "report", "sources"].includes(name);
  releaseContextBar.hidden = !inRelease;
  releaseContextBar.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  window.scrollTo({ top: 0, behavior: "smooth" });
  closeDrawer();
  closeSelectionAssistant();
  if (name === "monitor") loadMonitor();
  if (name === "feed") loadPersonalizedFeed();
  if (name === "report" && currentReleaseItem?.readableReportId && featuredReport?.id !== currentReleaseItem.readableReportId) {
    loadFeaturedReport(currentReleaseItem.readableReportId);
  }
}

function currentReleaseLogo(item) {
  const path = modelLogoPaths[item.modelKey];
  return path ? `<img src="${path}" alt="" />` : escapeHtml(item.mark || item.modelName.slice(0, 1));
}

function renderGenericRelease(item) {
  const hasReport = Boolean(item.hasTechReport);
  const evidence = item.documents.map((document, index) => {
    const meta = `${document.sourceLabels.join(" · ")}${document.isPrimary ? " · 主证据" : ""}${document.pageCount ? ` · ${document.pageCount} 页` : ""}`;
    const body = `<span>${String(index + 1).padStart(2, "0")}</span><div><strong>${escapeHtml(document.title)}</strong><small>${escapeHtml(meta)}</small></div>`;
    if (document.reportType === "technical_report" && document.parseStatus === "parsed") {
      return `<button class="generic-evidence-link primary" data-open-release="${item.releaseId}" data-release-view="report">${body}<b>AI 辅助阅读 →</b></button>`;
    }
    return `<a class="generic-evidence-link" href="${escapeHtml(document.url)}" target="_blank" rel="noopener">${body}<b>打开原文 ↗</b></a>`;
  }).join("");
  const briefHighlights = (item.highlights || []).map((highlight, index) => `<article><span>${String(index + 1).padStart(2, "0")}</span><div><small>${escapeHtml(highlight.label)}</small><p>${escapeHtml(highlight.text)}</p>${highlight.firstPage ? `<em>官方原文第 ${highlight.firstPage}${highlight.lastPage && highlight.lastPage !== highlight.firstPage ? `–${highlight.lastPage}` : ""} 页</em>` : ""}</div></article>`).join("");
  const productImplications = (item.productImplications || []).map((impact) => `<li><b>${escapeHtml(impact.label)}</b><span>${escapeHtml(impact.text)}</span></li>`).join("");
  const understanding = briefHighlights ? `<section class="generic-understanding-section"><div><span class="eyebrow">WHAT CHANGED</span><h2>从官方证据中提取的变化信号</h2><p>${escapeHtml(item.highlightBasis || "基于当前官方证据")}</p></div><div class="generic-brief-highlights">${briefHighlights}</div>${productImplications ? `<aside><span>FOR AI PRODUCT MANAGERS</span><h3>接下来应该验证什么</h3><ul>${productImplications}</ul></aside>` : ""}</section>` : "";
  const primaryAction = item.canReadTechReport
    ? `<button class="primary-button" data-open-release="${item.releaseId}" data-release-view="report">AI 辅助阅读 Tech Report <span>→</span></button>`
    : `<button class="secondary-button" data-open-release="${item.releaseId}" data-release-view="sources">查看全部官方证据</button>`;
  const evidenceAction = item.canReadTechReport
    ? `<button class="secondary-button" data-open-release="${item.releaseId}" data-release-view="sources">核对证据来源</button>`
    : "";
  document.getElementById("genericReleaseBrief").innerHTML = `<section class="generic-release-hero">
    <div><span class="eyebrow">RELEASE WORKSPACE · ${escapeHtml(item.provider)}</span><h1>${escapeHtml(item.title)}</h1><p>${escapeHtml(item.briefSummary || "FrontierLens 已把这次发布识别为一个独立事件，并将来自官方渠道的资料归档到同一工作区。")}</p><div class="generic-release-meta"><span><b>${item.documentCount}</b> 份官方证据</span><span><b>${escapeHtml(item.sourceLabels.join(" · "))}</b></span></div><div class="generic-release-actions">${primaryAction}${evidenceAction}</div></div>
    <aside><span>${hasReport ? "TECH REPORT AVAILABLE" : "REPORT WATCH ACTIVE"}</span><h2>${hasReport ? "技术报告已经进入证据层。" : "发布已确认，完整 Tech Report 尚未发现。"}</h2><p>${hasReport ? "先看发布变化，再回到主报告核对技术事实。" : "现有官方资料会先并存展示；报告发布后会自动成为主证据，不覆盖当前记录。"}</p></aside>
  </section>${understanding}<section class="generic-evidence-section"><div><span class="eyebrow">CURRENT EVIDENCE</span><h2>这次发布现在有哪些依据</h2><p>新资料会追加到这里，不会把发布事件复制成多个页面。</p></div><div class="generic-evidence-list">${evidence}</div></section>`;
  document.getElementById("genericReleaseSources").innerHTML = `<div class="sources-header"><span class="eyebrow">${escapeHtml(item.title.toUpperCase())} · EVIDENCE WORKSPACE</span><h1>一个发布，多份证据</h1><p>Tech Report 是主证据；Blog、Benchmark、GitHub 与 Safety Report 按问题补充。尚未出现的来源保持监控，不用社区材料冒充。</p></div><div class="generic-source-stack">${evidence}</div>`;
}

function knowledgeStateLabel(state) {
  return ({ supported: "官方证据", inferred: "综合推断", background: "背景知识", pending: "等待证据", unavailable: "原文不可用" })[state] || "理解层";
}

function renderKnowledgeMap(payload) {
  const container = document.getElementById("releaseKnowledgeMap");
  currentKnowledgeGraph = payload;
  if (!payload || payload.status === "pending" || !payload.primaryConcepts?.length) {
    container.innerHTML = `<div class="knowledge-map-empty"><div><span class="eyebrow">TECHNICAL INTUITION MAP</span><h2>认知地图等待更多官方证据</h2><p>FrontierLens 不会仅凭模型名称补写技术关系。Tech Report 完成解析后，概念、关系和页码证据会自动出现在这里。</p></div><span>Evidence pending</span></div>`;
    return;
  }
  const nodes = payload.primaryConcepts.map((concept, index) => {
    const evidence = concept.evidence?.[0];
    const citation = evidence ? `${escapeHtml(evidence.title)}${evidence.firstPage ? ` · P${evidence.firstPage}${evidence.lastPage && evidence.lastPage !== evidence.firstPage ? `–${evidence.lastPage}` : ""}` : ""}` : knowledgeStateLabel(concept.evidenceState);
    return `<button class="knowledge-node role-${escapeHtml(concept.role)}" data-knowledge-concept="${escapeHtml(concept.id)}" style="--node-index:${index}">
      <span class="knowledge-node-index">${String(index + 1).padStart(2, "0")}</span>
      <span class="knowledge-node-copy"><small>${escapeHtml(knowledgeStateLabel(concept.evidenceState))}</small><strong>${escapeHtml(concept.name)}</strong><p>${escapeHtml(concept.contextSummary || concept.oneLiner)}</p><em>${citation}</em></span>
      <i>↗</i>
    </button>`;
  }).join("");
  container.innerHTML = `<div class="knowledge-map-heading"><div><span class="eyebrow">TECHNICAL INTUITION MAP</span><h2>从变化，走向可复用的技术直觉</h2><p>不是展示一张复杂的图，而是把这次发布所依赖的概念、关系与官方证据连接起来。</p></div><aside><strong>${payload.primaryConcepts.length}</strong><span>个核心概念</span><small>${escapeHtml(payload.principle)}</small></aside></div>
    <div class="knowledge-map-canvas"><div class="knowledge-release-node"><span>MODEL RELEASE</span><strong>${escapeHtml(payload.releaseName)}</strong><small>What changed?</small></div><div class="knowledge-connector" aria-hidden="true"><i></i><i></i><i></i></div><div class="knowledge-node-grid">${nodes}</div></div>
    <div class="knowledge-map-legend"><span><i class="supported"></i>官方原文支持</span><span><i class="inferred"></i>多源综合推断</span><span><i class="background"></i>通用背景知识</span><small>点击概念查看前置知识、技术关系与产品影响</small></div>`;
}

async function loadReleaseKnowledge(item, workspaceVersion) {
  const container = document.getElementById("releaseKnowledgeMap");
  container.innerHTML = `<div class="knowledge-loading"><span class="eyebrow">TECHNICAL INTUITION MAP</span><p>正在把 ${escapeHtml(item.title)} 连接到官方证据与关键概念…</p></div>`;
  try {
    const response = await fetch(`/api/releases/${encodeURIComponent(item.releaseId)}/knowledge`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (workspaceVersion !== releaseWorkspaceVersion || currentReleaseItem?.releaseId !== item.releaseId) return;
    renderKnowledgeMap(payload);
  } catch {
    if (workspaceVersion !== releaseWorkspaceVersion || currentReleaseItem?.releaseId !== item.releaseId) return;
    container.innerHTML = `<div class="knowledge-map-empty error"><div><span class="eyebrow">TECHNICAL INTUITION MAP</span><h2>认知地图暂时无法载入</h2><p>发布与原始证据仍然可用。请稍后刷新，FrontierLens 不会用无证据内容填补空白。</p></div><button data-open-release="${item.releaseId}" data-release-view="sources">先核对证据</button></div>`;
  }
}

function openReleaseWorkspace(item, targetView = "brief") {
  const workspaceVersion = ++releaseWorkspaceVersion;
  currentReleaseItem = item;
  const isQwen3 = item.releaseSlug === "qwen3";
  document.getElementById("releaseContextLogo").innerHTML = currentReleaseLogo(item);
  document.getElementById("releaseContextFamily").textContent = `${item.modelName.toUpperCase()} · RELEASE`;
  document.getElementById("releaseContextTitle").textContent = item.title;
  document.getElementById("releaseEvidenceCount").textContent = item.documentCount;
  document.getElementById("releaseReportCount").textContent = item.techReportCount || 0;
  document.getElementById("releaseReportTab").disabled = !item.canReadTechReport;
  document.querySelectorAll(".qwen-release-content").forEach((element) => { element.hidden = !isQwen3; });
  document.getElementById("genericReleaseBrief").hidden = isQwen3;
  document.getElementById("genericReleaseSources").hidden = isQwen3;
  if (!isQwen3) renderGenericRelease(item);
  loadReleaseKnowledge(item, workspaceVersion);
  if (personalizedFeedPayload) renderSidebarWorkspaces(personalizedFeedPayload.items, personalizedFeedPayload.watching, personalizedFeedPayload.preferences);
  showView(targetView === "report" && !item.canReadTechReport ? "sources" : targetView);
}

function releaseById(id) {
  return personalizedFeedPayload?.items.find((item) => String(item.releaseId) === String(id));
}

function renderSidebarWorkspaces(items, watching = [], preferences = {}) {
  const list = document.getElementById("sidebarModelWorkspaces");
  if (!list) return;
  const families = new Map();
  const preferredOrder = preferences.models || [];

  items.forEach((item) => {
    if (!families.has(item.modelKey)) families.set(item.modelKey, { modelKey: item.modelKey, modelName: item.modelName, provider: item.provider, releases: [] });
    const family = families.get(item.modelKey);
    if (!family.releases.some((release) => release.releaseId === item.releaseId)) family.releases.push(item);
  });
  watching.forEach((item) => {
    if (!families.has(item.modelKey)) families.set(item.modelKey, { ...item, releases: [] });
  });

  const orderedFamilies = [...families.values()].sort((a, b) => {
    const aIndex = preferredOrder.indexOf(a.modelKey);
    const bIndex = preferredOrder.indexOf(b.modelKey);
    if (aIndex !== bIndex) return (aIndex < 0 ? 999 : aIndex) - (bIndex < 0 ? 999 : bIndex);
    return a.modelName.localeCompare(b.modelName);
  });

  list.innerHTML = orderedFamilies.length ? orderedFamilies.map((family, familyIndex) => {
    const activeFamily = currentReleaseItem?.modelKey === family.modelKey;
    const logoItem = family.releases[0] || family;
    const releaseButton = (item, latest = false) => {
      const active = currentReleaseItem?.releaseId === item.releaseId;
      const track = item.releaseTrack ? `<em>${escapeHtml(item.releaseTrack)}</em>` : "";
      const evidenceBadge = item.catalogStatus === "evidence_only" ? '<b>报告</b>' : (latest ? '<b>最新</b>' : "");
      return `<button class="workspace-release-item${active ? " active" : ""}" data-open-release="${item.releaseId}" aria-current="${active ? "page" : "false"}"><span class="workspace-release-line"></span><span class="workspace-release-copy"><span><strong>${escapeHtml(item.title)}</strong>${track}</span><small>${escapeHtml(readableFeedDate(item.publishedAt, item.dateBasis))} · ${item.documentCount} 份证据</small></span>${evidenceBadge}<i>›</i></button>`;
    };
    const datedReleases = family.releases.filter((item) => item.catalogStatus !== "evidence_only");
    const reportOnlyItems = family.releases.filter((item) => item.catalogStatus === "evidence_only");
    const latestRelease = datedReleases[0] ? releaseButton(datedReleases[0], true) : "";
    const historyItems = datedReleases.slice(1);
    const activeInHistory = historyItems.some((item) => currentReleaseItem?.releaseId === item.releaseId);
    const history = historyItems.length ? `<details class="workspace-history" ${activeInHistory ? "open" : ""}><summary>历史发布 <b>${historyItems.length}</b><i>⌄</i></summary><div>${historyItems.map((item) => releaseButton(item)).join("")}</div></details>` : "";
    const activeInReports = reportOnlyItems.some((item) => currentReleaseItem?.releaseId === item.releaseId);
    const reports = reportOnlyItems.length ? `<details class="workspace-history" ${activeInReports || !latestRelease ? "open" : ""}><summary>官方报告 <b>${reportOnlyItems.length}</b><i>⌄</i></summary><div>${reportOnlyItems.map((item) => releaseButton(item)).join("")}</div></details>` : "";
    const emptyState = `<div class="workspace-watch-state"><span class="status-dot"></span><span><strong>官方来源监控中</strong><small>发现首个发布后自动建立工作区</small></span></div>`;
    const techReportTotal = family.releases.reduce((total, item) => total + (item.techReportCount || 0), 0);
    const familySummary = datedReleases.length || reportOnlyItems.length ? `${datedReleases.length} 次发布 · ${techReportTotal} 份 Tech Report` : "监控中";
    return `<details class="model-workspace-group${activeFamily ? " active" : ""}" ${(activeFamily || (!currentReleaseItem && familyIndex === 0)) ? "open" : ""}><summary><span class="workspace-family-logo">${currentReleaseLogo(logoItem)}</span><span class="workspace-family-copy"><strong>${escapeHtml(family.modelName)}</strong><small>${escapeHtml(family.provider)} · ${familySummary}</small></span><i>⌄</i></summary><div class="workspace-release-list">${latestRelease || (reportOnlyItems.length ? "" : emptyState)}${history}${reports}</div></details>`;
  }).join("") : '<p class="sidebar-empty">请先选择想要追踪的模型</p>';
  if (currentReleaseItem) requestAnimationFrame(() => list.querySelector(".model-workspace-group.active")?.scrollIntoView({ block: "nearest" }));
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    showView(button.dataset.view);
    document.querySelector(".sidebar").classList.remove("open");
  });
});

document.querySelectorAll("[data-jump]").forEach((button) => {
  button.addEventListener("click", () => document.getElementById(button.dataset.jump)?.scrollIntoView({ behavior: "smooth" }));
});

function renderConceptDrawer(concept) {
  closeDrawer();
  closeSelectionAssistant();
  const title = concept.title || concept.name;
  const relationships = concept.relationships || [];
  const prerequisites = concept.prerequisites || relationships.filter((item) => item.type === "prerequisite").map((item) => item.name);
  const related = concept.relations || relationships.filter((item) => item.type !== "prerequisite").map((item) => item.name);
  const evolution = concept.evolution || relationships.filter((item) => item.type === "evolves_from").map((item) => item.name);
  const flow = concept.flow || [title, ...relationships.slice(0, 3).map((item) => item.name)];
  document.getElementById("conceptTitle").textContent = title;
  document.getElementById("conceptOneLiner").textContent = concept.oneLiner;
  document.getElementById("conceptWhy").textContent = concept.why;
  document.getElementById("conceptAnalogy").textContent = concept.analogy;
  document.getElementById("conceptImpact").textContent = concept.impact || concept.productImpact;
  document.getElementById("conceptFlow").innerHTML = flow.map((step, index) => `${index ? "<i>→</i>" : ""}<span>${escapeHtml(step)}</span>`).join("");
  document.getElementById("conceptPrerequisites").innerHTML = prerequisites.length ? prerequisites.map((item) => `<span>✓ ${escapeHtml(item)}</span>`).join("") : "<small>这是理解当前发布的起点概念</small>";
  document.getElementById("relationCenter").textContent = title;
  document.getElementById("conceptRelations").innerHTML = related.length ? related.map((item) => `<span>${escapeHtml(item)}</span>`).join("") : "<span>当前关系仍在整理</span>";
  document.getElementById("conceptEvolution").innerHTML = (evolution.length ? evolution : [title]).map((item, index) => `${index ? "<i>→</i>" : ""}<span>${escapeHtml(item)}</span>`).join("");
  document.getElementById("conceptCompareQuestion").textContent = concept.compareQuestion || "它和相邻技术有什么区别？";
  document.getElementById("conceptComparison").textContent = concept.comparison || relationships.find((item) => item.type === "contrasts_with")?.explanation || "当前证据只支持它与相关概念的连接，更多比较需要回到具体报告语境。";
  const evidence = concept.evidence || [];
  const evidenceBlock = document.getElementById("conceptEvidenceBlock");
  evidenceBlock.innerHTML = evidence.length ? `<span>OFFICIAL EVIDENCE</span>${evidence.map((item) => `<div><b>${escapeHtml(item.title)}</b><small>${item.firstPage ? `P${item.firstPage}${item.lastPage && item.lastPage !== item.firstPage ? `–${item.lastPage}` : ""}` : "页码待定位"} · ${escapeHtml(knowledgeStateLabel(item.evidenceState))}</small></div>`).join("")}` : `<span>KNOWLEDGE STATE</span><div><b>${escapeHtml(knowledgeStateLabel(concept.evidenceState || "background"))}</b><small>通用解释，不作为当前发布的官方主张</small></div>`;
  const evidenceAction = document.getElementById("conceptEvidenceAction");
  const primaryEvidence = evidence.find((item) => item.readable) || evidence[0];
  evidenceAction.hidden = !primaryEvidence;
  evidenceAction.dataset.reportId = primaryEvidence?.reportId || "";
  evidenceAction.dataset.page = primaryEvidence?.firstPage || "";
  drawer.classList.add("open");
  backdrop.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
}

function openConcept(key) {
  const concept = concepts[key];
  if (concept) renderConceptDrawer(concept);
}

async function openCanonicalConcept(identifier) {
  const cached = currentKnowledgeGraph?.primaryConcepts?.find((item) => item.id === identifier || item.aliases?.some((alias) => alias.toLowerCase() === String(identifier).toLowerCase()));
  if (cached) return renderConceptDrawer(cached);
  const releaseQuery = currentReleaseItem ? `?releaseId=${encodeURIComponent(currentReleaseItem.releaseId)}` : "";
  try {
    const response = await fetch(`/api/concepts/${encodeURIComponent(identifier)}${releaseQuery}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderConceptDrawer(await response.json());
  } catch {
    const fallbackKey = ({ "mixture-of-experts": "moe-architecture", "thinking-mode": "hybrid-reasoning" })[identifier];
    if (fallbackKey) openConcept(fallbackKey);
  }
}

function closeDrawer() {
  drawer.classList.remove("open");
  document.getElementById("variantInspector")?.classList.remove("open");
  backdrop.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  document.getElementById("variantInspector")?.setAttribute("aria-hidden", "true");
  document.querySelectorAll("[data-variant]").forEach((button) => button.classList.remove("selected"));
}

function openVariant(key, trigger) {
  const variant = modelVariants[key];
  if (!variant) return;
  closeDrawer();
  closeSelectionAssistant();
  document.querySelectorAll("[data-variant]").forEach((button) => button.classList.toggle("selected", button === trigger));
  document.getElementById("variantTitle").textContent = variant.name;
  document.getElementById("variantArchitecture").textContent = variant.architecture;
  document.getElementById("variantScaleBadge").textContent = variant.badge;
  document.getElementById("variantSummary").textContent = variant.summary;
  document.getElementById("variantTotalParams").textContent = variant.total;
  document.getElementById("variantActiveParams").textContent = variant.active;
  document.getElementById("variantDeployment").textContent = variant.deployment;
  document.getElementById("variantDecision").textContent = variant.decision;
  document.getElementById("variantTradeoff").textContent = variant.tradeoff;
  document.getElementById("variantUseCases").innerHTML = variant.uses.map((item) => `<b>${escapeHtml(item)}</b>`).join("");
  const architectureAction = document.getElementById("variantArchitectureAction");
  architectureAction.dataset.concept = variant.concept || "";
  architectureAction.innerHTML = variant.concept ? "理解 MoE 架构 <span>→</span>" : "查看发布速览 <span>→</span>";
  const inspector = document.getElementById("variantInspector");
  inspector.classList.add("open");
  inspector.setAttribute("aria-hidden", "false");
  backdrop.classList.add("open");
}

document.querySelectorAll("[data-variant]").forEach((button) => button.addEventListener("click", () => openVariant(button.dataset.variant, button)));
document.getElementById("variantInspectorClose")?.addEventListener("click", closeDrawer);
document.getElementById("variantArchitectureAction")?.addEventListener("click", (event) => {
  const concept = event.currentTarget.dataset.concept;
  if (concept) openConcept(concept);
  else showView("brief");
});

document.querySelectorAll(".change-card").forEach((card) => {
  card.addEventListener("click", () => openConcept(card.dataset.concept));
  card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") openConcept(card.dataset.concept); });
});
document.getElementById("drawerClose").addEventListener("click", closeDrawer);
backdrop.addEventListener("click", closeDrawer);
document.addEventListener("click", (event) => {
  const node = event.target.closest("[data-knowledge-concept]");
  if (node) openCanonicalConcept(node.dataset.knowledgeConcept);
});
document.getElementById("conceptEvidenceAction").addEventListener("click", async (event) => {
  const reportId = event.currentTarget.dataset.reportId;
  if (!reportId) return;
  showView("report");
  await loadFeaturedReport(reportId);
  const page = event.currentTarget.dataset.page;
  if (page && featuredReport?.original_pdf_url) document.getElementById("locateOriginalPage").dataset.knowledgePage = page;
});

const sectionNotes = {
  abstract: ["Qwen3 最核心的变化是什么？", "把思考与非思考模式统一在同一个模型框架，并允许控制推理预算。", "先读这一页建立全局判断；所有结论都可以回到官方原文。"],
  introduction: ["这份报告为什么值得看？", "它同时交代模型系列、训练规模、推理模式与主要评测结果。", "注意区分作者报告的评测结果与真实业务中的实际表现。"],
  architecture: ["模型能力是怎样训练出来的？", "这一部分覆盖架构、预训练与分阶段后训练，是技术细节最集中的章节。", "AI PM 可重点查找 thinking mode、MoE 和 post-training；工程师建议阅读全文。"],
  "general rl": ["General RL 在解决什么？", "它用覆盖二十多种任务的奖励系统增强通用能力与稳定性。", "重点看不同训练阶段带来的提升与退化，避免只看最终总分。"],
  conclusion: ["作者最终确认了哪些结论？", "这一部分汇总训练阶段、模式融合与不同规模模型的实验观察。", "结论章节包含较长评测内容，阅读时同时核对具体测试条件。"],
  references: ["这些结论建立在哪些研究之上？", "参考文献记录了架构、训练和评测所依据的相关工作。", "需要深挖某个概念时，从这里追溯原始论文。"]
};

const sectionAids = {
  abstract: { points: ["同时发布 Dense 与 MoE 两类模型，规模覆盖 0.6B–235B。", "同一个模型统一支持 thinking 与 non-thinking 两种模式。", "Thinking Budget 用于平衡效果、延迟与成本。"], translation: "摘要的核心意思是：Qwen3 不只是扩大参数规模，而是把深度推理与快速回答放进同一个模型体系，并允许产品按任务控制推理投入。" },
  introduction: { points: ["预训练数据约 36 万亿 token，覆盖 119 种语言和方言。", "后训练采用多个阶段，分别强化推理和通用能力。", "通过强模型蒸馏，把能力迁移到更小的模型。"], translation: "引言交代了 Qwen3 的完整技术路线：更大且更多语的数据、分阶段后训练，以及把大模型能力迁移到小模型的蒸馏方法。" },
  architecture: { points: ["模型家族包含 6 个 Dense 模型和 2 个 MoE 模型。", "MoE 使用 128 个专家，每个 token 激活其中 8 个。", "4B 以上 Dense 与两个 MoE 模型支持 128K 上下文。"], translation: "这一节解释模型如何构建和训练。重点是 Dense 与 MoE 两条架构路线，以及预训练、长上下文扩展和后训练之间的衔接。" },
  "general rl": { points: ["General RL 覆盖二十多类任务和奖励信号。", "目标包括指令遵循、格式控制和回答稳定性。", "通用强化可能牺牲局部专项能力，需要逐项查看评测。"], translation: "General RL 不是只强化数学或代码，而是让模型在更广泛任务中更可靠；判断效果时不能只看总分，还要关注各项能力是否出现退化。" },
  conclusion: { points: ["统一双模式是 Qwen3 的核心产品变化。", "不同规模模型共享相似训练路线。", "论文结论仍需结合具体任务和评测条件理解。"], translation: "结论汇总了模型系列、训练流程和评测观察。它说明官方验证了什么，但不代表所有真实业务场景都会得到相同结果。" },
  references: { points: ["参考文献是继续追溯技术来源的入口。", "架构、训练与评测方法分别来自不同研究脉络。", "遇到关键主张时，应优先回到被引用的原始工作。"], translation: "这一节不是正文总结，而是证据索引。FrontierLens 将它保留下来，方便用户从报告继续追溯概念和方法的原始出处。" }
};

const glossary = {
  moe: { label: "Mixture-of-Experts (MoE)", aliases: ["Mixture-of-Experts", "Mixture of Experts", "MoE"], definition: "一种稀疏模型架构：模型拥有多个专家网络，但每个 token 只调用少数专家，因此可以扩大总容量而不让每次计算都使用全部参数。" },
  thinking: { label: "Thinking Mode", aliases: ["thinking mode", "thinking-mode"], definition: "模型在给出答案前投入更多推理步骤的模式，适合数学、代码和规划等复杂任务，但通常需要更长时间和更高成本。" },
  nonthinking: { label: "Non-thinking Mode", aliases: ["non-thinking mode", "non-thinking"], definition: "跳过长推理过程、直接生成回答的模式，适合日常问答和强调响应速度的场景。" },
  budget: { label: "Thinking Budget", aliases: ["thinking budget"], definition: "对模型推理投入设置上限，让产品在答案质量、等待时间和调用成本之间做可控取舍。" },
  dense: { label: "Dense Model", aliases: ["dense models", "dense model", "Dense"], definition: "每次处理 token 时都会使用模型主体的全部参数。结构相对简单稳定，但模型越大，每次计算成本通常也越高。" },
  rl: { label: "Reinforcement Learning", aliases: ["reinforcement learning", "General RL"], definition: "模型通过奖励信号学习哪些行为更好。报告中的 General RL 用于提升指令遵循、格式控制和通用稳定性。" },
  distillation: { label: "Knowledge Distillation", aliases: ["knowledge distillation", "distillation"], definition: "让较小模型学习较强模型输出或行为的方法，用较低部署成本保留尽可能多的能力。" },
  activated: { label: "Activated Parameters", aliases: ["activated parameters", "active parameters"], definition: "一次前向计算中真正参与运算的参数量。对 MoE 来说，它通常远小于模型的总参数量。" },
  transformer: { label: "Transformer", aliases: ["Transformer"], definition: "当前大语言模型常用的基础架构，利用注意力机制让不同 token 彼此关联并逐层形成表示。" },
  pretraining: { label: "Pre-training", aliases: ["pre-training", "pretraining", "pre-training stage"], definition: "模型先从大规模语料中学习语言、知识和模式的基础训练阶段。" },
  posttraining: { label: "Post-training", aliases: ["post-training", "post training"], definition: "预训练之后，通过监督微调、强化学习等方式让模型更会遵循指令和完成目标任务。" }
};

const glossaryConceptIds = {
  moe: "mixture-of-experts",
  thinking: "thinking-mode",
  budget: "thinking-budget",
  dense: "dense-model",
  rl: "reinforcement-learning",
  transformer: "transformer",
};

const glossaryAliases = Object.entries(glossary)
  .flatMap(([key, item]) => item.aliases.map((alias) => ({ key, alias })))
  .sort((a, b) => b.alias.length - a.alias.length);
const glossaryPattern = new RegExp(`\\b(${glossaryAliases.map(({ alias }) => alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`, "gi");

function glossaryKeyFor(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return glossaryAliases.find(({ alias }) => normalized === alias.toLowerCase() || normalized.includes(alias.toLowerCase()))?.key;
}

function decorateTerms(html) {
  return html.replace(glossaryPattern, (match) => {
    const key = glossaryKeyFor(match);
    return key ? `<button class="term-button" data-term="${key}" type="button">${match}</button>` : match;
  });
}

function textToHtml(text) {
  return String(text || "")
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => `<p>${decorateTerms(escapeHtml(paragraph).replaceAll("\n", "<br>"))}</p>`)
    .join("");
}

function loadReportSection(section) {
  const index = Number(section);
  const data = reportSections[index];
  if (!data) return;
  document.getElementById("paperTitle").textContent = data.title;
  document.getElementById("paperContent").innerHTML = textToHtml(data.text);
  const notes = sectionNotes[data.title.toLowerCase()] || ["这一节在讲什么？", `这是官方报告的“${data.title}”章节，内容未经摘要替代。`, "遇到重要结论时，请结合页码在原始 PDF 中核对图表和上下文。"];
  document.getElementById("noteQuestion").textContent = notes[0];
  document.getElementById("noteAnswer").textContent = notes[1];
  document.getElementById("noteTip").textContent = `${notes[2]} · 原文第 ${data.first_page}–${data.last_page} 页`;
  const aid = sectionAids[data.title.toLowerCase()] || { points: ["先确认这一节的研究问题。", "区分作者主张、实验结果与推测。", "重要结论回到原始 PDF 核对上下文。"], translation: `本节围绕“${data.title}”展开。请把辅助译读当作理解线索，而不是原文的替代。` };
  document.getElementById("noteKeyPoints").innerHTML = aid.points.map((point) => `<li>${escapeHtml(point)}</li>`).join("");
  document.getElementById("noteTranslation").textContent = aid.translation;
  document.querySelectorAll(".report-toc button[data-section]").forEach((button) => button.classList.toggle("active", button.dataset.section === String(index)));
  const progress = Math.round(((index + 1) / reportSections.length) * 100);
  document.querySelector(".toc-progress strong").textContent = `${progress}%`;
  document.querySelector(".toc-progress div i").style.width = `${progress}%`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelector(".report-toc").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-section]");
  if (button) loadReportSection(button.dataset.section);
});
document.querySelectorAll("[data-report-section]").forEach((button) => button.addEventListener("click", () => { showView("report"); loadReportSection(button.dataset.reportSection); }));

async function loadFeaturedReport(reportId = null) {
  const content = document.getElementById("paperContent");
  content.innerHTML = '<p class="reader-loading">正在从 FrontierLens 资料库载入官方报告…</p>';
  try {
    const endpoint = reportId ? `/api/reports/${encodeURIComponent(reportId)}` : "/api/reports/featured";
    const response = await fetch(endpoint, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    featuredReport = await response.json();
    reportSections = featuredReport.parsed?.sections || [];
    if (!reportSections.length) throw new Error("报告没有可用章节");
    document.getElementById("reportDocumentTitle").textContent = featuredReport.title;
    document.getElementById("reportDocumentMeta").textContent = `完整文献阅读 · ${featuredReport.page_count} 页 · 已保存并结构化解析`;
    document.getElementById("paperKicker").textContent = `${featuredReport.provider.toUpperCase()} · OFFICIAL TECHNICAL REPORT`;
    const pdfLink = document.getElementById("openOriginalPdf");
    pdfLink.href = featuredReport.original_pdf_url;
    pdfLink.classList.remove("disabled");
    document.getElementById("reportTocItems").innerHTML = reportSections.map((item, index) => `<button data-section="${index}" class="${index === 0 ? "active" : ""}"><i>${String(index + 1).padStart(2, "0")}</i>${escapeHtml(item.title)}<small>${item.first_page}–${item.last_page}</small></button>`).join("");
    loadReportSection(0);
  } catch (error) {
    content.innerHTML = '<div class="reader-error"><strong>暂时无法载入官方报告</strong><p>请确认 FrontierLens 数据服务已启动，然后刷新页面。</p></div>';
    document.getElementById("reportDocumentMeta").textContent = "数据服务暂未连接";
  }
}

loadFeaturedReport();

const evidenceRoutes = {
  why: {
    label: "为什么这么做？",
    title: "先读 Tech Report，再用 Official Blog 补充设计动机",
    note: "论文负责方法与实验，官方博客负责解释发布背景；两者不是同一权重。",
    sources: [{ name: "Tech Report", role: "主要依据", weight: "1.0" }, { name: "Official Blog", role: "动机补充", weight: "0.8" }]
  },
  implementation: {
    label: "怎么实现？",
    title: "优先查看 Official GitHub，并回到 Tech Report 核对方法",
    note: "代码和部署说明回答“怎么做”，报告回答“为什么这样设计”；实现细节不能反过来替代实验依据。",
    sources: [{ name: "Official GitHub", role: "主要依据", weight: "0.7" }, { name: "Tech Report", role: "方法核对", weight: "1.0" }]
  },
  performance: {
    label: "效果如何？",
    title: "优先核对 Benchmark，再阅读 Tech Report 的测试条件",
    note: "分数只有和数据集、基线、推理预算及限制一起阅读才有意义。FrontierLens 不把单个榜单数字当成最终结论。",
    sources: [{ name: "Benchmark", role: "结果依据", weight: "0.8" }, { name: "Tech Report", role: "条件核对", weight: "1.0" }]
  },
  safety: {
    label: "安全吗？",
    title: "优先查找 Safety Report，并用 Tech Report 核对能力边界",
    note: "如果厂商没有发布独立安全报告，FrontierLens 会明确标记缺失，不使用社区材料冒充官方证据。",
    sources: [{ name: "Safety Report", role: "风险依据", weight: "0.8" }, { name: "Tech Report", role: "能力边界", weight: "1.0" }]
  }
};

function renderEvidenceRoute(key) {
  const route = evidenceRoutes[key];
  if (!route) return;
  document.getElementById("evidenceQuestionLabel").textContent = route.label;
  document.getElementById("evidenceRouteTitle").textContent = route.title;
  document.getElementById("evidenceRouteNote").textContent = route.note;
  document.getElementById("routeEvidenceList").innerHTML = route.sources.map((source, index) => `<div class="route-evidence-item ${index === 0 ? "primary" : ""}"><span>${index + 1}</span><div><strong>${escapeHtml(source.name)}</strong><small>${escapeHtml(source.role)}</small></div><b>${escapeHtml(source.weight)}</b></div>`).join("");
  document.querySelectorAll("[data-evidence-question]").forEach((button) => button.classList.toggle("active", button.dataset.evidenceQuestion === key));
}

document.querySelectorAll("[data-evidence-question]").forEach((button) => button.addEventListener("click", () => renderEvidenceRoute(button.dataset.evidenceQuestion)));
renderEvidenceRoute("why");

const trackingStorageKey = "frontierlens-tracking-v1";
const trackingProfileStorageKey = "frontierlens-profile-v1";
let trackingProfile = null;
const trackingModal = document.getElementById("trackingModal");
let draftCustomSources = [];
const feedSourceNames = {
  "tech-report": "Tech Report",
  "official-blog": "Official Blog",
  benchmark: "Benchmark",
  github: "GitHub",
  "safety-report": "Safety Report",
};

function readTrackingPreferences() {
  try { return JSON.parse(localStorage.getItem(trackingStorageKey) || "null"); } catch { return null; }
}

function storeTrackingPreferences(preferences) {
  localStorage.setItem(trackingStorageKey, JSON.stringify(preferences));
}

function readTrackingProfile() {
  try { return JSON.parse(localStorage.getItem(trackingProfileStorageKey) || "null"); } catch { return null; }
}

async function ensureTrackingProfile() {
  trackingProfile = readTrackingProfile();
  if (trackingProfile?.profileId && trackingProfile?.accessToken) return trackingProfile;
  const response = await fetch("/api/profiles", { method: "POST" });
  if (!response.ok) throw new Error("无法创建安全设备身份");
  trackingProfile = await response.json();
  localStorage.setItem(trackingProfileStorageKey, JSON.stringify(trackingProfile));
  return trackingProfile;
}

function profileRequestOptions(options = {}) {
  return {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${trackingProfile?.accessToken || ""}`,
    },
  };
}

async function fetchTrackingPreferences() {
  const response = await fetch(`/api/preferences/${encodeURIComponent(trackingProfile.profileId)}`, profileRequestOptions({ cache: "no-store" }));
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("无法读取追踪设置");
  return response.json();
}

async function syncTrackingPreferences(preferences) {
  const response = await fetch(`/api/preferences/${encodeURIComponent(trackingProfile.profileId)}`, profileRequestOptions({
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ models: preferences.models, sources: preferences.sources, customModels: preferences.customModels || [], customSources: preferences.customSources || [] }),
  }));
  if (!response.ok) throw new Error("无法保存追踪设置");
  return response.json();
}

function selectedTrackingValues(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((input) => input.value);
}

function updateTrackingSummary(preferences = readTrackingPreferences()) {
  const modelCount = preferences?.models?.length || 1;
  const sourceCount = (preferences?.sources?.length || 0) + (preferences?.customSources?.length || 0) || 5;
  document.getElementById("trackingSummary").textContent = `${modelCount} 个模型 · ${sourceCount} 类来源`;
}

function renderCustomTrackingItems() {
  document.getElementById("customSourceList").innerHTML = draftCustomSources.map((item, index) => `<span class="custom-tracking-chip"><strong>${escapeHtml(item.name)}</strong><small>等待验证</small><button type="button" data-remove-custom-source="${index}" aria-label="移除 ${escapeHtml(item.name)}">×</button></span>`).join("");
}

function readableFeedDate(value, basis = "official_release") {
  if (basis === "official_report_undated") return "官方报告 · 日期待核验";
  if (basis === "pending" || !value) return "日期待核验";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "已发现";
  const prefixes = {
    official_release: "正式发布于",
    official_document_update: "官方文档更新于",
    official_source_published: "官方资料发表于",
  };
  const prefix = prefixes[basis] || "官方记录于";
  return `${prefix} ${new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "short", day: "numeric" }).format(date)}`;
}

function feedDescription(item) {
  if (item.sourceKeys.includes("tech-report")) return `本次发布已归档 ${item.documentCount || 1} 份官方证据${item.pageCount ? `，主报告共 ${item.pageCount} 页` : ""}。先看变化，再按问题回到对应原文。`;
  if (item.sourceKeys.includes("official-blog") && item.sourceKeys.includes("safety-report")) return "官方发布信息与安全资料已合并归档，可同时判断能力变化、产品价值与使用边界。";
  if (item.sourceKeys.includes("safety-report")) return "官方安全资料已被发现，可用于核对能力边界、风险评估与使用限制。";
  if (item.sourceKeys.includes("github")) return "官方实现入口有新内容，可进一步查看模型说明、部署方式与开源资源。";
  return "你追踪的官方来源出现了新内容，FrontierLens 已将它加入个人更新流。";
}

function renderPersonalizedFeed(payload) {
  const container = document.getElementById("personalizedFeed");
  const preferences = payload.preferences;
  const modelNames = { qwen: "Qwen", gpt: "GPT", claude: "Claude", gemini: "Gemini", deepseek: "DeepSeek", kimi: "Kimi", seed: "Seed", glm: "GLM", minimax: "MiniMax" };
  const models = preferences.models.map((key) => modelNames[key] || key).join("、");
  const sources = [...preferences.sources.map((key) => feedSourceNames[key] || key), ...(preferences.customSources || []).map((item) => item.name)].join("、");
  document.getElementById("feedPreferenceSummary").textContent = `正在追踪 ${models} · ${preferences.sources.length + (preferences.customSources?.length || 0)} 类官方来源`;
  renderSidebarWorkspaces(payload.items, payload.watching, preferences);

  const query = document.getElementById("feedSearchInput").value.trim().toLowerCase();
  const browsingArchive = Boolean(query || activeFeedFilter !== "all" || activeFeedModel !== "all");
  const defaultItems = payload.items.filter((item) => item.catalogStatus !== "evidence_only");
  const newlyDiscoveredReports = payload.items
    .filter((item) => item.catalogStatus === "evidence_only" && item.hasTechReport)
    .sort((a, b) => String(b.discoveredAt || "").localeCompare(String(a.discoveredAt || "")))
    .slice(0, 6);
  const feedItems = browsingArchive ? payload.items : [...defaultItems.slice(0, 24), ...newlyDiscoveredReports];
  const filteredItems = feedItems.filter((item) => {
    const matchesQuery = !query || `${item.title} ${item.modelName} ${item.provider} ${item.sourceLabels.join(" ")}`.toLowerCase().includes(query);
    const matchesFilter = activeFeedFilter === "all"
      || (activeFeedFilter === "model-card"
        ? item.documents.some((document) => document.reportType === "model_card")
        : activeFeedFilter === "safety-report"
          ? item.documents.some((document) => document.reportType === "safety_report")
          : item.documents.some((document) => document.sourceKeys.includes(activeFeedFilter)));
    const matchesModel = activeFeedModel === "all" || item.modelKey === activeFeedModel;
    return matchesQuery && matchesFilter && matchesModel;
  });
  document.getElementById("feedResultCount").textContent = `${filteredItems.length} 条更新`;

  let reportSectionStarted = false;
  const cards = filteredItems.map((item) => {
    const startsReportSection = !browsingArchive && item.catalogStatus === "evidence_only" && !reportSectionStarted;
    if (startsReportSection) reportSectionStarted = true;
    const sourcePills = item.sourceLabels.map((label) => `<span>${escapeHtml(label)}</span>`).join("");
    const logoPath = modelLogoPaths[item.modelKey];
    const modelMark = logoPath
      ? `<img src="${logoPath}" alt="${escapeHtml(item.provider)} Logo" />`
      : `<b aria-label="${escapeHtml(item.provider)}">${escapeHtml(item.mark || item.modelName.slice(0, 1))}</b>`;
    const reportAction = item.canReadTechReport
      ? `<button data-open-release="${item.releaseId}" data-release-view="report">阅读 Tech Report</button>`
      : item.hasTechReport
        ? `<a href="${escapeHtml(item.documents.find((document) => document.reportType === "technical_report")?.url || item.url)}" target="_blank" rel="noopener">打开原始 Tech Report ↗</a>`
        : `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">查看当前证据 ↗</a>`;
    const actions = item.workspaceReady
      ? `<button class="feed-primary-action" data-open-release="${item.releaseId}" data-release-view="brief">进入发布工作区</button>${reportAction}`
      : `<a class="feed-primary-action" href="${escapeHtml(item.url)}" target="_blank" rel="noopener">打开官方来源 ↗</a>`;
    const highlights = item.highlights?.length ? `<div class="feed-release-highlights"><div class="feed-highlight-heading"><span>WHAT CHANGED</span><small>${escapeHtml(item.highlightBasis)}</small></div><ul>${item.highlights.map((highlight) => `<li><b>${escapeHtml(highlight.label)}</b><span>${escapeHtml(highlight.text)}</span></li>`).join("")}</ul></div>` : "";
    const sectionDivider = startsReportSection ? `<div class="feed-section-divider"><span>RECENTLY RECOVERED</span><div><strong>新收录的官方 Tech Report</strong><small>发布日期尚待核验的报告不会混入发布时序，但仍可完整阅读。</small></div></div>` : "";
    return `${sectionDivider}<article class="feed-card${item.catalogStatus === "evidence_only" ? " report-only" : ""}">
      <span class="feed-model-mark">${modelMark}</span>
      <div class="feed-card-body">
        <div class="feed-card-meta"><span class="feed-source-pill">${escapeHtml(item.sourceLabels[0])}</span><span>${escapeHtml(item.modelName)}</span><span>${escapeHtml(readableFeedDate(item.publishedAt, item.dateBasis))}</span></div>
        <h2>${escapeHtml(item.title)}</h2>
        <p>${escapeHtml(feedDescription(item))}</p>
        ${highlights}
        <div class="feed-evidence-row">${sourcePills}<small>${item.documentCount || 1} 份证据并存</small></div>
      </div>
      <div class="feed-card-actions">${actions}</div>
    </article>`;
  }).join("");

  const watching = !query && activeFeedFilter === "all" ? payload.watching
    .filter((item) => activeFeedModel === "all" || item.modelKey === activeFeedModel)
    .map((item) => `<div class="feed-watching"><span><strong>${escapeHtml(item.modelName)}</strong><small> · ${escapeHtml(item.provider)}</small></span><small>官方来源监控中，发现符合偏好的新内容后会出现在这里。</small></div>`).join("") : "";
  if (!cards && !watching) {
    container.innerHTML = `<div class="feed-empty"><strong>暂时没有匹配的更新</strong>当前筛选范围：${escapeHtml(sources)}。你可以调整追踪设置，或等待下一次官方来源扫描。</div>`;
    return;
  }
  container.innerHTML = cards + watching;
}

async function loadPersonalizedFeed() {
  const container = document.getElementById("personalizedFeed");
  if (!container) return;
  try {
    if (!trackingProfile) await ensureTrackingProfile();
    const response = await fetch(`/api/feed/${encodeURIComponent(trackingProfile.profileId)}`, profileRequestOptions({ cache: "no-store" }));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    personalizedFeedPayload = await response.json();
    renderPersonalizedFeed(personalizedFeedPayload);
  } catch {
    const local = readTrackingPreferences();
    if (local) document.getElementById("feedPreferenceSummary").textContent = `${local.models.length} 个模型 · ${local.sources.length} 类官方来源`;
    container.innerHTML = '<div class="feed-error"><strong>暂时无法生成更新流</strong>你的追踪设置仍然保留。请确认 FrontierLens 数据服务已启动后刷新页面。</div>';
  }
}

function restoreTrackingPreferences() {
  const preferences = readTrackingPreferences();
  if (!preferences) return;
  document.querySelectorAll('input[name="tracked-model"]').forEach((input) => { input.checked = preferences.models.includes(input.value); });
  document.querySelectorAll('input[name="tracked-source"]').forEach((input) => { input.checked = preferences.sources.includes(input.value); });
  draftCustomSources = [...(preferences.customSources || [])];
  renderCustomTrackingItems();
  updateTrackingSummary(preferences);
}

function openTrackingSettings() {
  restoreTrackingPreferences();
  document.getElementById("trackingValidation").textContent = "";
  trackingModal.classList.add("open");
  trackingModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function closeTrackingSettings() {
  trackingModal.classList.remove("open");
  trackingModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

document.getElementById("openTrackingSettings").addEventListener("click", openTrackingSettings);
document.querySelectorAll("[data-open-tracking]").forEach((button) => button.addEventListener("click", openTrackingSettings));
document.getElementById("closeTrackingSettings").addEventListener("click", closeTrackingSettings);
document.getElementById("skipTrackingSettings").addEventListener("click", () => {
  sessionStorage.setItem("frontierlens-tracking-dismissed", "1");
  closeTrackingSettings();
});
trackingModal.addEventListener("click", (event) => { if (event.target === trackingModal) closeTrackingSettings(); });

document.getElementById("toggleCustomSource").addEventListener("click", () => { document.getElementById("customSourceForm").hidden = !document.getElementById("customSourceForm").hidden; });
document.getElementById("addCustomSource").addEventListener("click", () => {
  const nameInput = document.getElementById("customSourceName");
  const urlInput = document.getElementById("customSourceUrl");
  const name = nameInput.value.trim();
  const url = urlInput.value.trim();
  const validation = document.getElementById("trackingValidation");
  if (!name) return nameInput.focus();
  if (!url.startsWith("https://")) {
    validation.textContent = "自定义来源必须填写 HTTPS 官方地址。";
    return urlInput.focus();
  }
  validation.textContent = "";
  draftCustomSources.push({ name, url, status: "pending_verification" });
  nameInput.value = "";
  urlInput.value = "";
  renderCustomTrackingItems();
});
document.getElementById("customSourceList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-custom-source]");
  if (!button) return;
  draftCustomSources.splice(Number(button.dataset.removeCustomSource), 1);
  renderCustomTrackingItems();
});

document.getElementById("saveTrackingSettings").addEventListener("click", async (event) => {
  const models = selectedTrackingValues("tracked-model");
  const sources = selectedTrackingValues("tracked-source");
  const validation = document.getElementById("trackingValidation");
  if (!models.length || (!sources.length && !draftCustomSources.length)) {
    validation.textContent = !models.length ? "请至少选择一个模型家族。" : "请至少选择一种官方数据源。";
    return;
  }

  const button = event.currentTarget;
  const originalContent = button.innerHTML;
  button.disabled = true;
  button.textContent = "正在保存…";
  validation.textContent = "";
  const preferences = { models, sources, customModels: [], customSources: draftCustomSources, updatedAt: new Date().toISOString() };
  storeTrackingPreferences(preferences);
  updateTrackingSummary(preferences);
  try {
    const savedPreferences = await syncTrackingPreferences(preferences);
    storeTrackingPreferences(savedPreferences);
    sessionStorage.setItem("frontierlens-tracking-dismissed", "1");
    updateTrackingSummary(savedPreferences);
    loadPersonalizedFeed();
    closeTrackingSettings();
  } catch {
    validation.textContent = "已保存在此设备，连接恢复后可再次同步。";
  } finally {
    button.disabled = false;
    button.innerHTML = originalContent;
  }
});

async function initializeTrackingPreferences() {
  let preferences = readTrackingPreferences();
  try {
    await ensureTrackingProfile();
    const serverPreferences = await fetchTrackingPreferences();
    if (serverPreferences) {
      preferences = serverPreferences;
      storeTrackingPreferences(serverPreferences);
    } else if (preferences) {
      const migratedPreferences = await syncTrackingPreferences(preferences);
      preferences = migratedPreferences;
      storeTrackingPreferences(migratedPreferences);
    }
  } catch {
    // Static demos and temporarily unavailable services continue with the local copy.
  }
  restoreTrackingPreferences();
  loadPersonalizedFeed();
  if (!preferences && !sessionStorage.getItem("frontierlens-tracking-dismissed")) setTimeout(openTrackingSettings, 450);
}

initializeTrackingPreferences();

document.addEventListener("click", (event) => {
  const action = event.target.closest("[data-open-release]");
  if (!action) return;
  const item = releaseById(action.dataset.openRelease);
  if (item) openReleaseWorkspace(item, action.dataset.releaseView || "brief");
});

document.getElementById("feedSearchInput").addEventListener("input", () => {
  if (personalizedFeedPayload) renderPersonalizedFeed(personalizedFeedPayload);
});

document.querySelectorAll("[data-feed-filter]").forEach((button) => button.addEventListener("click", () => {
  activeFeedFilter = button.dataset.feedFilter;
  document.querySelectorAll("[data-feed-filter]").forEach((item) => item.classList.toggle("active", item === button));
  if (personalizedFeedPayload) renderPersonalizedFeed(personalizedFeedPayload);
}));

document.querySelectorAll("[data-feed-model]").forEach((button) => button.addEventListener("click", () => {
  activeFeedModel = button.dataset.feedModel;
  document.querySelectorAll("[data-feed-model]").forEach((item) => item.classList.toggle("active", item === button));
  if (personalizedFeedPayload) renderPersonalizedFeed(personalizedFeedPayload);
}));

document.getElementById("locateOriginalPage").addEventListener("click", () => {
  if (!featuredReport || !reportSections.length) return;
  const activeIndex = Number(document.querySelector(".report-toc button.active")?.dataset.section || 0);
  const knowledgePage = Number(document.getElementById("locateOriginalPage").dataset.knowledgePage || 0);
  const page = knowledgePage || reportSections[activeIndex]?.first_page || 1;
  delete document.getElementById("locateOriginalPage").dataset.knowledgePage;
  window.open(`${featuredReport.original_pdf_url}#page=${page}`, "_blank", "noopener");
});

document.getElementById("toggleHighlights").addEventListener("click", (event) => {
  const notes = document.querySelector(".atlas-notes");
  notes.classList.toggle("is-hidden");
  event.currentTarget.textContent = notes.classList.contains("is-hidden") ? "显示 AI 辅助" : "隐藏 AI 辅助";
});

function activeReportSectionIndex() {
  return Number(document.querySelector(".report-toc button.active")?.dataset.section || 0);
}

async function requestAiAssistance(task, selectedText = "") {
  if (!featuredReport) throw new Error("报告尚未载入");
  if (!trackingProfile) await ensureTrackingProfile();
  const response = await fetch("/api/ai/assist", profileRequestOptions({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profileId: trackingProfile.profileId,
      reportId: featuredReport.id,
      sectionIndex: activeReportSectionIndex(),
      task,
      selectedText,
    }),
  }));
  if (!response.ok) throw new Error(`AI HTTP ${response.status}`);
  return response.json();
}

document.getElementById("summaryModeButton").addEventListener("click", async (event) => {
  const notes = document.querySelector(".atlas-notes");
  notes.classList.remove("is-hidden");
  document.getElementById("toggleHighlights").textContent = "隐藏 AI 辅助";
  notes.scrollIntoView({ behavior: "smooth", block: "nearest" });
  const button = event.currentTarget;
  const previous = button.textContent;
  button.disabled = true;
  button.textContent = "正在基于原文提炼…";
  try {
    const result = await requestAiAssistance("summarize");
    document.getElementById("noteAnswer").textContent = result.answer;
    if (result.keyPoints.length) document.getElementById("noteKeyPoints").innerHTML = result.keyPoints.map((point) => `<li>${escapeHtml(point)}</li>`).join("");
    document.getElementById("noteTip").textContent = `${result.whyItMatters || "结论仅基于当前章节原文。"} · 原文第 ${result.citation.firstPage}–${result.citation.lastPage} 页`;
  } catch {
    document.getElementById("noteTip").textContent = "在线 AI 暂不可用，当前展示经过人工校对的本地辅助内容；技术结论仍请核对原文。";
  } finally {
    button.disabled = false;
    button.textContent = previous;
  }
});

document.getElementById("toggleKeyPoints").addEventListener("click", (event) => {
  const active = event.currentTarget.classList.toggle("active");
  document.querySelector(".paper-page").classList.toggle("show-key-points", active);
  event.currentTarget.textContent = active ? "隐藏重点" : "显示重点";
});

document.getElementById("toggleTranslation").addEventListener("click", async (event) => {
  const card = document.getElementById("translationCard");
  const active = card.hidden;
  card.hidden = !active;
  event.currentTarget.classList.toggle("active", active);
  if (!active) return;
  card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  const translation = document.getElementById("noteTranslation");
  const fallback = translation.textContent;
  translation.textContent = "正在基于本节原文生成辅助译读…";
  try {
    const result = await requestAiAssistance("translate");
    translation.textContent = result.answer;
  } catch {
    translation.textContent = fallback;
  }
});

const paperFontSizes = [16, 18, 20, 22];
let paperFontIndex = 1;
function updatePaperFontSize() {
  const size = paperFontSizes[paperFontIndex];
  document.querySelector(".paper-page").style.setProperty("--paper-font-size", `${size}px`);
  document.getElementById("fontSizeLabel").textContent = paperFontIndex === 1 ? "标准" : `${size}px`;
  document.getElementById("decreaseFont").disabled = paperFontIndex === 0;
  document.getElementById("increaseFont").disabled = paperFontIndex === paperFontSizes.length - 1;
}

document.getElementById("decreaseFont").addEventListener("click", () => {
  paperFontIndex = Math.max(0, paperFontIndex - 1);
  updatePaperFontSize();
});

document.getElementById("increaseFont").addEventListener("click", () => {
  paperFontIndex = Math.min(paperFontSizes.length - 1, paperFontIndex + 1);
  updatePaperFontSize();
});
updatePaperFontSize();

const selectionAssistant = document.getElementById("selectionAssistant");
async function showTermExplanation(key, selectedText) {
  const item = glossary[key];
  document.getElementById("selectionTerm").textContent = item?.label || selectedText || "所选内容";
  const definition = document.getElementById("selectionDefinition");
  definition.textContent = item?.definition || "正在结合当前章节原文生成解释…";
  selectionAssistant.classList.add("open");
  selectionAssistant.setAttribute("aria-hidden", "false");
  selectionAssistant.scrollIntoView({ behavior: "smooth", block: "nearest" });
  const conceptButton = document.getElementById("openSelectionConcept");
  const conceptId = glossaryConceptIds[key];
  conceptButton.hidden = !conceptId;
  conceptButton.dataset.conceptId = conceptId || "";
  if (!item && selectedText) {
    try {
      const result = await requestAiAssistance("explain", selectedText);
      definition.textContent = [result.answer, result.whyItMatters].filter(Boolean).join("\n\n");
    } catch {
      definition.textContent = `“${selectedText}”暂时无法生成在线解释。你仍可根据右侧页码回到官方原文核对上下文。`;
    }
  }
}

document.getElementById("openSelectionConcept").addEventListener("click", (event) => {
  const conceptId = event.currentTarget.dataset.conceptId;
  if (conceptId) openCanonicalConcept(conceptId);
});

function closeSelectionAssistant() {
  selectionAssistant.classList.remove("open");
  selectionAssistant.setAttribute("aria-hidden", "true");
}

document.getElementById("paperContent").addEventListener("click", (event) => {
  const term = event.target.closest(".term-button");
  if (term) showTermExplanation(term.dataset.term, term.textContent);
});

document.getElementById("paperContent").addEventListener("mouseup", () => {
  const selection = window.getSelection();
  const text = selection?.toString().trim();
  if (!text || text.length < 2 || text.length > 80 || !selection.anchorNode || !document.getElementById("paperContent").contains(selection.anchorNode)) return;
  showTermExplanation(glossaryKeyFor(text), text);
});

document.getElementById("selectionAssistantClose").addEventListener("click", closeSelectionAssistant);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") { closeDrawer(); closeSelectionAssistant(); }
});

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
    const scanButton = document.getElementById("scanNowButton");
    if (scanButton) scanButton.hidden = data.manual_scan_available === false;
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
      return `<a class="source-row monitor-link-row" href="${escapeHtml(source.index_url)}" target="_blank" rel="noopener" aria-label="打开 ${escapeHtml(source.name)} 官方入口"><span class="provider-badge">${escapeHtml(abbreviation)}</span><div><strong>${escapeHtml(source.provider)}</strong><small>${escapeHtml(source.name)} · ${escapeHtml(formatTime(source.last_checked_at))}</small></div><span class="source-status ${stateClass}">${escapeHtml(statusLabel(source.last_status))}</span></a>`;
    }).join("") : '<div class="empty-monitor">尚未配置来源</div>';
    const reportTable = document.getElementById("recentReportTable");
    reportTable.innerHTML = data.recent_reports?.length ? data.recent_reports.map((report) => `<a class="report-row monitor-link-row" href="${escapeHtml(report.url)}" target="_blank" rel="noopener" aria-label="打开 ${escapeHtml(report.title)} 官方原文"><div><strong>${escapeHtml(report.title)}</strong><small>${escapeHtml(report.provider)} · ${escapeHtml(report.page_count ? `${report.page_count} 页` : statusLabel(report.parse_status))}</small></div><span>${escapeHtml(report.report_type.replaceAll("_", " "))}</span></a>`).join("") : '<div class="empty-monitor">首次扫描后，新报告会出现在这里</div>';
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
