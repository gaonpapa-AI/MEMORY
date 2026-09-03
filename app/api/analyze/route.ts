import { NextResponse } from "next/server";
import { scrapeSite, ScrapeError } from "@/lib/scrape";
import { analyzeSite, AnalysisError } from "@/lib/analyze";
import type { AnalysisResult } from "@/lib/schema";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "잘못된 요청입니다." }, { status: 400 });
  }

  const url = (body as { url?: unknown })?.url;
  if (typeof url !== "string" || url.trim().length === 0) {
    return NextResponse.json({ error: "URL을 입력해주세요." }, { status: 400 });
  }

  try {
    const site = await scrapeSite(url);
    const result = await analyzeSite(site);

    const payload: AnalysisResult = {
      url: site.finalUrl,
      fetchedTitle: site.title,
      ...result,
    };

    return NextResponse.json(payload);
  } catch (err) {
    if (err instanceof ScrapeError) {
      return NextResponse.json({ error: err.message }, { status: 422 });
    }
    if (err instanceof AnalysisError) {
      return NextResponse.json({ error: err.message }, { status: 502 });
    }
    console.error(err);
    return NextResponse.json(
      { error: "서버에서 알 수 없는 오류가 발생했습니다." },
      { status: 500 },
    );
  }
}
