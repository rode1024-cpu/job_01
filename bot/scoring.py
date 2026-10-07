"""조건표 -> 점수. None을 반환하면 탈락(알림 안 함).

웹앱(engine.js)과 같은 배점(100점 만점)을 쓴다.
직무 15 / 경력 5 / 카테고리 20 / 업무 15 / 지역 15 / 연봉 10 / 조직·규모 10
공고에 없는 정보는 감점하지 않고 중간 점수(60%)를 준다.
봇은 목록 정보만 보기 때문에 업무·조직·규모는 대부분 '없음'으로 처리된다. 상세 판정은 웹앱에서.
"""
import re

UNKNOWN = 0.6


def _hits(text, terms):
    t = text.lower()
    return [w for w in terms if w.lower() in t]


def _salary_max(s):
    """'4,800~5,500만원' -> 5500, '회사내규' -> None"""
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]{2,5}", s)]
    nums = [n for n in nums if 1500 <= n <= 20000]  # 만원 단위로 보이는 숫자만
    return max(nums) if nums else None


def quick_reject(job, cfg, regions=None):
    """검색 카드 정보(제목·회사·직무분류·경력·지역)만으로 확실히 탈락인지. 상세 조회를 아끼는 용도."""
    from regions import match_region
    title = job["title"]
    card_text = f"{title} {job['company']} {job.get('tags', '')}"
    if title and not _hits(title, cfg["role_terms"]):
        return True
    if _hits(card_text, cfg["exclude_categories"]):
        return True
    lo, hi = job["exp_min"], job["exp_max"]
    if (lo == 0 and hi == 0) or (hi and hi <= 3) or (lo is not None and lo >= 10):
        return True
    loc = job["location"]
    if regions and loc and "외 " not in loc and match_region(loc, regions) is None:
        return True                       # '외 N곳'이 없는 단일 근무지가 내 지역 밖
    return False


def score(job, cfg):
    title_co = f"{job['title']} {job['company']}"
    text = job["text"]
    plus, minus, pts = [], [], 0.0

    # 1) 직무 (15): 제목에 MD 계열 단어가 없으면 탈락
    if not _hits(job["title"], cfg["role_terms"]):
        return None
    if _hits(job["title"], cfg["role_strong_terms"]):
        pts += 15
    else:
        pts += 7.5
        minus.append("직무 불분명")

    # 2) 카테고리 (20): 제목/회사명에 제외 카테고리가 있으면 탈락
    if _hits(title_co, cfg["exclude_categories"]):
        return None
    g = _hits(text, cfg["good_categories"])
    m = _hits(text, cfg["maybe_categories"])
    ex = _hits(text, cfg["exclude_categories"])
    if ex and len(ex) >= 2 and len(ex) > len(g) + len(m):
        return None                               # 본문도 제외 카테고리가 주력
    if len(g) >= 2:
        pts += 20
    elif g or m:
        pts += 10
    else:
        pts += 20 * UNKNOWN
    if ex:
        pts -= 10
        minus += ex
    plus += g[:3] + m[:2]

    # 3) 경력 (5): 3년 이하 또는 10년 이상 요구면 탈락
    e = cfg["experience"]
    lo, hi = job["exp_min"], job["exp_max"]
    if lo == 0 and hi == 0:
        return None                               # 신입만 채용
    if hi and hi <= 3:
        return None
    if lo is not None and lo >= 10:
        return None
    if lo is None and not hi:
        pts += 5 * UNKNOWN
    elif lo is not None and lo <= e["max"] and (not hi or hi >= e["min"]):
        pts += 5
        plus.append(job["exp_text"] or "경력 적합")
    else:
        pts += 2.5
        minus.append(job["exp_text"] or "경력 애매")

    # 4) 지역 (15)
    if job.get("region"):
        # 내가 정한 지역(regions)에서 이미 걸러졌으므로 만점. 지역 정보가 없던 공고는 중간 점수
        if job["region"] == "지역 미확인":
            pts += 15 * UNKNOWN
        else:
            pts += 15
            plus.append("지역◎")
    else:
        # regions를 안 쓸 때: 출퇴근 불가 지역은 탈락
        loc_src = job["location"] or text[:500]
        if _hits(loc_src, cfg["locations"]["far"]):
            return None
        if _hits(loc_src, cfg["locations"]["primary"]):
            pts += 15
            plus.append("지역◎")
        elif _hits(loc_src, cfg["locations"]["secondary"]):
            pts += 7.5
            plus.append("지역○")
        elif job["location"]:
            pts += 4
            minus.append(f"지역({job['location'][:15]})")
        else:
            pts += 15 * UNKNOWN

    # 5) 업무 (15)
    t = _hits(text, cfg["good_tasks"])
    pts += 15 if len(t) >= 3 else 7.5 if t else 15 * UNKNOWN
    plus += t[:3]

    # 6) 연봉 (10): 회사내규/미기재는 감점 없이 중간 점수
    smax = _salary_max(job["salary_text"])
    if smax is None:
        pts += 10 * UNKNOWN
    elif smax >= cfg["salary"]["preferred"]:
        pts += 10
        plus.append(f"연봉 ~{smax:,}")
    elif smax >= 4200:
        pts += 5
        minus.append(f"연봉 ~{smax:,}")
    else:
        minus.append(f"연봉 ~{smax:,}")

    # 7) 조직·규모 (10)
    o = _hits(text, cfg["org_terms"])
    n = _hits(text, cfg["org_negative_terms"])
    if len(n) >= 2:
        minus += n
    elif n:
        pts += 5
        minus += n
    elif o:
        pts += 10
        plus += o[:2]
    else:
        pts += 10 * UNKNOWN

    # 8) 고용 형태: 계약직·인턴·파견 등은 감점 (과장급 정규직 이직 기준)
    c = _hits(text, cfg.get("contract_terms", []))
    if c:
        pts -= 10
        minus.append(f"고용형태({c[0]})")

    if _hits(text, cfg["level_terms"]):
        plus.append("과장급")

    return {"score": max(0, min(round(pts), 100)), "plus": plus, "minus": minus}
