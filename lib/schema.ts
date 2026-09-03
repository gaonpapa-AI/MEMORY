import { z } from "zod";

export const SiteAnalysisSchema = z.object({
  siteName: z.string().describe("사이트 또는 서비스의 이름"),
  oneLineSummary: z.string().describe("사이트를 한 문장으로 요약"),
  category: z.string().describe("사이트가 속한 산업/카테고리 (예: 이커머스, SaaS, 미디어)"),
  targetAudience: z.string().describe("주요 타겟 사용자층"),
  coreFeatures: z
    .array(z.string())
    .min(3)
    .max(8)
    .describe("사이트의 핵심 기능 및 특징 목록"),
  valueProposition: z.string().describe("사용자에게 제공하는 핵심 가치"),
  businessModel: z.string().describe("추정되는 비즈니스 모델"),
  monetizationMethods: z
    .array(z.string())
    .min(1)
    .max(6)
    .describe("추정되는 수익화 방식 목록"),
  techSignals: z
    .array(z.string())
    .max(6)
    .describe("페이지에서 관찰된 기술적 특징이나 신호 (프레임워크, 도구 등 추정 포함)"),
  strengths: z.array(z.string()).min(2).max(6).describe("강점"),
  weaknesses: z.array(z.string()).min(2).max(6).describe("약점 또는 개선 여지"),
});

export const BusinessIdeaSchema = z.object({
  title: z.string().describe("신사업 아이디어 제목"),
  summary: z.string().describe("아이디어 요약 (2~3문장)"),
  reverseEngineeringInsight: z
    .string()
    .describe("원 사이트의 어떤 기능/구조/약점에서 착안했는지 설명"),
  targetMarket: z.string().describe("타겟 시장 및 고객"),
  differentiation: z.string().describe("원 사이트 및 기존 경쟁자와의 차별점"),
  monetizationModel: z.string().describe("예상 수익 모델"),
  difficulty: z
    .enum(["low", "medium", "high"])
    .describe("실행 난이도"),
  firstSteps: z
    .array(z.string())
    .min(2)
    .max(4)
    .describe("실행을 위한 첫 단계들"),
});

export const AnalysisResponseSchema = z.object({
  analysis: SiteAnalysisSchema,
  businessIdeas: z.array(BusinessIdeaSchema).min(3).max(5),
});

export type SiteAnalysis = z.infer<typeof SiteAnalysisSchema>;
export type BusinessIdea = z.infer<typeof BusinessIdeaSchema>;
export type AnalysisResponse = z.infer<typeof AnalysisResponseSchema>;

export type AnalysisResult = AnalysisResponse & {
  url: string;
  fetchedTitle: string | null;
};
