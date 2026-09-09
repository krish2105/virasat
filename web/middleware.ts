import { NextResponse, type NextRequest } from "next/server";

const PROTECTED = ["/queue", "/changes", "/visits", "/audit", "/health", "/dossier", "/buildings"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PROTECTED.some((p) => pathname.startsWith(p)) && !req.cookies.get("virasat_session")) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/((?!api|_next|.*\\..*).*)"] };
