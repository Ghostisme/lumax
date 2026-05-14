import { NextResponse, type NextRequest } from "next/server";

const NEW_CHAT_PATH = "/workspace/chats/new";

export function middleware(request: NextRequest) {
  const redirectUrl = request.nextUrl.clone();
  redirectUrl.pathname = NEW_CHAT_PATH;

  return NextResponse.redirect(redirectUrl);
}

export const config = {
  matcher: "/",
};
