"""잡코리아 파서 시험 (실제 페이지에서 확인한 구조를 흉내 낸 가짜 HTML): python test_parsers.py"""
import yaml
from sources import parse_cards, parse_detail, parse_exp
from scoring import quick_reject, score
from regions import match_region

CARDS = '''<div data-sentry-component="CardJob"><a href="https://www.jobkorea.co.kr/Recruit/GI_Read/101?Oem_Code=C1"><img alt="로고"></a>
<span>상여금/인센티브 지급</span><button>스크랩</button><div>[㈜케이디] 이너웨어 / 식품 카테고리 온라인 MD채용</div><div>㈜케이디</div><div>서울 송파구 외 14</div>
<div>백화점·유통·도소매, MD</div><button>즉시 지원</button><span>경력2년↑</span></div>
<div data-sentry-component="CardJob"><a href="https://www.jobkorea.co.kr/Recruit/GI_Read/102"><img></a>
<button>스크랩</button><div>[에이게임] 게임 채널 MD (온라인)</div><div>에이게임</div><div>서울 구로구</div><div>게임, MD</div><span>연봉 5,000만원~</span><button>즉시 지원</button><span>경력5년↑</span></div>
<div data-sentry-component="CardJob"><a href="/Recruit/GI_Read/103"><img></a>
<button>스크랩</button><div>[제이스] 화장품 브랜드사 온라인 MD</div><div>제이스</div><div>서울 마포구</div><div>생활화학·화장품, MD</div><button>즉시 지원</button><span>경력5년↑</span></div>
<div data-sentry-component="CardJob"><a href="/Recruit/GI_Read/104"><img></a>
<button>스크랩</button><div>이커머스 MD 모집</div><div>비비몰</div><div>경기 성남시</div><div>MD</div><button>즉시 지원</button><span>경력3~7년</span></div>'''
DETAIL = '''<html><head><meta property="og:title" content="에이게임 채용 - [에이게임] 게임 채널 MD | 잡코리아"></head><body><nav><a>기업·연봉</a></nav>
<div class="flex flex-col gap-[28px]"><div class="flex gap-[20px]"><span class="min-w-[80px]">고용형태</span><div>정규직</div></div>
<div class="flex gap-[20px]"><span class="min-w-[80px]">급여</span><div>회사 내규에 따름 (면접 후 결정)</div></div>
<div class="flex gap-[20px]"><span class="min-w-[80px]">근무지주소</span><div>서울 구로구 디지털로 1 <button>지도보기</button></div></div>
<div class="flex gap-[20px]"><span class="min-w-[80px]">경력</span><div>경력 (5년이상)</div></div></div></body></html>'''

cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
regions = cfg["regions"]
cards = parse_cards(CARDS)
assert [c["id"] for c in cards] == ["101", "102", "103", "104"], cards
assert cards[0]["title"].startswith("[㈜케이디]") and cards[0]["location"] == "서울 송파구 외 14" and cards[0]["exp_text"] == "경력2년↑"
assert cards[1]["salary_text"] == "연봉 5,000만원~" and cards[1]["tags"] == "게임, MD" and cards[1]["exp_text"] == "경력5년↑"
assert parse_exp("경력5년↑") == (5, None) and parse_exp("경력 (2년이상)") == (2, None) and parse_exp("경력3~7년") == (3, 7)
assert parse_exp("신입") == (0, 0) and parse_exp("경력무관") == (None, None)

def J(c):
    lo, hi = parse_exp(c["exp_text"])
    return {"title": c["title"], "company": c["company"], "location": c["location"], "tags": c["tags"], "exp_min": lo, "exp_max": hi}
verdicts = [quick_reject(J(c), cfg, regions) for c in cards]
# 101 식품(제목) 탈락 / 102 통과 / 103 화장품 탈락 / 104 성남(내 지역 밖) 탈락
assert verdicts == [True, False, True, True], verdicts

d = parse_detail(DETAIL)
assert d["근무지주소"] == "서울 구로구 디지털로 1" and d["고용형태"] == "정규직" and d["경력"] == "경력 (5년이상)", d
assert d["급여"].startswith("회사 내규") and d["_og"].startswith("에이게임 채용")
assert match_region(d["근무지주소"], regions) == "서울 구로구"

job = {"id": "x", "source": "jobkorea", "title": "[에이게임] 게임 채널 MD", "company": "에이게임", "location": d["근무지주소"],
       "exp_min": 5, "exp_max": None, "exp_text": d["경력"], "salary_text": d["급여"],
       "text": "[에이게임] 게임 채널 MD 에이게임 게임, MD 고용형태 정규직 급여 회사 내규에 따름", "url": "", "region": "서울 구로구"}
r = score(job, cfg)
assert r and r["score"] >= cfg["notify_threshold"], r
job["text"] += " 계약직"; job["exp_min"], job["exp_max"] = 0, 0
assert score(job, cfg) is None               # 신입만 채용은 탈락
# 경력 점수: 2~3년↑·경력무관은 감점, 4~8년↑·3~7년은 가점
def with_exp(text):
    lo, hi = parse_exp(text)
    j = dict(job, exp_min=lo, exp_max=hi, exp_text=text, text="[에이게임] 게임 채널 MD 에이게임 게임, MD 정규직")
    return score(j, cfg)
good, low2, low3, anyexp, rng = (with_exp(t) for t in ("경력5년↑", "경력2년↑", "경력 (3년이상)", "경력무관", "경력3~7년"))
assert good["score"] - low2["score"] >= 15 and good["score"] - low3["score"] >= 15, (good, low2, low3)
assert any("연차 낮음" in m for m in low2["minus"]) and any("경력무관" in m for m in anyexp["minus"])
assert rng["score"] == good["score"], (rng, good)
# 교육·훈련 과정 모집은 제외
assert quick_reject({"title": "[청년취업사관학교] [오아랩] 브랜드 MD", "company": "오아랩", "location": "서울 강남구", "tags": "", "exp_min": None, "exp_max": None}, cfg, regions)
print("파서 시험 통과, 점수:", r["score"])
