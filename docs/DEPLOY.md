# 部署对接指南(QQ=NapCat,微信=WeChatFerry)

## 1. QQ(NapCat OneBot11)

1. 在本机装 NapCatQQ(跟随 QQ NT),开启网络配置 → HTTP 服务器,记下端口(默认 3000)。
2. 同页配置 HTTP 上报(Post),地址填 `http://127.0.0.1:8000/webhook/onebot`,事件勾消息。
3. `.env` 配 `ONEBOT_HTTP_URL=http://127.0.0.1:3000`(有鉴权再配 `ONEBOT_ACCESS_TOKEN`)。
4. `python -m askbot serve` 后用小号私聊测试,看服务端日志 `QQ send` 是否成功。

go-cqhttp 已归档不再采用;以后上 Linux 服务器可换 Lagrange(OneBot 协议兼容,本项目不用改代码)。

## 2. 微信(WeChatFerry 主 + wxauto 降级)

版本锁定(已验证): `wcferry==39.5.2` 配微信 `3.9.12.51`,安装包取自官方
Release(`WeChatFerry v39.5.2` 自带 `WeChatSetup-3.9.12.51.exe`),
SHA256=`86593666b6a81a742435879db25c2575a9f8967b877968c91aaa8a68b5f21af4`。

1. `pip install "wcferry==39.5.2"`,装 3.9.12.51 版微信(别装 4.x)。
2. `.env` 配 `WECHAT_MODE=ferry`,跑 `python -m askbot listen` 轮询收发。
3. 无 Ferry 环境时 `WECHAT_MODE=wxauto`(需微信窗口前台,仅发送稳定)或 `log`(纯日志联调)。

## 3. 上线前检查

```powershell
python -m askbot doctor
python -m askbot send-test --platform qq --target 123 --text "退货怎么走"
pytest -q
```

- 微信/QQ 防封:群聊默认只回 @消息(`group_only_on_at`),单用户 10s 内超 3 条自动限流。
- 不要用大号长期挂机,新号先小流量试水;被限制登录立即停机转人工。
