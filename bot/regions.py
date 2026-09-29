"""내가 정한 지역(config.yaml의 regions)과 공고 근무지를 맞춰본다."""
import re


def _norm(s):
    return re.sub(r"[\s>·,/()\-]+", "", s or "")


def _tokens(region):
    """'서울 구로구' -> ['서울', '구로'], '부천시' -> ['부천'], '인천 서구' -> ['인천', '서구']"""
    toks = []
    for t in region.split():
        base = re.sub(r"(시|구|군)$", "", t)
        toks.append(base if len(base) >= 2 else t)   # '서구'처럼 짧아지면 그대로 둠
    return toks


def match_region(location, regions):
    """근무지 문자열이 regions 중 어디에 속하는지. 없으면 None (목록 순서대로 먼저 맞는 지역)."""
    loc = _norm(location)
    if not loc:
        return None
    for reg in regions:
        if all(t in loc for t in _tokens(reg)):
            return reg
    return None
