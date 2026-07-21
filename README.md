# FrontierLens

**AI Frontier Intelligence Platform — AI 前沿技术情报平台。**

> See what changed. Understand why it matters.
> 看清变化，理解影响。

FrontierLens 将官方模型报告转化为有证据的技术认知，聚焦于“让 AI 产品经理用 15 分钟理解一次模型发布”。

产品不是论文聚合器，也不是通用 AI 新闻站。它以“模型发布”为工作对象，以 Tech Report
为主证据，把变化、概念、技术关系与产品影响组织成一条可核验的理解路径。

## 体验内容

- 发布速览：这次更新了什么、为什么重要、是否值得读
- 概念解释：点击四个核心变化，30 秒建立直觉
- Tech Report：保留完整阅读入口，并提供可隐藏的 FrontierLens 解读
- 证据库：Tech Report 第一优先，Blog、Benchmark、GitHub、Safety Report 分工补充
- 技术认知地图：把一次发布连接到概念、前置知识、相关技术和原文页码

## 打开方式

### 完整模式：前端、API 和自动监控

```bash
python3 -m pip install -r requirements.txt
python3 run.py init
python3 run.py serve
```

浏览器打开 `http://127.0.0.1:4173`。服务启动后会立即扫描一次官方来源，之后每 300 秒自动检查新报告。

常用命令：

```bash
# 只发现候选，不下载文件
python3 run.py scan --no-download

# 扫描单个来源，并限制本轮最多下载 1 份文件
python3 run.py scan --source qwen-official-report --max-downloads 1

# 单独解析本地 PDF
python3 run.py parse /path/to/report.pdf --output report.json

# 修改自动扫描间隔，例如 5 分钟（默认值）
python3 run.py serve --interval 300
```

### 纯静态 Demo

直接打开 `index.html` 仍可体验原有页面；来源监控和真实数据 API 需要使用完整模式。

## 当前可用能力

- 官方来源注册表与域名、路径白名单
- 条件请求和每 5 分钟定时检查
- Tech Report、System Card、Model Card 候选识别
- 原始文件 SHA-256 去重与归档
- PDF 页码、正文及顶层章节结构化解析
- SQLite 扫描历史和报告元数据
- 本地监控 API 与可视化状态页
- 用户追踪偏好 API（模型家族与官方数据源）
- 根据用户偏好筛选的个性化发布 Feed
- Feed 关键词检索和证据类型筛选
- 自定义模型与待验证的 HTTPS 官方来源
- 安全的匿名设备身份与用户偏好隔离
- 模型家族 → 发布 → 多份证据的归档层级
- 基于官方原文的在线 AI 提炼、翻译与划词解释（配置 API Key 后启用）
- 独立定时 Worker、生产健康检查与 PDF Range 请求
- Docker Compose 单机生产部署
- 规范概念、类型关系、发布上下文与页码证据组成的知识图谱
- 报告划词可继续进入同一个规范概念，不再生成孤立名词解释

详细设计见 [`docs/architecture.md`](docs/architecture.md)。

## 生产部署

生产环境使用两个进程：网页/API 服务与独立官方来源监控 Worker。复制 `.env.example` 为 `.env`，填写管理员密钥与可选 AI API Key，然后运行：

```bash
docker compose up -d --build
```

完整部署、安全边界、备份与扩容说明见 [`docs/production.md`](docs/production.md)。

## Git 工作方式

本项目使用 `main` 保存稳定版本。开始新功能时创建短分支：

```bash
git switch -c feature/report-parser
```

开发过程中经常查看变化：

```bash
git status
git diff
```

完成一个可独立说明的改动后提交：

```bash
git add backend tests README.md
git commit -m "feat: parse official model reports"
```

确认无误后合并回 `main`：

```bash
git switch main
git merge feature/report-parser
```

不要提交 `data/` 中下载的报告、SQLite 数据库或临时渲染文件；这些已写入 `.gitignore`。

当前产品页已接入 Qwen3 官方 Tech Report：原始 PDF、章节、页码和正文均来自本地保存的官方文件。FrontierLens 的中文速览与概念解释属于“理解层”，原始事实仍以官方报告为准。
