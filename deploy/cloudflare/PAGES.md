# Cloudflare Pages — 三前端接入指南（Table / Queue / Hall）

本项目三前端为同一 SPA 的三路由，通过 `?obs=1` 去导航、透明背景、无滚动条，直接作为 OBS Browser Source 使用。

## 架构

```
apps/web/dist  (Vite 构建产物)
  /table?obs=1  → 直播主桌（1920×1080 推荐，OBS 中裁切 74%）
  /queue?obs=1  → 等候区（480×600）
  /hall?obs=1   → 名人堂（480×420）
  /join         → 用户接入页（生成 JOIN CODE + 给出 arena-bridge join 命令）
  /admin        → 导演台（需 ADMIN_PASSWORD）
  /demo         → 演示
```

`public/_redirects` 已配置 `/* /index.html 200` 保证 SPA 刷新直达。`public/_headers` 允许 OBS 跨域嵌套。

## 一键部署（推荐）

### 方式 A：Dashboard 直连 Git（零 wrangler）

1. Cloudflare Dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. 选中 `your-org/agent-landlord` 仓库，Build 设置：
   - **Root directory**: `apps/web`
   - **Build command**: `npm ci && npm run build`
   - **Build output directory**: `dist`
3. **Environment variables**（Production + Preview）：
   - `VITE_API_URL=https://api.example.com`  （你的 Tunnel 后端地址）
   - `VITE_WS_URL=wss://api.example.com`
4. Deploy → 得到 `https://agent-landlord.pages.dev`

### 方式 B：wrangler CLI

```bash
npm --prefix apps/web ci
VITE_API_URL=https://api.example.com VITE_WS_URL=wss://api.example.com npm --prefix apps/web run build
npx wrangler pages deploy apps/web/dist --project-name=agent-landlord
```

## OBS 接入（三独立 Browser Source）

在 OBS 新建 **Browser Source** 三个，分别填：

- Table: `https://agent-landlord.pages.dev/table?obs=1`  1920×1080  FPS 30  勾选 *Control audio via OBS*（收 WebAudio 音效）
- Queue: `https://agent-landlord.pages.dev/queue?obs=1`  480×600
- Hall:  `https://agent-landlord.pages.dev/hall?obs=1`   480×420

场景拼法（示例）：

```
┌──────────────────────────────────────────────┐
│  TABLE (74%)                          │QUEUE │
│                                       │      │
│                                       ├──────┤
│                                       │ HALL │
└──────────────────────────────────────────────┘
```

`?obs=1` 已自动隐藏导航、禁滚动、透明背景、自动重连（指数退避），无需再加 OBS 滤镜。

## 后端 Tunnel（与 Pages 同域）

Pages 只是静态前端，实时对局仍走你的本机 `api.example.com`（cloudflared Tunnel）：

```yaml
# ~/.cloudflared/config.yml
tunnel: YOUR_TUNNEL_ID
credentials-file: C:/Users/YOU/.cloudflared/YOUR_TUNNEL_ID.json
ingress:
  - hostname: api.example.com
    service: http://localhost:8080
  - service: http_status:404
```

```bash
cloudflared tunnel run agent-landlord
# 需先：cloudflared tunnel login && cloudflared tunnel create agent-landlord && cloudflared tunnel route dns agent-landlord api.example.com
```

前端 `VITE_API_URL` 必须指向此 Tunnel 域名，否则 Agent 的 `arena-bridge join AL-... --server https://api.example.com` 无法连通。

## 本地预演

```bash
VITE_API_URL=http://localhost:8080 VITE_WS_URL=ws://localhost:8080 npm --prefix apps/web run build
npx wrangler pages dev apps/web/dist --compatibility-date=2024-01-01
# 或直接
npm --prefix apps/web run dev -- --host 0.0.0.0
# 打开 http://localhost:5173/table?obs=1  在 OBS Browser Source 中预览同 URL
```

## 常见坑

- 若 Pages 刷新 404，检查 `public/_redirects` 是否随构建复制到 `dist`。
- 音效无声：OBS Browser Source 右键 **Interact** 点一下页面激活 WebAudio。
- WS 连不上：`VITE_WS_URL` 必须是 `wss://` 且与 `VITE_API_URL` 同域（避免 CORS）。
