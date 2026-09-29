"""실행: python main.py  (테스트: python main.py --dry-run)"""
import html
import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

from scoring import score
from sources import fetch_jobkorea, fetch_saramin

ROOT = Path(__file__).parent
SEEN_FILE = ROOT / "seen.json"
DRY = "--dry-run" in sys.argv
KEEP_DAYS = 60


def send(text):
    if DRY:
        print("-" * 50 + "\n" + text)
        return
    token, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  data={"chat_id": chat, "text": text, "parse_mode": "HTML",
                        "disable_web_page_preview": True}, timeout=20)
    time.sleep(1)


def fmt(job, r, star):
    e = html.escape
    head = f"{'★ ' if r['score'] >= star else ''}{r['score']}점 · {'사람인' if job['source'] == 'saramin' else '잡코리아'}"
    info = " · ".join(x for x in [job["location"], job["exp_text"], job["salary_text"]] if x)
    lines = [f"<b>{e(head)}</b>", f"[{e(job['company'])}] {e(job['title'])}"]
    if info:
        lines.append(e(info[:120]))
    if r["plus"]:
        lines.append("＋ " + e(", ".join(dict.fromkeys(r["plus"]))))
    if r["minus"]:
        lines.append("－ " + e(", ".join(dict.fromkeys(r["minus"]))))
    lines.append(job["url"])
    return "\n".join(lines)


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    seen = json.loads(SEEN_FILE.read_text()) if SEEN_FILE.exists() else {}
    first_run = not seen
    now = int(time.time())

    jobs = fetch_saramin(cfg["search_keywords"])
    jobs += fetch_jobkorea(cfg["search_keywords"], seen, cfg["jobkorea_max_detail"])

    picked = []
    for j in jobs:
        if j["id"] in seen:
            continue
        seen[j["id"]] = now          # 점수와 상관없이 본 공고는 기록 (중복 방지)
        r = score(j, cfg)
        if r and r["score"] >= cfg["notify_threshold"]:
            picked.append((r["score"], j, r))

    picked.sort(key=lambda x: -x[0])
    limit = cfg["first_run_max"] if first_run else cfg["max_alerts_per_run"]
    for _, j, r in picked[:limit]:
        send(fmt(j, r, cfg["star_threshold"]))
    if len(picked) > limit:
        rest = "\n".join(f"{s}점 [{html.escape(j['company'])}] {html.escape(j['title'][:30])}"
                         for s, j, _ in picked[limit:limit + 15])
        send(f"<b>그 외 {len(picked) - limit}건</b>\n{rest}")
    print(f"신규 {len(picked)}건 알림 대상 / 전송 {min(len(picked), limit)}건")

    # 오래된 기록 정리 후 저장
    seen = {k: v for k, v in seen.items() if now - v < KEEP_DAYS * 86400}
    if not DRY:
        SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False))


if __name__ == "__main__":
    main()
