#!/usr/bin/env python3
"""
De-AI Writer Engine — 写作引擎核心
====================================
LLM 调用 + 配置加载 + 提示词构建（供 writer.py 各子命令复用）

配置（优先级：环境变量 > ~/.deai_writer.conf > 默认值）:
  LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
"""
import os, json, sys, configparser, urllib.request

DEFAULT_CONF = os.path.expanduser("~/.deai_writer.conf")

def load_config():
    """返回 {key, base_url, model}"""
    cfg = {"key": None, "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"}
    # 1. 配置文件
    if os.path.exists(DEFAULT_CONF):
        try:
            c = configparser.ConfigParser()
            c.read(DEFAULT_CONF)
            if c.has_section("llm"):
                cfg["key"] = c.get("llm", "key", fallback=cfg["key"])
                cfg["base_url"] = c.get("llm", "base_url", fallback=cfg["base_url"])
                cfg["model"] = c.get("llm", "model", fallback=cfg["model"])
        except Exception:
            pass
    # 2. 环境变量覆盖
    cfg["key"] = os.environ.get("LLM_API_KEY", cfg["key"])
    cfg["base_url"] = os.environ.get("LLM_BASE_URL", cfg["base_url"])
    cfg["model"] = os.environ.get("LLM_MODEL", cfg["model"])
    return cfg

def call_llm(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 4000):
    """调用 OpenAI 兼容接口，返回文本。失败抛异常。"""
    cfg = load_config()
    if not cfg["key"]:
        raise RuntimeError("未配置 API Key：设置环境变量 LLM_API_KEY 或写 ~/.deai_writer.conf（[llm] key=...）")
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    body = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system or "你是一位资深中文写作专家。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg['key']}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()

def read_text(path):
    """读取输入文件（支持 -t 文本 / 文件 / stdin）"""
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_out(text, out_path):
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ 已写入: {out_path}")
    else:
        print(text)
