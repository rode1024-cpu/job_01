/* 채용공고 판정 엔진 — 규칙(키워드) 기반. 브라우저/Node 공용. */
(function (root) {
  'use strict';

  var W = { role: 15, exp: 5, cat: 20, work: 15, loc: 15, pay: 10, org: 10, size: 10 };
  var RATIO = { '적합': 1, '애매': 0.5, '부적합': 0, '공고에 없음': 0.6 };

  function snipAt(t, i, len) {
    var s = Math.max(0, i - 15), e = Math.min(t.length, i + len + 25);
    return '…' + t.slice(s, e).replace(/\s+/g, ' ').trim() + '…';
  }

  // srcs(정규식 문자열 배열) 전체 히트 수, 매칭된 단어, 첫 근거 문구
  function H(t, srcs) {
    var n = 0, words = [], first = '';
    srcs.forEach(function (s) {
      var re = new RegExp(s, 'gi'), m, c = 0;
      while ((m = re.exec(t))) {
        c++;
        if (!first) first = snipAt(t, m.index, m[0].length);
        if (m[0].length === 0) re.lastIndex++;
      }
      if (c) { n += c; var f = new RegExp(s, 'i').exec(t); words.push(f[0]); }
    });
    return { n: n, words: words, ev: first };
  }

  var CAT_GOOD = ['게임', '\\bIT\\b', '디지털', '가전', '생활용품', '생활가전', '리빙', '취미', '컴퓨터', '노트북', '주변기기', '스마트폰', '전자기기', '콘텐츠 상품'];
  var CAT_REVIEW = ['완구', '장난감', '캐릭터', '\\bIP\\b', '피규어', '반려', '애견', '애묘', '펫', '자동차\\s*용품', '카\\s*용품'];
  var CAT_EXCL = ['패션', '의류', '어패럴', '화장품', '뷰티', '코스메틱', '식품', '푸드', '건강기능', '건기식', '영양제'];

  var ROLE_STRONG = ['온라인\\s*MD', '채널\\s*MD', '이커머스\\s*MD', 'e-?commerce\\s*MD', '브랜드\\s*MD', '플랫폼\\s*MD', '온라인\\s*(?:상품\\s*)?기획'];
  var ROLE_WEAK = ['\\bMD\\b', '상품\\s*기획', '바이어', '머천다이저'];

  var WORK = [
    ['채널 전략', ['채널\\s*(?:전략|운영|확장|믹스)']],
    ['프로모션', ['프로모션', '기획전', '할인\\s*행사', '이벤트\\s*기획', '행사\\s*기획']],
    ['매출 분석', ['매출\\s*분석', '실적\\s*분석', '데이터\\s*분석', '성과\\s*분석', '손익']],
    ['수요예측', ['수요\\s*예측', '판매\\s*예측', '재고\\s*(?:관리|운영)', '재고\\s*회전']],
    ['발주', ['발주', '입고\\s*관리', '사입']],
    ['협상', ['협상', '제휴', '입점\\s*(?:협의|관리)', '벤더', '거래처', '플랫폼\\s*(?:협의|담당|대응)', '브랜드사?\\s*(?:협의|대응)']]
  ];
  var WORK_TIP = {
    '채널 전략': '채널별 매출 비중을 어떻게 바꿨는지 숫자로',
    '프로모션': '기획전·프로모션 하나를 골라 목표 대비 결과로',
    '매출 분석': '분석에서 액션까지 이어진 사례 하나',
    '수요예측': '예측과 실제 판매 차이를 어떻게 줄였는지',
    '발주': '발주 주기와 재고 회전을 관리한 방식',
    '협상': '플랫폼·브랜드와 조건을 조율한 사례'
  };

  var ORG_POS = ['\\bAMD\\b', '어시스턴트', '디자인\\s*팀', '물류\\s*팀', 'CS\\s*팀', '고객\\s*(?:센터|만족팀)', '촬영\\s*팀', '콘텐츠\\s*팀', '운영\\s*지원'];
  var ORG_NEG = ['상세\\s*페이지', '촬영', 'CS\\s*(?:응대|업무)', '고객\\s*응대', '문의\\s*응대', '포장', '출고', '1인\\s*다역', '올라운더', '멀티\\s*플레이어'];

  var SIZE_STRONG = ['상장', '코스닥', '코스피', 'KOSDAQ', '대기업', '중견', '계열사', '그룹사', '총판', '공식\\s*(?:유통|수입)', '매출\\s*\\d{3,}\\s*억', '\\d+\\s*개\\s*브랜드', '임직원\\s*\\d{3,}'];
  var SIZE_SMALL = ['스타트업', '시드', '소수\\s*정예', '초기\\s*멤버', '창업\\s*\\d\\s*년'];

  // [정규식, 라벨, 부천 기준 예상 분, 등급 ok|mid|far]
  var LOC = [
    ['부천', '부천', 25, 'ok'], ['광명', '경기 광명', 25, 'ok'],
    ['구로|가산|금천|독산', '서울 구로·금천', 30, 'ok'],
    ['영등포|여의도|문래|당산', '서울 영등포·여의도', 35, 'ok'],
    ['강서|마곡|발산|화곡|김포공항|등촌|가양', '서울 강서·마곡', 40, 'ok'],
    ['양천|목동|신정|신월', '서울 양천', 35, 'ok'],
    ['관악|신림|동작|사당|노량진', '서울 관악·동작', 50, 'ok'],
    ['마포|상암|디지털미디어시티|홍대|합정|공덕', '서울 마포·상암', 50, 'ok'],
    ['은평|서대문|신촌|불광', '서울 서부', 55, 'ok'],
    ['용산|중구|종로|시청|을지로|서울역|광화문', '서울 도심', 55, 'mid'],
    ['강남|서초|송파|삼성동|역삼|선릉|잠실', '서울 강남권', 65, 'mid'],
    ['성수|성동|광진|강동|강북|노원|동대문|성북|중랑|도봉|건대', '서울 동·북부', 75, 'mid'],
    ['시흥|정왕|배곧|월곶', '경기 시흥', 35, 'ok'],
    ['안산|반월|시화', '경기 안산', 50, 'ok'],
    ['김포|고촌|풍무', '경기 김포', 45, 'ok'],
    ['고양|일산|덕양|화정', '경기 고양', 60, 'ok'],
    ['안양|군포|의왕|과천|평촌', '경기 안양·군포', 45, 'mid'],
    ['파주|운정', '경기 파주', 80, 'mid'],
    ['부평|계양|청라|검단|석남|가좌', '인천 서·북부', 30, 'ok'],
    ['인천|송도|남동|연수|논현|미추홀', '인천', 60, 'mid'],
    ['판교|성남|분당|하남|용인|수원|화성|동탄|평택|오산|이천|여주|경기\\s*광주|남양주|구리|의정부|양주|포천|안성|광교', '경기 남·동·북부', 80, 'far'],
    ['부산|대구|대전|광주광역|울산|세종|제주|강원|충청|충북|충남|전라|전북|전남|경상|경북|경남|천안|아산|청주|창원|포항', '지방', 150, 'far']
  ];

  function parseExp(t) {
    var m = t.match(/(\d{1,2})\s*(?:년)?\s*[~\-–∼]\s*(\d{1,2})\s*년/);
    if (m) return { min: +m[1], max: +m[2], ev: snipAt(t, m.index, m[0].length) };
    m = t.match(/(\d{1,2})\s*년\s*(?:이상|↑)/);
    if (m) return { min: +m[1], max: null, ev: snipAt(t, m.index, m[0].length) };
    m = t.match(/(\d{1,2})\s*년\s*(?:이하|미만)/);
    if (m) return { min: null, max: +m[1], ev: snipAt(t, m.index, m[0].length) };
    m = t.match(/경력\s*무관/);
    if (m) return { min: null, max: null, any: true, ev: snipAt(t, m.index, m[0].length) };
    m = t.match(/신입/);
    if (m && !/경력/.test(t)) return { min: 0, max: 0, ev: snipAt(t, m.index, m[0].length) };
    return null;
  }

  function parseSalary(t) {
    var nn = /회사\s*내규|내규에?\s*따|면접\s*(?:후\s*)?(?:결정|협의)|추후\s*협의|협의/.test(t);
    var nums = [], ev = '', re = /(?:연봉|급여|salary|보수|초봉)[^\n]{0,40}/gi, m;
    while ((m = re.exec(t))) {
      var seg = m[0], before = nums.length, x;
      var r1 = /(\d{1,2}),?(\d{3})/g;
      while ((x = r1.exec(seg))) { var v = +(x[1] + x[2]); if (v >= 2500 && v <= 15000) nums.push(v); }
      var r2 = /(\d)\s*천\s*(?:(\d)\s*백)?/g;
      while ((x = r2.exec(seg))) nums.push(+x[1] * 1000 + (x[2] ? +x[2] * 100 : 0));
      if (nums.length > before && !ev) ev = snipAt(t, m.index, seg.length);
    }
    if (!nums.length) return { nn: nn, ev: nn ? snipAt(t, t.search(/회사\s*내규|내규|협의/), 4) : '' };
    return { min: Math.min.apply(null, nums), max: Math.max.apply(null, nums), nn: nn, ev: ev };
  }

  function findLoc(t) {
    var win = t, a = t.search(/근무\s*(?:지|위치|처)|근무지역|위치|주소|본사/);
    if (a >= 0) win = t.slice(a, a + 120);
    function best(txt) {
      var b = null;
      LOC.forEach(function (L) {
        var m = new RegExp(L[0], 'i').exec(txt);
        if (m && (!b || m.index < b.idx)) b = { idx: m.index, len: m[0].length, L: L };
      });
      return b && { L: b.L, ev: snipAt(txt, b.idx, b.len) };
    }
    var r = best(win) || best(t);
    if (r) return r;
    var m2 = /서울/.exec(t);
    if (m2) return { L: ['', '서울(구 정보 없음)', 50, 'mid'], ev: snipAt(t, m2.index, 2) };
    var m3 = /경기/.exec(t);
    if (m3) return { L: ['', '경기(시·구 정보 없음)', 60, 'mid'], ev: snipAt(t, m3.index, 2) };
    return null;
  }

  function item(key, label, v, ev, note, extra) {
    var max = W[key], o = { key: key, label: label, v: v, ev: ev || '', note: note || '', max: max, pts: Math.round(max * RATIO[v] * 10) / 10 };
    for (var k in (extra || {})) o[k] = extra[k];
    return o;
  }

  function analyze(text, meta) {
    var t = String(text || '').replace(/\r/g, '');
    var items = [], gates = [];

    // 직무
    var rs = H(t, ROLE_STRONG), rw = H(t, ROLE_WEAK), roleItem;
    if (rs.n) roleItem = item('role', '직무', '적합', rs.ev, '');
    else if (rw.n) roleItem = item('role', '직무', '애매', rw.ev, '', { concern: 'MD라고는 돼 있는데 온라인·채널·이커머스 성격인지 공고만으론 불분명해요.', q: '이 포지션이 담당하는 채널(온라인/오프라인)과 주요 카테고리는 무엇인가요?' });
    else roleItem = item('role', '직무', '부적합', '', '', { concern: '온라인/채널/이커머스/브랜드 MD 직무로 보이는 문구가 없어요.' });
    items.push(roleItem);

    // 경력
    var ex = parseExp(t), exItem;
    if (!ex) exItem = item('exp', '경력', '공고에 없음', '', '', { q: '기대하시는 경력 연차와 팀 내 직급 구성은 어떻게 되나요?' });
    else if ((ex.max != null && ex.max <= 3) || (ex.min != null && ex.min >= 10)) {
      exItem = item('exp', '경력', '부적합', ex.ev, '경력 요구가 5~8년에서 크게 벗어나요.', { gate: true });
      gates.push('경력 요구(' + (ex.max != null && ex.max <= 3 ? ex.max + '년 이하' : ex.min + '년 이상') + ')가 내 연차와 안 맞음');
    } else if (ex.any) exItem = item('exp', '경력', '적합', ex.ev, '경력 무관');
    else {
      var lo = ex.min == null ? 0 : ex.min, hi = ex.max == null ? 99 : ex.max;
      var ov = Math.min(hi, 8) - Math.max(lo, 5);
      if (ov >= 2 || (ex.max == null && lo <= 8 && lo >= 3)) exItem = item('exp', '경력', '적합', ex.ev);
      else exItem = item('exp', '경력', '애매', ex.ev, '', { concern: '경력 범위(' + (ex.min == null ? '' : ex.min) + '~' + (ex.max == null ? '' : ex.max) + '년)가 내 연차와 겨우 걸쳐요. 직급이 낮게 잡힐 수 있어요.', q: '이 포지션의 직급(과장/대리)과 팀 내 보고 라인은 어떻게 되나요?' });
    }
    items.push(exItem);

    // 카테고리
    var g = H(t, CAT_GOOD), rv = H(t, CAT_REVIEW), xc = H(t, CAT_EXCL);
    var head = t.slice(0, 200), xh = H(head, CAT_EXCL).n, gh = H(head, CAT_GOOD).n + H(head, CAT_REVIEW).n;
    var xw = xc.n + xh, gw = g.n + rv.n + gh, catItem;
    if (xc.n >= 2 && xw > gw) {
      catItem = item('cat', '카테고리', '부적합', xc.ev, '제외 카테고리(' + xc.words.join('·') + ')가 주력으로 보여요.', { gate: true });
      gates.push('제외 카테고리(' + xc.words.join('·') + ')가 주력');
    } else if (xc.n && g.n < 2) {
      catItem = item('cat', '카테고리', '애매', xc.ev, '', { concern: '제외 카테고리 키워드(' + xc.words.join('·') + ')가 있어요. 담당 카테고리가 어느 쪽인지 확인이 필요해요.', q: '담당 카테고리별 매출 비중은 어떻게 되나요?' });
    } else if (g.n >= 2) catItem = item('cat', '카테고리', '적합', g.ev, g.words.join('·'));
    else if (g.n === 1 || rv.n) {
      var ev2 = g.n ? g.ev : rv.ev;
      catItem = item('cat', '카테고리', '애매', ev2, '', { concern: rv.n && !g.n ? '검토 가능 카테고리(' + rv.words.join('·') + ')라서 매출 규모와 성장성을 따져봐야 해요.' : '선호 카테고리 언급이 한 번뿐이라 주력인지 불분명해요.', q: '주력 카테고리와 매출 비중, 신규 카테고리 확장 계획이 있나요?' });
    } else catItem = item('cat', '카테고리', '공고에 없음', '', '', { q: '주력 카테고리와 매출 비중은 어떻게 되나요?' });
    items.push(catItem);

    // 업무
    var tags = [];
    WORK.forEach(function (w) { var h = H(t, w[1]); if (h.n) tags.push({ tag: w[0], ev: h.ev }); });
    if (tags.length >= 3) items.push(item('work', '업무', '적합', tags[0].ev, tags.map(function (x) { return x.tag; }).join('·')));
    else if (tags.length) items.push(item('work', '업무', '애매', tags[0].ev, tags.map(function (x) { return x.tag; }).join('·'), { concern: '좋아하는 업무가 ' + tags.length + '개(' + tags.map(function (x) { return x.tag; }).join('·') + ')만 보여요. 나머지는 실제 권한을 확인해야 해요.', q: '발주·수요예측·가격 결정에서 이 포지션이 가지는 권한 범위는 어디까지인가요?' }));
    else items.push(item('work', '업무', '공고에 없음', '', '', { q: '발주·수요예측·프로모션 기획 중 실제 비중이 큰 업무는 무엇인가요?' }));

    // 지역
    var lc = findLoc(t), locItem;
    if (!lc) locItem = item('loc', '지역', '공고에 없음', '', '', { q: '근무지 위치와 유연근무·재택 여부를 알 수 있을까요?' });
    else {
      var L = lc.L, note = '부천 기준 대중교통 약 ' + L[2] + '분 [검증 필요]';
      if (L[3] === 'ok') locItem = item('loc', '지역', '적합', lc.ev, L[1] + ' · ' + note);
      else if (L[3] === 'mid') locItem = item('loc', '지역', '애매', lc.ev, L[1] + ' · ' + note, { concern: L[1] + ' 근무라 ' + note + '. 왕복 시간이 부담될 수 있어요.', q: '유연근무·재택·셔틀 지원이 있나요?' });
      else { locItem = item('loc', '지역', '부적합', lc.ev, L[1] + ' · ' + note, { gate: true }); gates.push('근무지(' + L[1] + ')가 출퇴근하기 어려움'); }
    }
    items.push(locItem);

    // 연봉
    var sal = parseSalary(t), payItem;
    if (sal.min == null) payItem = item('pay', '연봉', '공고에 없음', sal.ev, sal.nn ? '회사내규/협의 — 감점 없이 질문으로 확인' : '', { q: '이 포지션의 연봉 범위(밴드)와 성과급 구조는 어떻게 되나요? (기준: 4,800 이상)' });
    else if (sal.max >= 4800) payItem = item('pay', '연봉', '적합', sal.ev, (sal.max >= 5000 && sal.min <= 5500 ? '5,000~5,500 적극 검토 구간 · ' : '') + sal.min + '~' + sal.max + '만원');
    else if (sal.max >= 4200) payItem = item('pay', '연봉', '애매', sal.ev, sal.max + '만원', { concern: '연봉 상단이 ' + sal.max + '만원이라 4,800 기준에 못 미쳐요.', q: '연봉 협상 여지와 성과급·인센티브 구조는 어떻게 되나요?' });
    else payItem = item('pay', '연봉', '부적합', sal.ev, sal.max + '만원', { concern: '연봉 상단이 ' + sal.max + '만원으로 기준(4,800)보다 꽤 낮아요.', q: '연봉 범위 상단과 협상 여지가 있나요?' });
    items.push(payItem);

    // 조직 분리
    var op = H(t, ORG_POS), on = H(t, ORG_NEG), orgItem;
    if (on.n >= 2 && !(op.n >= 2)) orgItem = item('org', '조직 분리', '부적합', on.ev, '담당 업무에 ' + on.words.join('·') + ' 포함', { concern: '담당 업무에 ' + on.words.join('·') + '이(가) 섞여 있어요. MD 외 업무를 같이 하는 구조일 수 있어요.', q: 'MD 1명이 담당하는 채널 수와 SKU 규모는? 상세페이지·촬영·CS는 어느 팀이 맡나요?' });
    else if (on.n) orgItem = item('org', '조직 분리', '애매', on.ev, '부정 신호: ' + on.words.join('·') + (op.n ? ' / 긍정 신호: ' + op.words.join('·') : ''), { concern: '"' + on.words[0] + '" 언급이 있어서 업무 범위가 MD 밖으로 번질 수 있어요.', q: 'MD 1명이 담당하는 채널 수와 SKU 규모는? ' + on.words[0] + ' 업무는 어느 정도 비중인가요?' });
    else if (op.n) orgItem = item('org', '조직 분리', '적합', op.ev, '긍정 신호: ' + op.words.join('·'));
    else orgItem = item('org', '조직 분리', '공고에 없음', '', '', { q: 'MD/AMD/디자인/물류/CS 역할은 어떻게 나뉘어 있나요? MD 1명당 SKU 규모도 궁금해요.' });
    items.push(orgItem);

    // 회사 규모
    var ss = H(t, SIZE_STRONG), sm = H(t, SIZE_SMALL), sz = null, sizeItem;
    var em = /(?:직원|임직원|구성원)\D{0,6}(\d[\d,]*)\s*명/.exec(t);
    if (em) sz = +em[1].replace(/,/g, '');
    if (ss.n || (sz != null && sz >= 100)) sizeItem = item('size', '회사 규모', '적합', ss.ev || snipAt(t, em.index, em[0].length), ss.words.join('·') + (sz ? ' 직원 ' + sz + '명' : ''));
    else if (sm.n || (sz != null && sz < 30)) sizeItem = item('size', '회사 규모', '애매', sm.ev || snipAt(t, em.index, em[0].length), '', { concern: '작은 조직일 가능성이 있어요(' + (sm.words[0] || '직원 ' + sz + '명') + ').', q: '운영 브랜드·채널 수와 MD 조직 규모는 어떻게 되나요?' });
    else sizeItem = item('size', '회사 규모', '공고에 없음', '', '', { q: '운영 중인 브랜드·채널 수와 MD 조직 규모는 어떻게 되나요?' });
    items.push(sizeItem);

    var score = Math.round(items.reduce(function (s, i) { return s + i.pts; }, 0));
    var gated = gates.length > 0;
    if (gated) score = Math.min(score, 35);
    var verdict = gated ? '패스' : score >= 70 ? '지원 추천' : score >= 50 ? '검토 후 지원' : '패스';

    var pos = items.filter(function (i) { return i.v === '적합'; }).sort(function (a, b) { return b.max - a.max; });
    var neg = items.filter(function (i) { return i.v === '부적합' || i.v === '애매'; }).sort(function (a, b) { return (a.v === b.v ? 0 : a.v === '부적합' ? -1 : 1) || b.max - a.max; });
    var reason;
    if (gated) reason = gates.join(', ') + '이라 패스예요.';
    else if (pos.length && neg.length) reason = pos[0].label + ' 쪽은 잘 맞는데 ' + neg[0].label + ' 쪽이 걸려요.';
    else if (pos.length) reason = pos.slice(0, 2).map(function (i) { return i.label; }).join('·') + ' 쪽은 조건에 잘 맞아요.';
    else reason = '공고에서 확인되는 맞는 조건이 거의 없어요.';

    var concerns = neg.filter(function (i) { return i.concern; }).slice(0, 3).map(function (i) { return i.concern; });
    if (gated) gates.forEach(function (g2) { if (concerns.length < 3) concerns.unshift('탈락 조건: ' + g2); });
    concerns = concerns.slice(0, 3);
    if (concerns.length < 2) {
      items.filter(function (i) { return i.v === '공고에 없음' && (i.key === 'org' || i.key === 'size' || i.key === 'pay'); }).forEach(function (i) {
        if (concerns.length < 2) concerns.push(i.label + ' 정보가 공고에 없어요. 직접 확인해야 해요.');
      });
    }

    // 질문: 연봉 확인은 항상 포함(내규/미기재 시), 나머지는 걸리는 순서
    var qs = [];
    function addQ(q) { if (q && qs.indexOf(q) < 0) qs.push(q); }
    if (payItem.v === '공고에 없음') addQ(payItem.q);
    neg.forEach(function (i) { addQ(i.q); });
    items.filter(function (i) { return i.v === '공고에 없음'; }).forEach(function (i) { addQ(i.q); });
    ['org', 'work', 'size'].forEach(function (k) { var it = items.filter(function (i) { return i.key === k; })[0]; if (qs.length < 3 && it) addQ(it.q || null); });
    var defaults = ['MD 1명이 담당하는 채널 수와 SKU 규모는?', '이 포지션이 발주·수요예측·가격 결정에서 가지는 권한은 어디까지인가요?', '입사 후 첫 3개월에 기대하는 성과는 무엇인가요?'];
    defaults.forEach(function (q) { if (qs.length < 3) addQ(q); });
    qs = qs.slice(0, 3);

    // 강조 포인트
    var strengths = [];
    tags.forEach(function (x) { strengths.push({ title: x.tag, ev: x.ev, tip: WORK_TIP[x.tag] }); });
    if (catItem.v === '적합' || catItem.v === '애매') strengths.push({ title: '카테고리 경험', ev: catItem.ev, tip: '해당 상품군을 직접 다뤄봤다면 그 이야기로 시작' });
    if (roleItem.v === '적합') strengths.push({ title: '직무 적합', ev: roleItem.ev, tip: '온라인/채널 MD로서 담당한 범위(채널 수·SKU 수)를 숫자로' });
    strengths = strengths.slice(0, 2);

    // 메타
    var company = (meta && meta.company) || '', title = (meta && meta.title) || '';
    var mc = /(?:회사명|회사|기업명|기업)\s*[:：]\s*(.+)/.exec(t), mt = /(?:직무|포지션|모집\s*분야|공고명|모집\s*직무)\s*[:：]\s*(.+)/.exec(t);
    if (!company && mc) company = mc[1].trim().slice(0, 40);
    if (!title && mt) title = mt[1].trim().slice(0, 50);
    if (!title) { var fl = t.split('\n').map(function (s) { return s.trim(); }).filter(Boolean)[0]; if (fl) title = fl.slice(0, 40); }

    return { company: company, title: title, score: score, verdict: verdict, reason: reason, items: items, gates: gates, concerns: concerns, questions: qs, strengths: strengths, deadline: parseDeadline(t) };
  }

  function parseDeadline(t, now) {
    now = now || new Date();
    var m = /(?:마감|접수\s*기간|모집\s*기간|지원\s*기간|~)[^\n]{0,30}?(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})/.exec(t);
    if (m) return m[1] + '-' + ('0' + m[2]).slice(-2) + '-' + ('0' + m[3]).slice(-2);
    m = /(?:마감|~)\s*(\d{1,2})\s*[./월]\s*(\d{1,2})/.exec(t);
    if (m) {
      var y = now.getFullYear(), d = new Date(y, +m[1] - 1, +m[2]);
      if (d < new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30)) y++;
      return y + '-' + ('0' + m[1]).slice(-2) + '-' + ('0' + m[2]).slice(-2);
    }
    return '';
  }

  function splitPostings(text) {
    return String(text || '').split(/\n\s*(?:={3,}|-{3,}|#{3,}|_{3,})\s*\n/).map(function (s) { return s.trim(); }).filter(function (s) { return s.length > 30; });
  }

  var api = { analyze: analyze, splitPostings: splitPostings, parseDeadline: parseDeadline };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.JobEngine = api;
})(typeof window !== 'undefined' ? window : this);
