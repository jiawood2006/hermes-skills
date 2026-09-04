#!/usr/bin/env python3
"""抖音视频提取 v4.0（2026-08-26 更新）
新流程（SSR 结构已变，不再注入 item_list）：
  1. curl 短链（iPhone UA）→ 提取 _ROUTER_DATA.video_(id)/page.itemId（19位真实ID）
  2. Playwright 桌面 UA 打开 www.douyin.com/video/{itemId}
     → 监听 aweme/detail API 响应 → 提取完整 aweme_detail
  3. 输出元数据（desc/作者/时长/点赞）+ play_url → 可选下载

用法:
  python3 douyin_extract.py "https://v.douyin.com/xxx/"
  python3 douyin_extract.py "https://v.douyin.com/xxx/" --download   # 下载视频
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

CHROME = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium-1223/chrome-mac-x64/"
    "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
DESKTOP_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def get_item_id(share_url):
    """curl 短链（iPhone UA）→ 提取真实 itemId（19 位）"""
    try:
        out = subprocess.run(
            ["curl", "-sL", "--max-time", "15", "-H", f"User-Agent: {IPHONE_UA}",
             "-H", "Accept: text/html", share_url],
            capture_output=True, text=True, timeout=20).stdout
        m = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>', out, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                page = data.get("loaderData", {}).get("video_(id)/page", {})
                item_id = page.get("itemId")
                if item_id and len(str(item_id)) >= 18:
                    return str(item_id)
            except Exception:
                pass
    except Exception:
        pass
    # 降级：从短链/URL 提取
    m = re.search(r"/(\d{15,20})", share_url)
    return m.group(1) if m else None


def extract_with_playwright(item_id):
    """Playwright 桌面 UA 打开视频页，监听 aweme/detail 响应"""
    code = r"""
import asyncio, json, sys
from playwright.async_api import async_playwright

CHROME = r"%s"
URL = "https://www.douyin.com/video/%s"
DESKTOP_UA = r"%s"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, executable_path=CHROME,
                                    args=["--disable-blink-features=AutomationControlled"])
        ctx = await b.new_context(user_agent=DESKTOP_UA,
                                  viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = await ctx.new_page()
        detail = {}
        async def on_response(r):
            try:
                if "aweme/detail" in r.url or "aweme/v1/web" in r.url:
                    body = await r.text()
                    if body and "aweme_detail" in body:
                        detail["body"] = body
            except Exception:
                pass
        page.on("response", on_response)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=40000)
        except Exception:
            pass
        await page.wait_for_timeout(7000)
        for _ in range(3):
            try:
                await page.mouse.wheel(0, 800)
            except Exception:
                pass
            await page.wait_for_timeout(1200)
        if detail:
            print(detail["body"])
        else:
            print("NO_DETAIL")
        await b.close()

asyncio.run(main())
""" % (CHROME, item_id, DESKTOP_UA)
    try:
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=90)
        body = out.stdout.strip()
        if body.startswith("{"):
            return json.loads(body).get("aweme_detail") or {}
    except Exception:
        pass
    return None


def fetch_douyin(share_url, download=False, out_dir=None):
    """抖音链接 → 元数据（+可选下载）。供 CLI 与其他模块复用。

    返回 dict:
      {ok: bool, error?: str, item_id?, meta?: {...}, video_path?: str|None}
    """
    item_id = get_item_id(share_url)
    if not item_id:
        return {"ok": False, "error": "无法获取视频 ID"}
    detail = extract_with_playwright(item_id)
    if not detail:
        return {"ok": False, "error": "提取失败：抖音反爬/网络问题。备选：从抖音App转发→复制文案。"}
    meta = {
        "item_id": item_id,
        "title": detail.get("desc", ""),
        "author": (detail.get("author") or {}).get("nickname", ""),
        "duration_s": round(((detail.get("video") or {}).get("duration", 0)) / 1000),
        "digg": ((detail.get("statistics") or {}).get("digg_count", 0)),
        "comment": ((detail.get("statistics") or {}).get("comment_count", 0)),
        "share": ((detail.get("statistics") or {}).get("share_count", 0)),
        "hashtags": [te.get("hashtag_name") for te in (detail.get("text_extra") or [])],
    }
    video_path = None
    if download:
        play = ((detail.get("video") or {}).get("play_addr") or {}).get("url_list") or []
        if play:
            video_path = download_video(play[0], out_dir=out_dir)
    return {"ok": True, "item_id": item_id, "meta": meta, "detail": detail,
            "video_path": video_path}


def download_video(play_url, out_dir=None):
    """下载无水印视频到 out_dir（默认 /tmp），返回本地路径"""
    out_dir = out_dir or tempfile.gettempdir()
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36",
                   "Referer": "https://www.douyin.com/"}
        req = urllib.request.Request(play_url, headers=headers)
        data = urllib.request.urlopen(req, timeout=90).read()
        path = os.path.join(out_dir, "douyin_video.mp4")
        with open(path, "wb") as f:
            f.write(data)
        return path if os.path.getsize(path) > 0 else None
    except Exception:
        return None


def print_metadata(detail):
    print("=" * 40)
    print("标题:", detail.get("desc", ""))
    print("作者:", (detail.get("author") or {}).get("nickname", ""))
    st = detail.get("statistics") or {}
    print("点赞:", st.get("digg_count"), "| 评论:", st.get("comment_count"))
    dur = (detail.get("video") or {}).get("duration", 0)
    print("时长:", round(dur / 1000), "秒")
    print("话题:", [te.get("hashtag_name") for te in (detail.get("text_extra") or [])])
    print("=" * 40)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 douyin_extract.py <链接> [--download]")
        return 1
    share_url = sys.argv[1]
    do_download = "--download" in sys.argv
    item_id = get_item_id(share_url)
    if not item_id:
        print("无法获取视频 ID")
        return 1
    print("视频ID:", item_id)
    detail = extract_with_playwright(item_id)
    if not detail:
        print("提取失败：抖音反爬/网络问题。备选：用户从抖音App 转发→复制文案。")
        return 1
    print_metadata(detail)
    # 保存完整 detail 供下载
    with open("/tmp/douyin_detail.json", "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=1)
    play = ((detail.get("video") or {}).get("play_addr") or {}).get("url_list") or []
    if play:
        with open("/tmp/douyin_playurl.txt", "w") as f:
            f.write(play[0])
        print("play_url 已保存 /tmp/douyin_playurl.txt")
    if do_download and play:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36",
                       "Referer": "https://www.douyin.com/"}
            req = urllib.request.Request(play[0], headers=headers)
            data = urllib.request.urlopen(req, timeout=90).read()
            path = "/tmp/douyin_video.mp4"
            with open(path, "wb") as f:
                f.write(data)
            print("视频已下载:", path, len(data), "bytes")
        except Exception as e:
            print("下载失败:", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
