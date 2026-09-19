#!/usr/bin/env python3
"""百炼模型可用性探针（先探不花钱，再按需真跑验证）

为什么需要它：**提交返回 task_id ≠ 模型可用**。第三方模型（vendor/model 命名，如 Vidu/PixVerse/可灵）
未在百炼控制台「模型广场」开通时，提交阶段照样受理，执行阶段才 FAILED：
    InvalidParameter: The product is not activated, please confirm that you have activated
    products and try again after activation.
→ 判「能不能用」必须跑通一条最低规格任务看到 SUCCEEDED，别凭入口响应向用户报「可用」。

用法：
    python3 probe_model_availability.py                       # 只做不花钱的入口探活
    python3 probe_model_availability.py --live                # 真跑最低规格任务（会计费，会打印预估）
    python3 probe_model_availability.py --models wan3.0-video,kling/kling-v3-video-generation
    python3 probe_model_availability.py --live --resolution 720P   # 更省钱的验证档

计费提示（2026-09 官方原价，元/秒）：万相 2.7-r2v 1080P 1.0 / 720P 0.6；wan3.0-video 1.2 / 0.6；
Vidu Q3 ad 0.9375 / 0.78125；PixVerse V6 0.68(有声)/0.53(无声) / 0.36/0.27；可灵 V3 1.2(有声)/0.8(无声)。
本脚本 --live 用 5 秒档，单模型成本≈1~6 元。

参考文件：ai-video-ad-production/references/bailian-video-model-catalog.md
          aliyun-bailien-and-tongyi-api/references/account-and-model-availability-diagnosis.md
"""
import argparse, json, os, subprocess, sys, time

KEY_PATH = os.path.expanduser("~/.hermes/.dashscope_key")
EP = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
TASK = "https://dashscope.aliyuncs.com/api/v1/tasks/"
REF = "https://yunvela.com/dh/hsq1_front.jpg"   # 任意公网可访问图；仅 --live 用

DEFAULT_MODELS = [
    "wan2.7-r2v",                              # 现用主线
    "wan3.0-video",                            # 自研新版：最长 30s / 多模态
    "vidu/viduq3-ad_reference2video",          # 第三方：广告专用
    "pixverse/pixverse-v6-r2v",                # 第三方：多参考 / 15s / 最便宜
    "kling/kling-v3-video-generation",         # 第三方：真人身段最好
]
PRICE_1080P = {  # 元/秒（官方原价，仅用于成本提示）
    "wan2.7-r2v": 1.0, "wan3.0-video": 1.2, "vidu/viduq3-ad_reference2video": 0.9375,
    "pixverse/pixverse-v6-r2v": 0.68, "kling/kling-v3-video-generation": 1.2,
}


def key():
    if not os.path.exists(KEY_PATH):
        sys.exit(f"缺 {KEY_PATH}")
    return open(KEY_PATH).read().strip()


def post(body, timeout=40):
    r = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-X", "POST", EP,
                        "-H", f"Authorization: Bearer {key()}",
                        "-H", "Content-Type: application/json",
                        "-H", "X-DashScope-Async: enable",
                        "-d", json.dumps(body, ensure_ascii=False)],
                       capture_output=True, text=True).stdout
    try:
        return json.loads(r)
    except Exception:
        return {"_raw": r[:300]}


def get(tid):
    r = subprocess.run(["curl", "-s", "--max-time", "30", "-H", f"Authorization: Bearer {key()}",
                        f"{TASK}{tid}"], capture_output=True, text=True).stdout
    try:
        return json.loads(r)
    except Exception:
        return {"_raw": r[:300]}


def probe(model):
    """入口探活：空 input 不花钱。返回 (结论, 详情)"""
    d = post({"model": model, "input": {}})
    code = str(d.get("code") or "")
    msg = str(d.get("message") or d.get("_raw") or "")[:150]
    if "Arrearage" in code + msg or "overdue" in msg.lower():
        return "账号拦截", msg          # 账号欠费/未结清账单：先处理好账号，与模型无关
    if d.get("output", {}).get("task_id"):
        return "入口放行", "空 input 也被受理"
    if "InvalidParameter" in code or "required" in msg.lower():
        return "入口放行", msg          # 参数被校验 = 没被权限拦
    return "未知", f"{code} {msg}"


def live(model, resolution, seconds, prompt):
    """真跑最低规格：唯一能证明「已开通/可出片」的方法"""
    d = post({"model": model,
              "input": {"prompt": prompt, "images": [REF]},
              "parameters": {"resolution": resolution, "duration": seconds, "watermark": False}})
    tid = (d.get("output") or {}).get("task_id")
    if not tid:
        return "提交被拒", f"{d.get('code')} {str(d.get('message'))[:150]}"
    t0 = time.time()
    while time.time() - t0 < 420:
        o = (get(tid).get("output") or {})
        st = o.get("task_status")
        if st == "SUCCEEDED":
            return "✅ 可用", f"{tid} 用时 {time.time()-t0:.0f}s"
        if st in ("FAILED", "CANCELED"):
            em = f"{o.get('code')} {o.get('message') or ''}"
            if "not been activated" in em or "not activated" in em:
                return "❌ 未开通", em[:150] + " → 控制台「模型广场」开通该产品"
            return "❌ 失败", em[:180]
        time.sleep(15)
    return "⏱ 超时", f"{tid}（可能仍在生成，稍后 GET /api/v1/tasks/{tid} 复查）"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--live", action="store_true", help="真跑最低规格任务（计费）")
    ap.add_argument("--resolution", default="720P")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--prompt", default="a person holding a small device, studio lighting, shallow depth of field")
    a = ap.parse_args()

    models = [m.strip() for m in a.models.split(",") if m.strip()]
    if a.live:
        est = sum(PRICE_1080P.get(m, 1.2) * a.duration * (0.6 if a.resolution == "720P" else 1.0)
                  for m in models)
        print(f"⚠️ --live 将真实计费：{len(models)} 个模型 × {a.duration}s × {a.resolution} ≈ {est:.1f} 元\n")

    print(f"{'模型':44s} {'入口探活':10s} 结论")
    print("-" * 96)
    results = {}
    for m in models:
        verdict, detail = probe(m)
        line = f"{m:44s} {verdict:10s} {detail}"
        if a.live:
            lv, ld = live(m, a.resolution, a.duration, a.prompt)
            results[m] = (verdict, lv, ld)
            line += f"\n{'':44s} {'真跑验证':10s} {lv} {ld}"
        print(line, flush=True)
    if results:
        print("\n=== 汇总（只有 ✅ 可用 的才能写进生产脚本）===")
        for m, (pv, lv, ld) in results.items():
            print(f"  {m}: 入口={pv} / 实测={lv}")
        blocked = [m for m, (_, lv, _) in results.items() if lv == "❌ 未开通"]
        if blocked:
            print("  → 需开通：" + "、".join(blocked) + "（百炼控制台「模型广场」→ 搜模型 → 开通）")


if __name__ == "__main__":
    main()
