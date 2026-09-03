import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { AnalysisResponseSchema, type AnalysisResponse } from "./schema";
import type { ScrapedSite } from "./scrape";

const client = new Anthropic();

export class AnalysisError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AnalysisError";
  }
}

function buildPrompt(site: ScrapedSite): string {
  return `아래는 한 웹사이트에서 수집한 정보다. 이 정보를 바탕으로 (1) 사이트를 상세히 분석하고, (2) 이 사이트를 역설계(reverse engineering)하여 만들 수 있는 새로운 사업 아이디어 3~5개를 도출하라.

역설계란: 이 사이트가 어떤 문제를 어떻게 풀고 있는지 분해한 뒤, 그 구조에서 (a) 다루지 않는 인접 시장/세그먼트, (b) 약점이나 미충족 니즈, (c) 다른 수익모델이나 다른 타겟으로의 변형 등을 찾아내 새로운 사업 기회로 재구성하는 것을 의미한다. 단순히 "비슷한 사이트를 만들자"가 아니라 구체적이고 실행 가능한 차별화 지점을 제시해야 한다.

[수집된 정보]
URL: ${site.finalUrl}
페이지 제목: ${site.title ?? "(없음)"}
메타 설명: ${site.metaDescription ?? "(없음)"}
OG 제목: ${site.ogTitle ?? "(없음)"}
OG 설명: ${site.ogDescription ?? "(없음)"}

주요 헤딩:
${site.headings.map((h) => `- ${h}`).join("\n") || "(없음)"}

네비게이션/헤더 링크 텍스트:
${site.navLinks.map((n) => `- ${n}`).join("\n") || "(없음)"}

관찰된 기술 신호:
${site.techSignals.join(", ") || "(없음)"}

본문 텍스트 (일부 발췌):
${site.bodyText || "(추출된 본문 없음)"}

모든 결과는 한국어로 작성하라.`;
}

export async function analyzeSite(site: ScrapedSite): Promise<AnalysisResponse> {
  try {
    const response = await client.messages.parse({
      model: "claude-opus-5",
      max_tokens: 16000,
      messages: [{ role: "user", content: buildPrompt(site) }],
      output_config: {
        format: zodOutputFormat(AnalysisResponseSchema),
      },
    });

    if (response.stop_reason === "refusal") {
      throw new AnalysisError("분석 요청이 거부되었습니다.");
    }

    if (!response.parsed_output) {
      throw new AnalysisError("분석 결과를 해석하지 못했습니다. 다시 시도해주세요.");
    }

    return response.parsed_output;
  } catch (err) {
    if (err instanceof AnalysisError) throw err;
    if (err instanceof Anthropic.AuthenticationError) {
      throw new AnalysisError("Claude API 인증에 실패했습니다. API 키를 확인해주세요.");
    }
    if (err instanceof Error && err.message.includes("Could not resolve authentication method")) {
      throw new AnalysisError(
        "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env.local 파일에 API 키를 설정해주세요.",
      );
    }
    if (err instanceof Anthropic.RateLimitError) {
      throw new AnalysisError("요청이 너무 많습니다. 잠시 후 다시 시도해주세요.");
    }
    if (err instanceof Anthropic.APIError) {
      throw new AnalysisError(`Claude API 오류: ${err.message}`);
    }
    throw new AnalysisError("분석 중 알 수 없는 오류가 발생했습니다.");
  }
}
