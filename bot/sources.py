"""공고 수집: 사람인(공식 API), 잡코리아(검색 페이지)"""
import html
import os
import re
import time

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (personal job alert; low frequency)"}


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
_EXP_RANGE = re.compile(r"경력\s*(\d{1,2})\s*[~\-]\s*(\d{1,2})\s*년")
_EXP_MIN = re.compile(r"경력\s*(\d{1,2})\s*년\s*(?:↑|이상)")
_LOC = re.compile(r"(서울|경기|인천)\s*[가-힣]+(?:시|구|군)?(?:\s*[가-힣]+구)?")


def fetch_jobkorea(keywords, seen, max_detail=15):
    ids = []
    for kw in keywords:
        try:
            r = requests.get("https://www.jobkorea.co.kr/Search/",
                             params={"stext": kw, "tabType": "recruit"},
                             headers=UA, timeout=20)
            ids += re.findall(r"/Recruit/GI_Read/(\d+)", r.text)
        except Exception as e:
            print(f"[잡코리아] '{kw}' 검색 실패: {e}")
        time.sleep(2)

    uniq = list(dict.fromkeys(ids))
    new_ids = [i for i in uniq if f"jobkorea:{i}" not in seen][:max_detail]
    print(f"[잡코리아] 검색 {len(uniq)}건 / 신규 상세조회 {len(new_ids)}건")

    jobs = []
    for gid in new_ids:
        url = f"https://www.jobkorea.co.kr/Recruit/GI_Read/{gid}"
        try:
            r = requests.get(url, headers=UA, timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            print(f"[잡코리아] {gid} 상세 실패: {e}")
            continue

        og = soup.find("meta", property="og:title")
        page_title = (og.get("content") if og else None) or (soup.title.string if soup.title else "")
        page_title = (page_title or "").replace("| 잡코리아", "").strip()
        # 보통 "회사명 채용 - 공고제목" 형태
        company, title = "", page_title
        if " - " in page_title:
            company, title = page_title.split(" - ", 1)
            company = company.replace("채용", "").strip()

        body = soup.get_text(" ", strip=True)[:8000]
        m = _EXP_RANGE.search(body)
        exp_min, exp_max = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        if not m:
            m2 = _EXP_MIN.search(body)
            exp_min = int(m2.group(1)) if m2 else None
        loc_m = _LOC.search(body)
        sal_m = re.search(r"(연봉|급여)[^가-힣]{0,3}[\d,]{3,6}\s*(?:~\s*[\d,]{3,6})?\s*만원|회사내규", body)

        jobs.append(_job("jobkorea", gid, title, company,
                         loc_m.group(0) if loc_m else "", exp_min, exp_max,
                         m.group(0) if m else "", sal_m.group(0) if sal_m else "",
                         f"{page_title} {body}", url))
        time.sleep(2)
    return jobs
