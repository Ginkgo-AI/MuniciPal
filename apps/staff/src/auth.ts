import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      name: "Municipal Staff Login",
      credentials: {
        username: { label: "Username", type: "text" },
        code: { label: "Code", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.code) return null;

        try {
          const res = await fetch("http://localhost:8080/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              username: credentials.username,
              code: credentials.code,
            }),
          });

          if (!res.ok) return null;
          const data = await res.json();

          if (data.success && data.token) {
            return {
              id: data.user_id,
              name: data.display_name,
              token: data.token,
            };
          }
          return null;
        } catch {
          return null;
        }
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.apiToken = (user as Record<string, unknown>).token;
      }
      return token;
    },
    async session({ session, token }) {
      (session as unknown as Record<string, unknown>).apiToken = token.apiToken;
      return session;
    },
  },
});
