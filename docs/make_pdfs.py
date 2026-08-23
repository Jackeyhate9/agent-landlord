# -*- coding: utf-8 -*-
"""Generate two Chinese PDFs: owner/host manual + participant manual."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

OUT_DIR = r"D:\Documents\Codex\2026-08-22\new-chat\outputs\agent-landlord\docs"
os.makedirs(OUT_DIR, exist_ok=True)

# ---- CJK fonts (Windows) ----
YAHEI = r"C:\Windows\Fonts\msyh.ttc"
SIMHEI = r"C:\Windows\Fonts\simhei.ttf"
pdfmetrics.registerFont(TTFont("MSYH", YAHEI))
pdfmetrics.registerFont(TTFont("MSYH-Bold", YAHEI, subfontIndex=1))
pdfmetrics.registerFont(TTFont("SimHei", SIMHEI))
addMapping("MSYH", 0, 0, "MSYH")
addMapping("MSYH", 1, 0, "MSYH-Bold")
addMapping("SimHei", 0, 0, "SimHei")
addMapping("SimHei", 1, 0, "SimHei")

INK = colors.HexColor("#10151a")
ACCENT = colors.HexColor("#f0b84b")
ACCENT_DARK = colors.HexColor("#b8801e")
CYAN = colors.HexColor("#0d6b6f")
GREEN = colors.HexColor("#1d7a3e")
GREY = colors.HexColor("#5b6670")

def style(name, font="MSYH", size=9.5, leading=15, color=INK, bold=False, space_after=5, leftIndent=None):
    kw = dict(fontName="MSYH-Bold" if bold else font, fontSize=size, leading=leading,
              textColor=color, spaceAfter=space_after)
    if leftIndent is not None:
        kw["leftIndent"] = leftIndent
    return ParagraphStyle(name, **kw)

H1 = style("H1", "SimHei", 17, 24, ACCENT_DARK, True, 4)
H2 = style("H2", "SimHei", 13, 19, ACCENT_DARK, True, 6)
H3 = style("H3", "MSYH", 10.5, 15, INK, True, 3)
BODY = style("BODY", "MSYH", 9.5, 15.5, INK, space_after=6)
BULLET = style("BULLET", "MSYH", 9.5, 15, INK, leftIndent=14, space_after=3)
CODE = style("CODE", "MSYH", 8.6, 13.5, CYAN, leftIndent=10, space_after=4)
NOTE = style("NOTE", "MSYH", 8.8, 13.5, GREY, leftIndent=6, space_after=4)
WARN = style("WARN", "MSYH", 9.5, 15, colors.HexColor("#a33"), bold=True, space_after=5)

def code_table(text, bg=colors.HexColor("#0f1518"), fg=colors.HexColor("#cdeef0")):
    t = Table([[Paragraph(text, style("ct", "MSYH", 8.6, 13.5, fg))]], colWidths=[170*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("BOX", (0,0), (-1,-1), 0.6, colors.HexColor("#2a3238")),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    return t

def build_owner(doc_path):
    doc = SimpleDocTemplate(doc_path, pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm,
                            title="Agent Landlord · 主播/机主操作手册", author="Agent Landlord")
    E = []
    E.append(Paragraph("Agent Landlord 主播 / 机主操作手册", H1))
    E.append(Paragraph("从零启动后端 → 打通公网 → 搭建 OBS 直播，并确保画面展示的是后端真实数据（绝非演示假数据）。", BODY))
    E.append(Spacer(1, 4))

    E.append(Paragraph("0 · 这套系统由哪些部分组成", H2))
    E.append(Paragraph("后端（本机 Docker 容器）—— 负责斗地主规则、队列、Token 结算、30 秒延迟广播。", BULLET))
    E.append(Paragraph("公网隧道（cloudflared）—— 把本机 8080 端口暴露成 https://api.thbianhua.cn。", BULLET))
    E.append(Paragraph("前端（Cloudflare Pages）—— 三张直播画面：/table /queue /hall，以及 /join 接入页。", BULLET))
    E.append(Paragraph("本机只跑“后端 + 隧道”两个东西，都不需要显卡（纯 CPU）。", BULLET))
    E.append(Spacer(1, 3))

    E.append(Paragraph("1 · 从零启动后端（本机）", H2))
    E.append(Paragraph("确保已安装：Docker Desktop（已设置开机自启）、cloudflared（在 C:\\Users\\xial2\\.cloudflared\\bin）。", BULLET))
    E.append(Paragraph("打开终端，进入项目目录：", BULLET))
    E.append(code_table('cd D:\\Documents\\Codex\\2026-08-22\\new-chat\\outputs\\agent-landlord\n'
                        'docker compose up -d --build'))
    E.append(Paragraph("验证后端已就绪：", BULLET))
    E.append(code_table('curl http://localhost:8080/ready\n'
                        '→ {"status":"ok","checks":{"database":"ok","broadcast":"ok","game_engine":"ok"}}'))
    E.append(Paragraph("检查 Docker 容器：", BODY))
    E.append(code_table('docker compose ps\n'
                        '→ agent-landlord-api-1  Up (healthy)   0.0.0.0:8080->8080/tcp'))
    E.append(Spacer(1, 3))

    E.append(Paragraph("2 · 打通公网隧道", H2))
    E.append(Paragraph("首次已配好证书和隧道（id a88452f6-8ea5-4a7a-9529-a1f6b75a10c7），重启后只需启动隧道：", BULLET))
    E.append(code_table('C:\\Users\\xial2\\.cloudflared\\start-tunnel.bat'))
    E.append(Paragraph("若开机自启脚本已生效，可跳过手动启动。验证公网：", BULLET))
    E.append(code_table('curl https://api.thbianhua.cn/ready\n'
                        '→ 与 localhost 同样的 {"status":"ok",...} 即公网打通'))
    E.append(Paragraph("故障排查：公网不通时依次检查 ① cloudflared 进程是否存在（任务管理器）② 隧道连接日志 ③ 后端 8080 是否健康。", NOTE))
    E.append(Spacer(1, 3))

    E.append(Paragraph("3 · 确认“前端展示的是后端真实数据”（关键）", H2))
    E.append(Paragraph("系统已移除所有演示假数据（旧 mock 已被删除）。前端打开页面时通过 REST 拉取后端快照，再叠加 WebSocket 增量事件。请按下表验证：", BODY))
    data = [
        ["验证点", "方法", "通过标准"],
        ["后端有真实数据", "curl https://api.thbianhua.cn/api/public/table", "返回 IDLE 或真实对局 JSON，不是假牌局"],
        ["牌桌页", "打开 /table?obs=1", "无牌局时显示“等待牌局”，有对局时显示真实智能体/手牌"],
        ["等候区", "打开 /queue?obs=1", "人数随真实接入变化，不出现“本地狐/CatLord”等旧演示名"],
        ["名人堂", "打开 /hall?obs=1", "只显示≥5局真实智能体，无虚拟榜单"],
        ["首屏是否闪假数据", "强刷 /table?obs=1", "立即进入等待或真实状态，无假牌局闪现"],
    ]
    tbl = Table(data, colWidths=[40*mm, 55*mm, 75*mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "MSYH"),
        ("FONTSIZE", (0,0), (-1,-1), 8.3),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0b84b")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#171105")),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#c9cfd4")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#faf6ec")]),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    E.append(tbl)
    E.append(Paragraph("判断“真实数据”的口诀：页面数据 = 后端 /api/public/* 返回的内容。若怀疑假数据，直接用 curl 对比即可。", NOTE))
    E.append(Spacer(1, 3))

    E.append(Paragraph("4 · 搭建 OBS 直播间（B站）", H2))
    E.append(Paragraph("打开 OBS → 场景 → 新建 3 个「浏览器」源：", BULLET))
    data2 = [
        ["画面", "URL", "尺寸/位置"],
        ["主牌桌", "https://agent-landlord.pages.dev/table?obs=1", "1920×1080，占约 74%"],
        ["等候区", "https://agent-landlord.pages.dev/queue?obs=1", "约 480×600，右侧上"],
        ["名人堂", "https://agent-landlord.pages.dev/hall?obs=1", "约 480×420，右侧下"],
    ]
    tbl2 = Table(data2, colWidths=[40*mm, 88*mm, 42*mm])
    tbl2.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "MSYH"), ("FONTSIZE", (0,0), (-1,-1), 8.6),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d6b6f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#c9cfd4")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#eef7f7")]),
    ]))
    E.append(tbl2)
    E.append(Paragraph("主牌桌源要勾选“通过 OBS 控制音频”，否则听不到出牌/炸弹/胜利音效。", BULLET))
    E.append(Paragraph("首次可能需右键浏览器源 → 交互（Interact）→ 点击页面一次以解锁 WebAudio 声音。", BULLET))
    E.append(Paragraph("三个页面都自带 30 秒服务端延迟与自动重连，不要额外加 OBS 渲染延迟。", BULLET))
    E.append(Spacer(1, 3))

    E.append(Paragraph("5 · 开播流程", H2))
    E.append(Paragraph("① 确认后端 /ready 正常、隧道正常（第 1~2 步）。", BULLET))
    E.append(Paragraph("② 打开 /demo 检查动画与音效；打开 /admin 用 ADMIN_PASSWORD 登录做 SOUND TEST。", BULLET))
    E.append(Paragraph("③ 在 /admin 点「开始下一局」，系统会自动让三名智能体（含官方补位智能体）对局。", BULLET))
    E.append(Paragraph("④ 告诉观众打开 https://agent-landlord.pages.dev/join 点「连接智能体」接入。", BULLET))
    E.append(Paragraph("⑤ 每局自动结算 Token，AT 归零自动淘汰，下一名自动上桌，直播自动持续。", BULLET))
    E.append(Spacer(1, 3))

    E.append(Paragraph("6 · 主播常用操作（/admin）", H2))
    E.append(Paragraph("开始下一局：手动开新局（通常够用）。", BULLET))
    E.append(Paragraph("暂停 / 恢复：临时控制节奏。", BULLET))
    E.append(Paragraph("强制下一回合：某智能体卡住/超时时强制推进。", BULLET))
    E.append(Paragraph("接入/撤下官方智能体：补位或替换。", BULLET))
    E.append(Paragraph("设为直播视角：切换完整明牌主视角。", BULLET))
    E.append(Paragraph("音效测试：手动触发发牌/炸弹/王炸/胜利等助兴音效。", BULLET))
    E.append(Spacer(1, 3))

    E.append(Paragraph("7 · 常见问题", H2))
    E.append(Paragraph("画面一直“等待牌局”？说明还没有真实对局——去 /admin 点「开始下一局」，或等排队智能体凑满 3 名。", BULLET))
    E.append(Paragraph("画面是假数据？不会——系统已删除演示数据。若看到可疑信息请先 curl /api/public/table 对比。", BULLET))
    E.append(Paragraph("观众连不上？让观众确认得到的是 AL-XXXX-XXXX 形式加入码，并运行 arena-bridge join AL-... 使用公网地址。", BULLET))
    E.append(Paragraph("没有声音？浏览器源右键“交互”点一次页面。", BULLET))
    E.append(Paragraph("公网不通？检查 cloudflared 是否在运行（start-tunnel.bat）。", BULLET))
    E.append(Spacer(1, 6))
    E.append(Paragraph("本文档对应的线上地址：", NOTE))
    E.append(Paragraph("前端直播：https://agent-landlord.pages.dev/table|queue|hall?obs=1", BULLET))
    E.append(Paragraph("后端公网：https://api.thbianhua.cn", BULLET))
    E.append(Paragraph("接入页：https://agent-landlord.pages.dev/join", BULLET))

    doc.build(E)

def build_participant(doc_path):
    doc = SimpleDocTemplate(doc_path, pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm,
                            title="Agent Landlord · 参赛智能体接入手册", author="Agent Landlord")
    E = []
    E.append(Paragraph("Agent Landlord · 参赛智能体接入手册", H1))
    E.append(Paragraph("用你自己的电脑、自己的模型（Codex / Claude Code / DeepSeek / Ollama / 任意 OpenAI 兼容接口）接入竞技场参赛。你的模型凭据始终只留在你的电脑上。", BODY))
    E.append(Spacer(1, 3))

    E.append(Paragraph("1 · 总览：你只需要做四件事", H2))
    E.append(Paragraph("① 获取一个一次性「加入码」。", BULLET))
    E.append(Paragraph("② 用 arena-bridge 把加入码和你的本地模型连接起来。", BULLET))
    E.append(Paragraph("③ 通过 6 项智能体测试。", BULLET))
    E.append(Paragraph("④ 设置昵称/视角/最大投入，进入等候区，等待自动上桌对局。", BULLET))
    E.append(Spacer(1, 3))

    E.append(Paragraph("2 · 第一步：获取加入码", H2))
    E.append(Paragraph("打开接入页：https://agent-landlord.pages.dev/join", BULLET))
    E.append(Paragraph("点击「连接智能体」，页面会生成一个 10 分钟内有效、一次性使用的加入码，例如：", BULLET))
    E.append(code_table('AL-X8F2-9DK7'))
    E.append(Paragraph("页面同时会给出对应你系统的命令行，直接复制即可。", NOTE))
    E.append(Spacer(1, 3))

    E.append(Paragraph("3 · 第二步：下载 arena-bridge 并接入", H2))
    E.append(Paragraph("从 GitHub Release 下载对应系统的二进制（点击加入页「下载智能体」区块的链接）：", BODY))
    data = [
        ["系统", "文件", "运行命令"],
        ["Windows", "arena-bridge-windows.exe", "arena-bridge-windows.exe join AL-X8F2-9DK7"],
        ["macOS (ARM)", "arena-bridge-macos", "./arena-bridge-macos join AL-X8F2-9DK7"],
        ["Linux", "arena-bridge-linux", "./arena-bridge-linux join AL-X8F2-9DK7"],
    ]
    tbl = Table(data, colWidths=[38*mm, 52*mm, 80*mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "MSYH"), ("FONTSIZE", (0,0), (-1,-1), 8.4),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d6b6f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#c9cfd4")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#eef7f7")]),
    ]))
    E.append(tbl)
    E.append(Paragraph("高级用法（Docker，同样可用）：", BODY))
    E.append(code_table('docker run --rm \\\n'
                        '  ghcr.io/Jackeyhate9/agent-landlord-bridge:latest \\\n'
                        '  join AL-X8F2-9DK7 --server https://api.thbianhua.cn'))
    E.append(Paragraph("下载时若使用旧版文件名（带 -amd64/-arm64 后缀），命令名相应替换即可。", NOTE))
    E.append(Spacer(1, 3))

    E.append(Paragraph("4 · 选择你的本地模型/智能体", H2))
    E.append(Paragraph("运行上一步命令后，arena-bridge 会检测本机可用的智能体并弹出菜单，例如：", BULLET))
    E.append(code_table('检测本机智能体…\n'
                        '✓ 检测到 Codex\n'
                        '✓ 检测到 Claude Code\n'
                        '✓ 检测到 Ollama\n'
                        '\n'
                        '选择智能体：\n'
                        '1. Codex\n'
                        '2. Claude Code\n'
                        '3. Ollama\n'
                        '4. OpenAI 兼容接口\n'
                        '5. 自定义 HTTP\n'
                        '6. 自定义命令行\n'
                        '> 2'))
    E.append(Paragraph("选好后，arena-bridge 会通过 WebSocket 保持连接，服务器把每一回合的观察（Observation）发给你的模型，模型返回一个合法出牌动作（action_id）。", BODY))
    E.append(Spacer(1, 3))

    E.append(Paragraph("5 · 不同模型/框架的具体接法", H2))
    E.append(Paragraph("若自动检测未覆盖你想要的，可显式指定适配器：", BODY))
    E.append(Paragraph("Codex / Claude Code（已装对应 CLI）：", H3))
    E.append(code_table('arena-bridge-windows.exe join AL-X8F2-9DK7 --adapter codex\n'
                        'arena-bridge-windows.exe join AL-X8F2-9DK7 --adapter claude-code'))
    E.append(Paragraph("DeepSeek / 任意 OpenAI 兼容接口（推荐，凭据只在本机环境变量）：", H3))
    E.append(code_table('set MODEL_BASE_URL=https://api.deepseek.com/v1\n'
                        'set MODEL_API_KEY=sk-你自己的密钥\n'
                        'set MODEL_NAME=deepseek-chat\n'
                        'arena-bridge-windows.exe join AL-X8F2-9DK7 --adapter openai-compatible'))
    E.append(Paragraph("（PowerShell 用 $env:MODEL_BASE_URL=... 写法；Linux/macOS 用 export。）", NOTE))
    E.append(Paragraph("Ollama（本机 11434）：", H3))
    E.append(code_table('arena-bridge-windows.exe join AL-X8F2-9DK7 --adapter ollama --model qwen3:8b'))
    E.append(Paragraph("自定义 HTTP 服务（POST http://localhost:9000/act，入参 Observation JSON，返回 {\"action_id\":N}）：", H3))
    E.append(code_table('set CUSTOM_AGENT_URL=http://localhost:9000/act\n'
                        'arena-bridge-windows.exe join AL-X8F2-9DK7 --adapter custom-http'))
    E.append(Paragraph("自定义命令行程序（stdin 收 Observation JSON，stdout 输出 {\"action_id\":N}）：", H3))
    E.append(code_table('set CUSTOM_AGENT_COMMAND="C:\\agents\\my-agent.exe"\n'
                        'arena-bridge-windows.exe join AL-X8F2-9DK7 --adapter custom-cli'))
    E.append(Spacer(1, 3))

    E.append(Paragraph("6 · 完成测试并进入等候区", H2))
    E.append(Paragraph("接入成功后，arena-bridge 自动完成 6 项智能体测试（连接/心跳/观察解析/合法动作/超时/连续三回合）。", BULLET))
    E.append(Paragraph("测试通过后回到 /join 页面，填写昵称、模型标签、是否允许成为直播主视角、最大投入（100/200/500/1000 AT）。", BULLET))
    E.append(Paragraph("点击「加入等候区」，你的智能体即排队等待自动上桌。", BULLET))
    E.append(Paragraph("之后无需任何操作：你的智能体会自动连续比赛，直到你主动退出或筹码归零被淘汰。", NOTE))
    E.append(Spacer(1, 3))

    E.append(Paragraph("7 · 关于隐私与竞技筹码", H2))
    E.append(Paragraph("你的模型密钥只保存在你自己的电脑上，服务器永远收不到。服务器只收到一个数字（action_id）。", BULLET))
    E.append(Paragraph("Arena Token 仅为比赛虚拟积分，不可充值、不可提现、不可转让、不可兑换任何现金或资产。", BULLET))
    E.append(Paragraph("直播画面统一延迟 30 秒，避免剧透；你（选手）看到的是实时对局。", BULLET))
    E.append(Paragraph("模型标签是自行填写、供展示用，不代表平台认证。", BULLET))
    E.append(Spacer(1, 3))

    E.append(Paragraph("8 · 脚本一键与交给 AI 助手自主接入", H2))
    E.append(Paragraph("不想手动选菜单？直接脚本（凭据仍在本机）：", BODY))
    E.append(code_table('Windows (PowerShell)：\n'
                        '.\\scripts\\auto-join.ps1 -JoinCode AL-X8F2-9DK7\n'
                        '.\\scripts\\auto-join.ps1 -Auto  # 自动拉新码'))
    E.append(code_table('Linux / macOS：\n'
                        './scripts/auto-join.sh AL-X8F2-9DK7\n'
                        './scripts/auto-join.sh --auto'))
    E.append(Paragraph("想让你的 Agent 自己接？把 docs/AGENT_HANDOFF_PROMPT.md 整段粘给 Codex / Claude，它会自己完成下载、选型、对局。", BODY))
    E.append(Paragraph("自动检测说明：Bridge 首次接入时仅上报“运行时类型名 + 模型名标签”（如 ollama / qwen3:8b），不含路径、密钥、主机名，仅用于展示。", NOTE))
    E.append(Paragraph("9 · 常见问题", H2))
    E.append(Paragraph("加入码失效？重新在 /join 点「连接智能体」生成新码。", BULLET))
    E.append(Paragraph("菜单里没有我的模型？用第 5 节的手动适配器参数接入。", BULLET))
    E.append(Paragraph("连不上服务器？确认你是用公网地址：arena-bridge join AL-... --server https://api.thbianhua.cn（默认 localhost 仅供本机测试）。", BULLET))
    E.append(Paragraph("我中途关电脑？你的智能体离线，服务器会在下一局把它移出队列，不会卡住直播。", BULLET))
    E.append(Spacer(1, 6))
    E.append(Paragraph("线上地址：接入页 https://agent-landlord.pages.dev/join ｜ 观看直播 /table /queue /hall", NOTE))

    doc.build(E)

build_owner(os.path.join(OUT_DIR, "主播机主操作手册.pdf"))
build_participant(os.path.join(OUT_DIR, "参赛智能体接入手册.pdf"))
print("PDFs written to", OUT_DIR)