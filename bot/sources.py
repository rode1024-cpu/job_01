"""공고 수집: 사람인(공식 API), 잡코리아(검색 페이지)"""
import html
import os
import re
import time

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (personal job alert; low frequency)"}

# 실행 결과 요약용 (main.py가 읽음)
STATS = {"jobkorea_search_ok": 0, "jobkorea_search_fail": 0}


def _get(url, **kw):
    """접속 실패 시 3번까지 다시 시도 (잡코리아가 간헐적으로 연결을 끊음)"""
    last = None
    for i in range(3):
        try:
            return requests.get(url, timeout=(10, 20), **kw)
        except requests.RequestException as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


def _job(source, jid, title, company, location, exp_min, exp_max, exp_text,
         salary_text, text, url):
    return {
        "id": f"{source}:{jid}", "source": source, "title": title or "",
        "company": company or "", "location": location or "",
        "exp_min": exp_min, "exp_max": exp_max, "exp_text": exp_text or "",
        "salary_text": salary_text or "", "text": text or "", "url": url,
    }


# ---------------------------------------------------------------- 사람인
def fetch_saramin(keywords, count=100):
    key = os.environ.get("SARAMIN_KEY")
    if not key:
        print("[사람인] SARAMIN_KEY가 없어서 건너뜀")
        return []

    jobs = {}
    for kw in keywords:
        params = {
            "access-key": key,
            "keywords": kw,   # API 명세 기준 파라미터명
            "keyword": kw,    # 공식 예제에 쓰인 이름도 같이 전송 (둘 중 하나만 쓰이면 무시됨)
            "sort": "pd",     # 게시일 최신순
            "count": count,
        }
        try:
            r = requests.get("https://oapi.saramin.co.kr/job-search",
                             params=params, headers={"Accept": "application/json"},
                             timeout=20)
            r.raise_for_status()
            items = r.json().get("jobs", {}).get("job", []) or []
        except Exception as e:
            print(f"[사람인] '{kw}' 조회 실패: {e}")
            continue

        for it in items:
            pos = it.get("position", {}) or {}
            exp = pos.get("experience-level", {}) or {}
            loc = html.unescape((pos.get("location", {}) or {}).get("name", ""))
            company = ((it.get("company", {}) or {}).get("detail", {}) or {}).get("name", "")
            salary = (it.get("salary", {}) or {}).get("name", "")
            industry = (pos.get("industry", {}) or {}).get("name", "")
            job_code = (pos.get("job-code", {}) or {}).get("name", "")
            title = html.unescape(pos.get("title", ""))
            text = " ".join([title, company, industry, job_code,
                             it.get("keyword", "") or "", salary, loc])
            jobs[it["id"]] = _job(
                "saramin", it["id"], title, company, loc,
                exp.get("min"), exp.get("max"), exp.get("name"),
                salary, text, it.get("url", ""),
            )
        time.sleep(1)
    print(f"[사람인] {len(jobs)}건 수집")
    return list(jobs.values())


# ---------------------------------------------------------------- 잡코리아
_REGION_HEAD = re.compile(r"^(서울|경기|인천|부산|대구|대전|광주|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)")
_GI = re.compile(r"/Recruit/GI_Read/(\d+)")
_DETAIL_LABELS = ("모집분야", "고용형태", "급여", "근무지주소", "근무시간", "경력")


def parse_exp(text):
    """'경력5년↑' / '경력 (2년이상)' / '경력3~5년' / '경력무관' / '신입' -> (min, max)"""
    text = text or ""
    m = re.search(r"(\d{1,2})\s*[~\-]\s*(\d{1,2})\s*년", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{1,2})\s*년\s*(?:↑|이상)", text)
    if m:
        return int(m.group(1)), None
    if "신입" in text and "경력" not in text:
        return 0, 0
    return None, None


def parse_cards(html):
    """검색 결과 페이지의 공고 카드 -> [{id, title, company, location, tags, exp_text, salary_text}]
    카드 안 글자 순서: (배지) 스크랩 / 제목 / 회사 / 지역 / 직무분류 / (연봉) 즉시 지원 / 경력 ..."""
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for c in soup.find_all(attrs={"data-sentry-component": "CardJob"}):
        a = c.find("a", href=_GI)
        if not a:
            continue
        gid = _GI.search(a["href"]).group(1)
        texts = list(c.stripped_strings)
        card = {"id": gid, "title": "", "company": "", "location": "", "tags": "", "exp_text": "", "salary_text": ""}
        if "스크랩" in texts:
            i = texts.index("스크랩")
            head = texts[i + 1:i + 5]
            if len(head) >= 3 and _REGION_HEAD.match(head[2]):
                card["title"], card["company"], card["location"] = head[0], head[1], head[2]
                card["tags"] = head[3] if len(head) > 3 and not head[3].startswith(("연봉", "즉시")) else ""
        for t in texts:
            if not card["salary_text"] and re.match(r"^(연봉|월급|시급)", t):
                card["salary_text"] = t
            if not card["exp_text"] and re.match(r"^(경력|신입)", t):
                card["exp_text"] = t
        cards.append(card)
    return cards


