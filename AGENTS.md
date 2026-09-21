# AskBot — 自动微信/QQ客服项目骨架

> 工作目录: `C:\Project\Ask` | 语言: Python 3.11+ | 入口: `src/askbot`

## 1. 这是什么

自动微信/QQ客服机器人,核心链路:

```
WeChat (WeChatFerry/wxauto) ─┐
                             ├─> Adapter(统一 MessageEvent) ─> Router(意图/关键词/LLM) ─> ReplyEngine ─> Adapter.send
QQ (NapCat/OneBot11 webhook) ┘              │                         │                        │
                                     SessionManager              KnowledgeBase              Guardrails(风控/合规/限流)
                                                                              └─> LLM (OpenAI兼容接口)
```

设计目标: 平台适配与业务逻辑解耦,新增平台只写 Adapter,不改 Core。

## 2. 目录结构(已初始化)

```
C:\Project\Ask/
├─ AGENTS.md                # 本文件,Agent 工作守则
├─ README.md
├─ pyproject.toml           # 构建/依赖/工具配置(唯一依赖声明源)
├─ requirements.txt         # pip install -r 用,由 pyproject 导出,保持同步
├─ .env.example
├─ .gitignore
├─ config/
│  └─ config.example.yaml
├─ src/askbot/
│  ├─ __init__.py           # version
│  ├─ __main__.py           # python -m askbot
│  ├─ config.py             # YAML+ENV 加载,全局 Settings
│  ├─ cli.py                # CLI: serve / doctor / send-test
│  ├─ app.py                # FastAPI: /healthz, /webhook/onebot, /webhook/wechat
│  ├─ core/
│  │  ├─ router.py          # 关键词路由 + LLM fallback
│  │  ├─ session.py         # 会话管理(内存+TTL,可换 Redis)
│  │  ├─ reply_engine.py    # 编排: session→router→knowledge→llm→guardrails
│  │  ├─ knowledge.py       # 本地 FAQ/知识库接口( stub )
│  │  └─ guardrails.py      # 限流/敏感词/长度截断
│  ├─ adapters/
│  │  ├─ base.py            # MessageEvent / Adapter 抽象,所有适配器必须实现
│  │  ├─ wechat.py          # WeChatFerry 占位实现(未装依赖时降级)
│  │  └─ qq.py              # OneBot11(NapCat) 发送+webhook 解析
│  ├─ llm/
│  │  ├─ base.py            # LLMClient Protocol
│  │  └─ openai_compat.py   # OpenAI兼容实现(DeepSeek/Qwen/OpenAI均可)
│  └─ infra/
│     ├─ logger.py          # loguru 统一日志
│     └─ db.py              # sqlite 会话持久化占位
├─ tests/
│  ├─ test_router.py
│  └─ test_session.py
└─ scripts/
   └─ dev_run.ps1
```

## 3. 快速开始(Windows PowerShell)

```powershell
cd C:\Project\Ask
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
copy config\config.example.yaml config\config.yaml
python -m askbot doctor      # 自检配置与依赖
python -m askbot serve       # 启动 FastAPI :8000
pytest -q                    # 跑测试
```

`serve` 启动后:

- `GET /healthz` 健康检查
- `POST /webhook/onebot` QQ(NapCat OneBot11)回调
- `POST /webhook/wechat` 微信回调(WeChatFerry 主动推)

## 4. 配置规范

- 敏感信息只放 `.env`,不进 git,不写死代码。`config.yaml` 只放非敏感结构化配置。
- `src/askbot/config.py:Settings` 是唯一配置入口,新增配置项必须:
  1. 加字段(带默认值)+类型注解,
  2. 同步 `.env.example` 和 `config/config.example.yaml`,
  3. 在 `doctor` 里加校验。
- LLM 接入 OpenAI 兼容接口:`LLM_BASE_URL / LLM_API_KEY / LLM_MODEL`。

## 5. 代码规范(Agent 必须遵守)

1. **先读后改**: 动 `src/askbot` 前先 `read` 相关文件,不凭空推测接口。
2. **Adapter 隔离**: 平台相关代码只允许在 `adapters/`,禁止在 `core/` 里 `import wechat/qq` 相关库。跨平台消息必须用 `adapters/base.py:MessageEvent`。
3. **Core 无 I/O 副作用**: `router/session/guardrails` 保持纯函数可测试,网络/DB 调用下沉到 `adapters/infra/llm`。
4. **类型+日志**: 新增公开函数必须有类型注解;关键链路用 `loguru` 打 info,异常打 exception,不用 `print`。
5. **最小 diff**: 优先改现有文件,不随意新建;新建文件必须同步更新本 AGENTS.md §2 结构树。
6. **依赖管理**: 只改 `pyproject.toml`,然后 `pip freeze` 思路同步 `requirements.txt`,不手动加第三方库不用就删。
7. **验证**: 涉及 `core/` 改动必须跑 `pytest -q`;涉及 `app/cli/config` 改动必须跑 `python -m askbot doctor`。

## 6. Adapter 实现契约

`adapters/base.py`:

```python
@dataclass MessageEvent: platform, user_id, group_id|None, text, msg_id, ts, raw
class Adapter(ABC):
  platform: str
  async start() -> None
  async stop() -> None
  async send(target_id: str, text: str, group_id: str|None) -> bool
  def parse_webhook(payload: dict) -> MessageEvent | None
```

- `wechat.py`: 默认 `WeChatFerry` 模式,未安装 `wcferry` 时 `available()=False`,走日志降级,不抛异常阻断启动。
- `qq.py`: 对接 NapCat OneBot11,出站 `POST {ONEBOT_HTTP_URL}/send_msg`,入站解析 `message/post_type`。
- 新增平台(如企业微信): 在 `adapters/` 新建文件实现上式 4 件套,并在 `app.py` 注册 webhook 路由。

## 7. 当前 Stub 与下一步(TODO)

- [x] 骨架/路由/会话/护栏/OneBot webhook/doctor/cli
- [ ] `llm/openai_compat.py` 当前 echo stub,下一步接真实 `httpx` 调用
- [ ] `core/knowledge.py` 当前内存 FAQ,下一步接向量检索(RAG)
- [ ] `infra/db.py` 当前 sqlite 占位,下一步接会话持久化
- [ ] `adapters/wechat.py` 接真实 WeChatFerry 登录+消息拉取
- [ ] 风控: QQ/微信防封(频率限制、人工接管关键词、夜间免打扰)

## 8. 风控与合规红线

- 微信/QQ 自动化有封号风险: 默认开启 `guardrails` 限流(单用户 10s 内 ≤3 条),群聊默认只 @回复。
- 不存储用户原始敏感信息(身份证/密码),日志脱敏。
- 人工接管: 用户发"转人工"直接短路,不再自动回复(见 `router.py:KEYWORD_ROUTES`)。

## 9. 常用命令速查

```powershell
python -m askbot doctor                 # 配置自检
python -m askbot serve --port 8000      # 启动服务
python -m askbot send-test --platform qq --target 123 --text hi  # 发送链路自测(日志模式)
pytest -q                               # 全量测试
```

## 10. Agent 工作流建议

- 接到需求先定位: 平台问题→`adapters/`,回复策略→`core/router.py + reply_engine.py`,模型问题→`llm/`,部署→`config.py/app.py`。
- 大改前用 `subagent:explore` 并行摸底,不把大文件全文塞上下文。
- 改完必须执行 §5.7 验证,失败不提交结论。
