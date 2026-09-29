"""가짜 공고로 점수 규칙 확인: python test_scoring.py"""
import yaml
from scoring import score
cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
def J(title, company, loc, lo, hi, sal, extra=""):
    return {"id":"t","source":"saramin","title":title,"company":company,"location":loc,
            "exp_min":lo,"exp_max":hi,"exp_text":f"경력 {lo}~{hi}년" if lo else "",
            "salary_text":sal,"text":f"{title} {company} {loc} {sal} {extra}","url":""}
cases = [
 J("게임 온라인MD 과장급 채용","○○총판","경기 부천시",5,10,"4,800~5,500만원","콘솔 게임 채널전략 발주 수요예측"),
 J("가전 이커머스MD 채용","△△전자","서울 구로구",5,0,"회사내규에 따름","디지털 가전 프로모션 매출분석"),
 J("반려동물 브랜드MD","□□펫","서울 마포구",3,7,"면접 후 결정","펫 용품 입점 협상"),
 J("패션 온라인MD","◇◇어패럴","서울 강서구",5,8,"5,000만원"),
 J("이커머스MD","식품몰","서울 강남구",5,8,"4,000만원","식품 건강기능식품"),
 J("온라인MD 신입/경력","쇼핑몰","경기 부천시",0,2,"2,800만원"),
]
for c in cases:
    r = score(c, cfg)
    print(f"{(r['score'] if r else '탈락'):>4} | {c['title']} | {r and r['plus']} {r and r['minus']}")
