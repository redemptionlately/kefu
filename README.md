# AskBot 自动微信/QQ客服
见 AGENTS.md。快速开始:

```powershell
pip install -r requirements.txt
copy .env.example .env
copy config\config.example.yaml config\config.yaml
python -m askbot doctor
python -m askbot serve
```

架构见 `AGENTS.md §1`,接口契约见 `src/askbot/adapters/base.py`。
