#!/usr/bin/env python3
"""
E-commerce Material Studio — AI 场景融合合成器
=================================================
用 Qwen-Image-Edit 图生图，把产品图真实融入使用场景（AI 重绘光影/透视/边缘，非 PIL 贴图）。

用法:
  python3 ai_compositor.py 产品图.png --scene "描述场景" -o 输出.png
  python3 ai_compositor.py 产品图.png --selling-point 口袋mini --o 输出.png   # 卖点→自动匹配场景模板
  python3 ai_compositor.py 产品图.png --scene "..." --dry-run                  # 只打印 prompt 不调 API

配置:
  SILICON_FLOW_API_KEY  硅基流动 API Key（必需）

卖点→场景模板（每个卖点必须有专属场景，场景含视觉证据）:
  口袋mini     → 手指从牛仔裤口袋抽出产品的瞬间
  90天续航     → 行李箱衣物间 + Type-C 充电线露出
  动力/高速    → 浴镜前手持使用中（动作证明）
  防水         → 水流冲刷/湿手使用
  便携         → 手掌托举对比尺寸
"""
import sys, os, json, base64, argparse, urllib.request

API_URL = "https://api.siliconflow.cn/v1/image/generations"
MODEL = "Qwen/Qwen-Image-Edit-2509"

SELLING_SCENES = {
    "口袋mini": "产品（剃须刀）被手指从牛仔裤口袋抽出，特写，休闲街头，产品是画面绝对主角",
    "90天续航": "产品（剃须刀）放在行李箱衣物间衣物上，Type-C充电线连着产品接口，出差场景，产品是画面绝对主角",
    "动力": "产品（剃须刀）在浴镜前被手持使用中，动作证明，浴室暖光，产品是画面绝对主角",
    "防水": "产品（剃须刀）在流水冲刷下，湿手使用，浴室，产品是画面绝对主角",
    "便携": "产品（剃须刀）放在手掌中托举对比尺寸，干净背景，产品是画面绝对主角",
    "通用": "简洁现代桌面，产品（剃须刀）居中，自然光，大景深前后清晰，产品是画面绝对主角",
}

PROMPT_TMPL = """把图片中的产品（严格保留产品原貌：{product_desc}，产品轮廓边缘保持原图锐利清晰，禁止柔化重绘添加光晕改变形状颜色）完整地放进场景，产品必须是画面绝对主角且完整可见：{scene}。{extra_lock}场景大景深前后都清晰，无虚化。产品摄影，真实光影融合，接触阴影自然。画面中只保留这一个产品，绝对不能出现第二个/复制品/残影/手机，绝对不能只画场景物品而不画产品本体。"""


def load_key():
    key = os.environ.get("SILICON_FLOW_API_KEY", "")
    if not key and os.path.exists(os.path.expanduser("~/.hermes/.env")):
        with open(os.path.expanduser("~/.hermes/.env")) as f:
            for line in f:
                if line.startswith("SILICON_FLOW_API_KEY="):
                    key = line.strip().split("=", 1)[1]
                    break
    return key


def build_prompt(scene, product_desc, product_name):
    lock = f"顶部部件特征必须与图片中完全一致绝不能改（{product_name}）。"
    return PROMPT_TMPL.format(product_desc=product_desc, scene=scene, extra_lock=lock)


def call_fusion(image_path, prompt, out_path):
    """图生图融合（Qwen-Image-Edit）— 用 curl 子进程（Python 3.9 LibreSSL 与硅基流动 TLS 不兼容）"""
    import subprocess, tempfile
    key = load_key()
    if not key:
        raise SystemExit("❌ 未配置 SILICON_FLOW_API_KEY（环境变量或 ~/.hermes/.env）")
    with open(image_path, "rb") as f:
        img_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode()

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "image": img_b64,
        "batch_size": 1,
        "num_inference_steps": 30,
        "guidance_scale": 7.5,
        "size": "1024x1024",
    }
    # payload 写临时文件（避免命令行长度限制）
    tmp_json = os.path.join(tempfile.gettempdir(), "ai_compositor_payload.json")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    print("⏳ AI 融合生成中（约 40-90s）...", file=sys.stderr)
    last_err = None
    for attempt in range(3):
        try:
            r = subprocess.run(
                ["curl", "-s", "--connect-timeout", "15", "-X", "POST", API_URL,
                 "-H", f"Authorization: Bearer {key}",
                 "-H", "Content-Type: application/json",
                 "--data", f"@{tmp_json}"],
                capture_output=True, text=True, timeout=190,
            )
            result = json.loads(r.stdout)
            break
        except Exception as e:
            last_err = e
            print(f"⚠️ 第{attempt+1}次失败: {e}（重试中）", file=sys.stderr)
            import time
            time.sleep(5)
    else:
        raise SystemExit(f"❌ API 调用失败（3次）: {last_err}")
    if "error" in result:
        raise SystemExit(f"❌ API 错误: {result['error']}")

    img_entry = result["images"][0]
    if isinstance(img_entry, dict) and "url" in img_entry:
        url = img_entry["url"]
    elif isinstance(img_entry, str) and img_entry.startswith("http"):
        url = img_entry
    elif isinstance(img_entry, str):
        img_bytes = base64.b64decode(img_entry)
        url = None
    else:
        raise SystemExit(f"❌ 未知返回格式: {img_entry}")

    if url:
        r = subprocess.run(["curl", "-s", "--connect-timeout", "15", "-L", url],
                           capture_output=True, timeout=90)
        img_bytes = r.stdout

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    print(f"✅ 已保存: {out_path}（{len(img_bytes)//1024}KB）")


def main():
    p = argparse.ArgumentParser(description="AI 场景融合合成器（Qwen-Image-Edit 图生图）")
    p.add_argument("product_image", help="产品图路径")
    p.add_argument("--scene", help="场景描述（优先于 --selling-point）")
    p.add_argument("--selling-point", help="卖点关键词（自动匹配场景模板）")
    p.add_argument("--product-name", default="产品", help="产品名（用于部件锁定 prompt）")
    p.add_argument("--product-desc", default="", help="产品外观描述（写清部件特征，防止 AI 改写）")
    p.add_argument("-o", "--output", default="output/ai_fusion.png", help="输出路径")
    p.add_argument("--dry-run", action="store_true", help="只打印 prompt 不调 API")
    args = p.parse_args()

    if not os.path.exists(args.product_image):
        raise SystemExit(f"❌ 产品图不存在: {args.product_image}")

    # 场景确定
    if args.scene:
        scene = args.scene
    elif args.selling_point:
        for k, v in SELLING_SCENES.items():
            if k in args.selling_point:
                scene = v
                break
        else:
            scene = SELLING_SCENES["通用"]
        print(f"🎯 卖点「{args.selling_point}」→ 场景: {scene}", file=sys.stderr)
    else:
        scene = SELLING_SCENES["通用"]

    product_desc = args.product_desc or "保持图片中的产品外观原样"
    prompt = build_prompt(scene, product_desc, args.product_name)

    if args.dry_run:
        print("【Prompt】")
        print(prompt)
        print("\n（dry-run 模式，未调用 API）")
        return

    call_fusion(args.product_image, prompt, args.output)


if __name__ == "__main__":
    main()