def parse_detail(html):
    """상세 페이지의 '모집요강' 이름표(근무지주소, 경력, 고용형태, 급여 ...) -> dict"""
    soup = BeautifulSoup(html, "html.parser")
    d = {}
    for sp in soup.find_all("span"):
        lab = sp.get_text(strip=True)
        if lab in _DETAIL_LABELS and lab not in d:
            val = sp.parent.get_text(" ", strip=True)
            if val.startswith(lab):
                val = val[len(lab):].strip()
            d[lab] = val.replace("지도보기", "").strip()
    og = soup.find("meta", property="og:title")
    d["_og"] = ((og.get("content") if og else "") or "").replace("| 잡코리아", "").strip()
    return d


def fetch_jobkorea(keywords, seen, max_detail=15, prefilter=None, pages=3):
    """검색(키워드 x 여러 페이지) -> 카드로 1차 거름(prefilter) -> 남은 신규 공고만 상세 조회.
    prefilter(card_job) 가 False 이면 상세 조회 없이 STATS['jobkorea_skipped_ids']에 담는다."""
    cards = {}
    for kw in keywords:
        for pg in range(1, pages + 1):
            try:
                r = _get("https://www.jobkorea.co.kr/Search/",
                         params={"stext": kw, "tabType": "recruit", "Page_No": pg}, headers=UA)
                found = parse_cards(r.text)
                if not found:                       # 카드 구조가 바뀌었을 때: 예전 방식(ID만)으로 대체
                    found = [{"id": g, "title": "", "company": "", "location": "", "tags": "",
                              "exp_text": "", "salary_text": ""} for g in dict.fromkeys(_GI.findall(r.text))]
                for c in found:
                    cards.setdefault(c["id"], c)
                STATS["jobkorea_search_ok"] += 1
            except Exception as e:
                STATS["jobkorea_search_fail"] += 1
                print(f"[잡코리아] '{kw}' {pg}페이지 검색 실패: {type(e).__name__}")
            time.sleep(2)

    new = [c for gid, c in cards.items() if f"jobkorea:{gid}" not in seen]
    keep, skipped = [], []
    for c in new:
        lo, hi = parse_exp(c["exp_text"])
        job = _job("jobkorea", c["id"], c["title"], c["company"], c["location"], lo, hi,
                   c["exp_text"], c["salary_text"], f"{c['title']} {c['company']} {c['tags']}", "")
        job["tags"] = c["tags"]
        (keep if (prefilter is None or prefilter(job)) else skipped).append(c)
    STATS["jobkorea_cards"] = len(cards)
    STATS["jobkorea_skipped_ids"] = [f"jobkorea:{c['id']}" for c in skipped]
    print(f"[잡코리아] 카드 {len(cards)}건 / 신규 {len(new)}건 / 카드에서 제외 {len(skipped)}건 / 상세조회 대상 {min(len(keep), max_detail)}건")

    jobs = []
    for c in keep[:max_detail]:
        gid = c["id"]
        url = f"https://www.jobkorea.co.kr/Recruit/GI_Read/{gid}"
        try:
            d = parse_detail(_get(url, headers=UA).text)
        except Exception as e:
            print(f"[잡코리아] {gid} 상세 실패: {type(e).__name__}")
            continue
        title, company = c["title"], c["company"]
        if not title and " - " in d["_og"]:
            company, title = (x.strip() for x in d["_og"].split(" - ", 1))
            company = company.replace("채용", "").strip()
        location = d.get("근무지주소") or c["location"]
        exp_text = d.get("경력") or c["exp_text"]
        lo, hi = parse_exp(exp_text)
        salary = d.get("급여") or c["salary_text"]
        text = " ".join([title, company, c["tags"]] + [f"{k} {v}" for k, v in d.items() if not k.startswith("_")])
        jobs.append(_job("jobkorea", gid, title, company, location, lo, hi, exp_text, salary, text, url))
        time.sleep(2)
    return jobs
