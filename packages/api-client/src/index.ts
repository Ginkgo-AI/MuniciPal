// Re-export generated client when available
// Run `pnpm generate-api` to generate the typed client from OpenAPI schema
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
