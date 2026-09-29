# 구직 알림봇 (사람인 + 잡코리아 → 텔레그램)

## 1. 텔레그램 봇 만들기 (5분)
1. 텔레그램에서 @BotFather 검색 → /newbot → 이름 정하기 → 토큰 복사 (TELEGRAM_TOKEN)
2. 만든 봇에게 아무 메시지나 1번 보내기
3. 브라우저에서 https://api.telegram.org/bot<토큰>/getUpdates 접속 → "chat":{"id":숫자} 복사 (TELEGRAM_CHAT_ID)

## 2. 사람인 API 키 받기 (승인 대기 있음)
1. https://oapi.saramin.co.kr 에서 이용신청
2. 승인 후 로그인 → 앱 등록 → 내 앱리스트에서 access-key 복사 (SARAMIN_KEY)
   - 승인 전에도 잡코리아만으로 먼저 돌려볼 수 있음

## 3. GitHub에 올리기

2. 이 폴더 파일 전부 업로드 (.github 폴더 포함)
3. Settings → Secrets and variables → Actions → New repository secret 3개 등록
   SARAMIN_KEY / TELEGRAM_TOKEN / TELEGRAM_CHAT_ID
4. Actions 탭 → job-alert → Run workflow 로 첫 실행 → 폰에 알림 오는지 확인

## 4. 조건 바꾸기
config.yaml 만 수정하면 됨. 알림이 너무 많으면 notify_threshold를 올리고, 적으면 내리기.
점수 규칙을 바꾼 뒤엔 `python test_scoring.py` 로 가짜 공고 점수를 확인.

## 5. 로컬 테스트
pip install -r requirements.txt
SARAMIN_KEY=키 python main.py --dry-run   (텔레그램 대신 화면에 출력, 기록 저장 안 함)

## 6. 웹앱과의 관계
- 봇은 공고 목록 정보만 보고 후보를 거르고, 상세 판정은 저장소 루트의 웹앱(`index.html`)에 공고를 붙여넣어서 해요.
- 점수 배점은 웹앱과 같아요(직무 15, 경력 5, 카테고리 20, 업무 15, 지역 15, 연봉 10, 조직·규모 10). 알림 기준은 50점 이상, ★는 70점 이상이에요.
- 저장소 루트의 `.github/workflows/job-alert.yml`이 `bot/` 폴더를 실행해요. Secrets 3개만 등록하면 돼요.

## 7. 알림 받을 지역 정하기
`config.yaml`의 `regions`에 원하는 지역을 한 줄에 하나씩 적으면, 그 지역 공고만 지역별로 묶여서 와요.
```yaml
regions:
  - 부천시
  - 서울 구로구
  - 서울 강남구
```
- 구 이름이 겹칠 수 있어서(강서구는 서울·부산에 있어요) `서울 강서구`처럼 앞에 서울/경기/인천을 붙이세요.
- 목록에 없는 지역 공고는 알림 없이 넘어가요. 근무지가 안 적힌 공고는 기본으로 제외하고, `unknown_region: send`로 바꾸면 "지역 미확인"으로 따로 와요.
- 지역별로 한 번에 최대 5건(`max_alerts_per_run`)이에요.
- 봇은 전국 검색 결과에서 걸러내는 방식이라, 검색 결과에 없는 지역 공고는 못 잡을 수 있어요.
