"""실행: python main.py  (테스트: python main.py --dry-run)"""
import html
import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

from regions import match_region
from scoring import score
from sources import fetch_jobkorea, fetch_saramin

ROOT = Path(__file__).parent
SEEN_FILE = ROOT / "seen.json"
DRY = "--dry-run" in sys.argv
KEEP_DAYS = 60


def send(text):
    if DRY:
        print("-" * 50 + "\n" + text)
        return True
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text, "parse_mode": "HTML",
                                "disable_web_page_preview": True}, timeout=20)
        ok = r.ok
        detail = r.text[:200]
    except Exception as e:                       # 토큰이 로그에 찍히지 않게 예외 문구는 쓰지 않음
        ok, detail = False, type(e).__name__
    if not ok:
        print(f"[텔레그램] 전송 실패: {detail}")
    time.sleep(1)
    return ok


def fmt(job, r, star):
    e = html.escape
    src = '사람인' if job['source'] == 'saramin' else '잡코리아'
    head = f"{job['region'] + ' · ' if job.get('region') else ''}{'★ ' if r['score'] >= star else ''}{r['score']}점 · {src}"
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


UNKNOWN_REGION = "지역 미확인"


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    regions = cfg.get("regions") or []
    seen = json.loads(SEEN_FILE.read_text()) if SEEN_FILE.exists() else {}
    first_run = not seen
    now = int(time.time())

    jobs = fetch_saramin(cfg["search_keywords"])
    jobs += fetch_jobkorea(cfg["search_keywords"], seen, cfg["jobkorea_max_detail"])

    groups = {}                                   # 지역 -> [(점수, 공고, 결과)]
    for j in jobs:
        if j["id"] in seen:
            continue
        if regions:
            reg = match_region(j["location"], regions)
            if reg is None and not j["location"] and cfg.get("unknown_region") == "send":
                reg = UNKNOWN_REGION
            if reg is None:
                seen[j["id"]] = now               # 내가 정한 지역이 아니면 알림 없이 기록
                continue
            j["region"] = reg
        r = score(j, cfg)
        if r and r["score"] >= cfg["notify_threshold"]:
            groups.setdefault(j.get("region") or "전체", []).append((r["score"], j, r))
        else:
            seen[j["id"]] = now                   # 알림 대상이 아닌 공고는 바로 기록 (중복 방지)

    limit = cfg["first_run_max"] if first_run else cfg["max_alerts_per_run"]   # 지역별 한도
    order = [g for g in regions + [UNKNOWN_REGION, "전체"] if g in groups]
    total = sent = 0
    for g in order:
        picked = sorted(groups[g], key=lambda x: -x[0])
        total += len(picked)
        for _, j, r in picked[:limit]:
            if send(fmt(j, r, cfg["star_threshold"])):
                seen[j["id"]] = now               # 알림 대상은 전송에 성공해야 기록
                sent += 1
        if len(picked) > limit:
            rest = "\n".join(f"{sc}점 [{html.escape(j['company'])}] {html.escape(j['title'][:30])}"
                             for sc, j, _ in picked[limit:limit + 15])
            if send(f"<b>{html.escape(g)} 그 외 {len(picked) - limit}건</b>\n{rest}"):
                for _, j, _ in picked[limit:limit + 15]:
                    seen[j["id"]] = now
    print(f"신규 {total}건 알림 대상 / 전송 성공 {sent}건 (지역: {', '.join(order) or '없음'})")

    # 오래된 기록 정리 후 저장
    seen = {k: v for k, v in seen.items() if now - v < KEEP_DAYS * 86400}
    if not DRY:
        SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False))


if __name__ == "__main__":
    main()
