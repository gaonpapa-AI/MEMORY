import * as cheerio from "cheerio";

const FETCH_TIMEOUT_MS = 12_000;
const MAX_BODY_TEXT_CHARS = 12_000;
const MAX_RESPONSE_BYTES = 5 * 1024 * 1024; // 5MB guard

export class ScrapeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ScrapeError";
  }
}

export interface ScrapedSite {
  finalUrl: string;
  title: string | null;
  metaDescription: string | null;
  ogTitle: string | null;
  ogDescription: string | null;
  headings: string[];
  navLinks: string[];
  bodyText: string;
  techSignals: string[];
}

function normalizeUrl(input: string): URL {
  let candidate = input.trim();
  if (!/^https?:\/\//i.test(candidate)) {
    candidate = `https://${candidate}`;
  }
  let url: URL;
  try {
    url = new URL(candidate);
  } catch {
    throw new ScrapeError("올바른 URL 형식이 아닙니다.");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new ScrapeError("http 또는 https 주소만 지원합니다.");
  }
  return url;
}

export async function scrapeSite(input: string): Promise<ScrapedSite> {
  const url = normalizeUrl(input);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      signal: controller.signal,
      redirect: "follow",
      headers: {
        "User-Agent":
          "Mozilla/5.0 (compatible; SiteAnalyzerBot/1.0; +personal-research-tool)",
        Accept: "text/html,application/xhtml+xml",
      },
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ScrapeError("사이트 응답 시간이 초과되었습니다.");
    }
    throw new ScrapeError("사이트에 접속할 수 없습니다. 주소를 확인해주세요.");
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    throw new ScrapeError(`사이트가 오류를 반환했습니다 (HTTP ${response.status}).`);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("text/html") && !contentType.includes("xml")) {
    throw new ScrapeError("HTML 페이지가 아닙니다.");
  }

  const contentLength = Number(response.headers.get("content-length") ?? 0);
  if (contentLength > MAX_RESPONSE_BYTES) {
    throw new ScrapeError("페이지 용량이 너무 큽니다.");
  }

  const html = await response.text();
  const $ = cheerio.load(html);

  $("script, style, noscript, svg, iframe").remove();

  const title = $("title").first().text().trim() || null;
  const metaDescription =
    $('meta[name="description"]').attr("content")?.trim() || null;
  const ogTitle = $('meta[property="og:title"]').attr("content")?.trim() || null;
  const ogDescription =
    $('meta[property="og:description"]').attr("content")?.trim() || null;

  const headings = $("h1, h2, h3")
    .map((_, el) => $(el).text().trim())
    .get()
    .filter(Boolean)
    .slice(0, 30);

  const navLinks = $("nav a, header a")
    .map((_, el) => $(el).text().trim())
    .get()
    .filter(Boolean)
    .slice(0, 30);

  const bodyText = $("body")
    .text()
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_BODY_TEXT_CHARS);

  const techSignals: string[] = [];
  if ($('meta[name="generator"]').attr("content")) {
    techSignals.push(`generator: ${$('meta[name="generator"]').attr("content")}`);
  }
  if ($("#__next").length) techSignals.push("Next.js/React 흔적 (#__next)");
  if ($("[data-reactroot]").length) techSignals.push("React 흔적");
  if ($("script[src*='shopify']").length || html.includes("cdn.shopify.com")) {
    techSignals.push("Shopify 흔적");
  }
  if (html.includes("wp-content") || html.includes("wp-includes")) {
    techSignals.push("WordPress 흔적");
  }

  return {
    finalUrl: response.url || url.toString(),
    title,
    metaDescription,
    ogTitle,
    ogDescription,
    headings,
    navLinks,
    bodyText,
    techSignals,
  };
}
