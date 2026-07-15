# FrontierLens Demo

**AI Frontier Intelligence Platform — AI 前沿技术情报平台。**

> See what changed. Understand why it matters.
> 看清变化，理解影响。

FrontierLens 将官方模型报告转化为有证据的技术认知。本 Demo 聚焦于“用 15 分钟理解一次 AI 模型发布”。

## 体验内容

- 发布速览：这次更新了什么、为什么重要、是否值得读
- 概念解释：点击四个核心变化，30 秒建立直觉
- Tech Report：保留完整阅读入口，并提供可隐藏的 FrontierLens 解读
- 证据库：Tech Report 第一优先，Blog、Benchmark、GitHub、Safety Report 分工补充

## 打开方式

### 完整模式：前端、API 和自动监控

```bash
python3 -m pip install -r requirements.txt
python3 run.py init
python3 run.py serve
```

浏览器打开 `http://127.0.0.1:4173`。服务运行期间，每 3600 秒自动扫描一次官方来源。

常用命令：

```bash
# 只发现候选，不下载文件
python3 run.py scan --no-download

# 扫描单个来源，并限制本轮最多下载 1 份文件
python3 run.py scan --source qwen-official-report --max-downloads 1

# 单独解析本地 PDF
python3 run.py parse /path/to/report.pdf --output report.json

# 修改自动扫描间隔，例如 10 分钟
python3 run.py serve --interval 600
```

### 纯静态 Demo

直接打开 `index.html` 仍可体验原有页面；来源监控和真实数据 API 需要使用完整模式。

## 当前底层能力

- 官方来源注册表与域名、路径白名单
- 条件请求和每小时定时检查
- Tech Report、System Card、Model Card 候选识别
- 原始文件 SHA-256 去重与归档
- PDF 页码、正文及顶层章节结构化解析
- SQLite 扫描历史和报告元数据
- 本地监控 API 与可视化状态页

详细设计见 [`docs/architecture.md`](docs/architecture.md)。

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

> Aster 1 及页面中的报告内容均为产品演示数据，不代表真实模型或真实研究结论。
