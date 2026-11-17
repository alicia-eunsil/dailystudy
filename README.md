# Daily Study — 평일 아침 회화 영어

월~금 한국 시간 오전 7시, Gmail에서 회사 메일로 **영어 문장 3개 + 한국어 뜻 + 짧은 설명 하나**를 보냅니다. 중상급 회화 중심으로 여행·업무·일상에서 활용할 표현을 담았습니다.

- 첫 콘텐츠: 4주 / 20회 / 60문장. 월~목 새 표현, 금요일 응용 복습.
- 4주 후에는 같은 콘텐츠를 반복합니다. 실시간 웹 수집이나 AI 생성은 하지 않습니다.
- Python 표준 라이브러리만 사용하며 유료 API 키나 별도 서버가 필요하지 않습니다.
- 메일 기능은 `study_mail.py`로 실행합니다.

## 메일 연결 (최초 한 번)

1. 발신 Gmail 계정에서 [2단계 인증](https://myaccount.google.com/security)을 설정하고 [앱 비밀번호](https://myaccount.google.com/apppasswords)를 만듭니다. 일반 로그인 비밀번호 대신 앱 비밀번호를 사용합니다. 계정 정책에 따라 앱 비밀번호를 사용할 수 없을 수 있습니다. [Google 안내](https://support.google.com/accounts/answer/185833?hl=ko)
2. [저장소 Actions Secrets](https://github.com/alicia-eunsil/dailystudy/settings/secrets/actions)에 다음 세 값을 등록합니다. 주소도 공개 소스에 넣지 않습니다.

| Secret 이름 | 값 |
|---|---|
| `GMAIL_ADDRESS` | 발신 Gmail 주소 |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 |
| `RECIPIENT_EMAIL` | 수신 회사 메일 주소 |

3. [Daily English Actions](https://github.com/alicia-eunsil/dailystudy/actions/workflows/daily-english.yml) → **Run workflow** → `preview`로 메일 미리보기를 확인합니다. 실행 결과의 `email-preview` 아티팩트에 HTML과 텍스트가 있습니다.
4. 평일에 `send`를 선택하면 실제 발송합니다. 같은 날 이미 발송했거나 발송 예약이 남아 있으면 건너뜁니다. 주말에는 수동 실행해도 보내지 않습니다.
5. 이후 월~금 오전 7시 자동 실행합니다. [GitHub 예약 실행](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)은 혼잡 시 지연·누락될 수 있어 정확한 도착 시각을 보장하지 않습니다. 공개 저장소는 60일간 활동이 없으면 예약 실행이 비활성화될 수 있습니다.

회사 보안 정책으로 메일이 격리되면 회사 메일의 스팸함과 수신 정책을 확인하세요. Gmail 수락 로그는 회사 메일함 도착 확인을 의미하지 않습니다.

## 로컬 미리보기와 검사

Python 3.11 이상에서 실행합니다. 별도 패키지 설치가 필요하지 않습니다.

```bash
python3 study_mail.py preview --lesson 1
python3 study_mail.py validate
python3 -m unittest discover -s tests -v
```

미리보기 파일은 `preview/email.html`이며 계정 연결 없이 생성됩니다. 기본 실행도 미리보기입니다.

## 커리큘럼과 운영

- [커리큘럼 설계와 참고 자료](docs/CURRICULUM.md)
- 콘텐츠: `curriculum/lessons.json` — 학습일마다 문장 3개, 한국어 뜻, 포인트 하나.
- 발송: `.github/workflows/daily-english.yml` — UTC 일~목 22시 = 한국 월~금 07시.
- 중간 요일에 시작하면 그 요일 수업부터 시작합니다. 예: 수요일 첫 발송은 3회차, 금요일은 5회차입니다. 첫 주에 놓친 앞부분은 다음 순환 때 받습니다. 매주 월요일에 다음 주제로 넘어갑니다.
- 콘텐츠는 자동으로 늘어나지 않습니다. 5회 단위로 학습 주를 추가하고 ID를 연속으로 지정하면 전체 콘텐츠를 순환합니다.
- 실제 발송 전 `mail_state/state.json`에 예약을 커밋하고, SMTP 성공 후 상태를 `sent`로 바꿉니다. 주소와 비밀번호는 기록하지 않습니다. 워크플로에는 `contents: write`가 필요하며 main 브랜치 보호로 봇의 푸시가 막히면 발송 전에 실패합니다.
- SMTP 연결 중단 등으로 발송 여부가 불확실할 때는 중복 방지를 우선하여 자동 재시도하지 않습니다. `reserved`는 발송 성공을 뜻하지 않습니다. Gmail 보낸편지함·수신함 확인 후 미발송이 확실한 경우에만 해당 날짜 항목을 삭제·커밋하고 평일 당일 `send`를 재실행하세요. 이전 날짜 메일은 자동 보충하지 않습니다.
- 예약 커밋 이후 취소되거나 발송 성공 기록 푸시가 실패해도 예약은 남습니다. 내용 확장이나 설정 변경 전 `git pull --rebase`로 발송 기록을 가져오세요.
- 자동 발송 중지는 Actions에서 Daily English → Disable workflow로 설정합니다.
