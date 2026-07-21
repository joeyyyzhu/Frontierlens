# FrontierLens 最小生产环境

这套部署面向产品验证期：一台服务器、一个网页服务、一个后台监控 Worker，以及一个持久化数据卷。它已经适合邀请真实用户使用，但还不是无限扩容架构。

## 运行结构

```text
Browser
  └─ HTTPS reverse proxy
       └─ FrontierLens web (UI + API)

FrontierLens worker
  └─ hourly official-source scan

web + worker
  └─ shared persistent volume
       ├─ SQLite metadata (WAL mode)
       ├─ original PDFs
       └─ parsed JSON
```

网页服务不负责定时扫描。这样重启网页或增加请求线程时，不会重复启动抓取任务。手动扫描接口在生产环境中由管理员密钥保护。

## 第一次部署

1. 准备一台安装了 Docker 和 Docker Compose 的服务器。
2. 将 `.env.example` 复制为 `.env`。
3. 生成管理员密钥，例如 `openssl rand -hex 32`，填入 `FRONTIERLENS_ADMIN_TOKEN`。
4. 如需在线 AI 辅助阅读，填写服务端 `FRONTIERLENS_AI_API_KEY`。密钥绝不能放进 `app.js` 或提交到 Git。
5. 将 `FRONTIERLENS_PUBLIC_BASE_URL` 改成正式 HTTPS 域名。
6. 运行 `docker compose up -d --build`。
7. 检查 `/api/health` 与 `/api/ready` 都返回正常状态。

建议使用 Caddy、Nginx 或云平台负载均衡器终止 HTTPS，再转发到容器的 `4173` 端口。

## 数据与备份

`frontierlens-data` 是必须持久化和备份的数据卷。备份至少应包含：

- `frontierlens.db`
- `frontierlens.db-wal`（在线备份时）
- `raw/`
- `parsed/`
- `snapshots/`

恢复时应同时恢复数据库和文件目录，避免元数据指向不存在的原文。

## 当前安全边界

- 用户首次访问会获得随机设备身份和访问令牌；不同设备不能读取彼此的追踪偏好。
- AI API Key 只保存在服务端环境变量中。
- AI 回答的上下文由服务端从已解析报告中读取，客户端不能伪造原文。
- AI 阅读接口每个设备每分钟最多调用 20 次。
- PDF 支持 Range 请求，浏览器无需一次性下载完整文件。
- 来源使用 HTTPS 域名白名单，重定向后再次校验。

## 扩容边界

当前 SQLite + 本地文件卷适合单机验证。出现以下任一情况时，应升级为 PostgreSQL + 对象存储，并使用任务队列：

- 需要在多台服务器上水平扩容；
- 日活达到数千并产生大量 AI 阅读请求；
- 报告原文达到数十 GB；
- 需要正式账号登录、团队空间和跨设备同步；
- 需要对解析、嵌入和 AI 提炼任务做失败重试与优先级调度。

## 上线前检查

- `.env` 未被 Git 跟踪。
- 生产环境管理员密钥不少于 24 个字符。
- AI Key 只存在于服务端。
- 数据卷已设置自动备份。
- 域名启用 HTTPS。
- Worker 最近一次扫描成功。
- 随机抽查至少三份 PDF 的页码、原文和来源链接。
