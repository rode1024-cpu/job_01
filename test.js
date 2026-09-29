const assert = require('assert');
const { analyze, splitPostings } = require('./engine');

const good = `회사명: 게임몰코리아
직무: 온라인MD (과장급)
[주요업무] 채널 전략 수립, 프로모션 기획, 매출 분석, 수요예측 및 발주, 플랫폼 협상
[자격요건] 경력 5~8년
[근무지] 서울 구로구 가산동
[연봉] 5,000 ~ 5,500만원
코스닥 상장사, 디자인팀·물류팀·CS팀 별도 운영. 게임, IT 디지털 주변기기 전문. 마감 2026-10-15`;
const g = analyze(good);
assert.strictEqual(g.verdict, '지원 추천', JSON.stringify(g.items.map(i => [i.key, i.v, i.pts])));
assert.ok(g.score >= 85);
assert.strictEqual(g.deadline, '2026-10-15');
assert.strictEqual(g.questions.length, 3);

const fashion = `여성 패션 의류 브랜드 온라인MD 모집. 패션 시즌 기획, 의류 발주. 경력 3~5년. 근무지 서울 성수동. 연봉 회사내규`;
const f = analyze(fashion);
assert.strictEqual(f.verdict, '패스');
assert.ok(f.score <= 35);

const junior = `이커머스 MD 신입 모집 게임 가전 부천 근무 연봉 3,200`;
assert.strictEqual(analyze(junior).verdict, '패스');

const far = `이커머스MD 경력 6년 이상, 가전·IT, 근무지 부산 해운대, 연봉 5,000`;
assert.strictEqual(analyze(far).verdict, '패스');

const naegyu = `채널MD 경력 5~7년 IT 가전 근무지 부천 연봉 회사내규 AMD 별도 채용`;
const n = analyze(naegyu);
assert.notStrictEqual(n.verdict, '패스');
assert.ok(n.questions[0].includes('연봉'));
assert.strictEqual(n.items.find(i => i.key === 'pay').v, '공고에 없음');

const messy = `브랜드MD 경력 5~8년 완구 캐릭터 IP 상세페이지 제작 및 촬영, CS 응대, 포장 출고, 올라운더 지향. 서울 강남구. 연봉 4,000`;
const m = analyze(messy);
assert.notStrictEqual(m.verdict, '지원 추천');
assert.strictEqual(m.items.find(i => i.key === 'org').v, '부적합');

assert.strictEqual(splitPostings(good + '\n=====\n' + fashion).length, 2);
console.log('ok', [g, f, n, m].map(a => a.verdict + ' ' + a.score).join(' | '));
