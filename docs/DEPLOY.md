# 部署对接指南(QQ=NapCat,微信=WeChatFerry)

## 1. QQ(NapCat OneBot11)

1. 在本机装 NapCatQQ(跟随 QQ NT),开启网络配置 → HTTP 服务器,记下端口(默认 3000)。
2. 同页配置 HTTP 上报(Post),地址填 `http://127.0.0.1:8000/webhook/onebot`,事件勾消息。
3. `.env` 配 `ONEBOT_HTTP_URL=http://127.0.0.1:3000`(有鉴权再配 `ONEBOT_ACCESS_TOKEN`)。
4. `python -m askbot serve` 后用小号私聊测试,看服务端日志 `QQ send` 是否成功。

go-cqhttp 已归档不再采用;以后上 Linux 服务器可换 Lagrange(OneBot 协议兼容,本项目不用改代码)。

## 2. 微信(个人号三条路均堵死,2026-09 本机实测结论)

❌ WeChatFerry: `wcferry==39.5.2`+微信`3.9.12.51`都装好(SHA256 与官方一致),
但服务端拒绝登录("当前微信版本过低,请升级至最新版本"),仓库已归档,此路终结。
❌ UI 自动化(wxauto 全系):4.x 主窗口是 Qt 自绘,整个窗口只暴露 2 个 UIA 节点
(`Qt51514QWindowIcon`+`MMUIRenderSubWindowHW`),任何 UI 自动化都是瞎子;
原 `wxauto` 已从 PyPI 下架,`wxauto4/wxautox4` 内嵌 MinGW pyd 本机加载失败。
❌ GeWeChat:官方已归档停服,无可用服务端(另有打击违规获取微信数据的合规背景)。
→ 微信个人号如需继续,只剩付费云 API(自行评估合规/成本/封号风险)或转企业微信
官方机器人(另一套方案,待立项)。在决策前,默认只跑 QQ 通道(`WECHAT_MODE=log`)。

## 3. 上线前检查

```powershell
python -m askbot doctor
python -m askbot send-test --platform qq --target 123 --text "退货怎么走"
pytest -q
```

- 微信/QQ 防封:群聊默认只回 @消息(`group_only_on_at`),单用户 10s 内超 3 条自动限流。
- 不要用大号长期挂机,新号先小流量试水;被限制登录立即停机转人工。
