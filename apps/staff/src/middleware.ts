export { auth as middleware } from "@/auth";

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/sessions/:path*",
    "/approvals/:path*",
  ],
};
