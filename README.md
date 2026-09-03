# 웹사이트 분석 & 역설계

웹사이트 주소를 입력하면 해당 사이트를 상세히 분석(핵심 기능, 타겟, 비즈니스 모델, 강점/약점 등)하고,
그 결과를 역설계하여 새로운 사업 아이디어를 도출해주는 개인용 웹 서비스입니다.

Next.js (App Router) + TypeScript + Claude API로 만들어졌습니다.

## 동작 방식

1. 사용자가 URL을 입력하면 서버(`app/api/analyze/route.ts`)가 해당 페이지를 가져와 (`lib/scrape.ts`)
   제목, 메타 정보, 헤딩, 본문 텍스트 등을 추출합니다.
2. 추출한 내용을 Claude API(`lib/analyze.ts`)에 전달해 구조화된 JSON(사이트 분석 + 신사업 아이디어)을 받습니다.
3. 결과를 화면에 카드 형태로 보여주고, 브라우저 로컬 스토리지에 최근 분석 기록을 저장합니다.

## 시작하기

1. 의존성 설치

```bash
npm install
```

2. Claude API 키 설정

`.env.local.example`을 참고해 `.env.local` 파일을 만들고 `ANTHROPIC_API_KEY`를 설정하세요.

```bash
cp .env.local.example .env.local
```

3. 개발 서버 실행

```bash
npm run dev
```

[http://localhost:3000](http://localhost:3000) 에서 확인할 수 있습니다.

## 주요 파일

- `app/page.tsx` — URL 입력 폼과 분석 결과 UI
- `app/api/analyze/route.ts` — 분석 API 엔드포인트
- `lib/scrape.ts` — 대상 사이트 크롤링 및 텍스트 추출
- `lib/analyze.ts` — Claude API 호출 및 구조화된 출력 파싱
- `lib/schema.ts` — 분석 결과의 Zod 스키마
