# AskBot 自动微信/QQ客服
见 AGENTS.md。快速开始:

```powershell
pip install -r requirements.txt
copy .env.example .env
copy config\config.example.yaml config\config.yaml
python -m askbot doctor
python -m askbot serve
```

架构见 `AGENTS.md §1`,接口契约与选型见 `AGENTS.md §6`(QQ=NapCat OneBot11,微信=WeChatFerry主+wxauto降级)。

平台接入:
- QQ: 装 NapCatQQ,配 OneBot HTTP 服务(`ONEBOT_HTTP_URL`),上报地址指到 `POST /webhook/onebot`
- 微信: `WECHAT_MODE=ferry` 需对应版本微信+`wcferry`;无环境时 `wxauto`/`log` 降级联调
