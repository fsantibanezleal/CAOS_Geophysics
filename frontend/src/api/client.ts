export class ApiHttpError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string) {
    super(message);
    this.name = "ApiHttpError";
  }
}

export interface ApiRequest {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  csrfToken?: string;
  query?: URLSearchParams;
}

/** Transport only. No endpoint is called by the released UI until backend parity is verified. */
export class ApiClient {
  constructor(
    private readonly origin: string,
    private readonly transport: typeof fetch = fetch,
  ) {
    const parsed = new URL(origin);
    if (!/^https?:$/.test(parsed.protocol) || parsed.origin !== origin || parsed.pathname !== "/")
      throw new Error("API origin must be an exact HTTP(S) origin");
    if (typeof window !== "undefined" && origin !== window.location.origin)
      throw new Error("API origin must match the application origin");
  }

  async requestJson<T>(path: string, parse: (value: unknown) => T, request: ApiRequest = {}): Promise<T> {
    if (!/^\/api\/[a-z0-9_-]+(?:\/[a-z0-9_-]+)*$/i.test(path))
      throw new Error("API path must stay under the same-origin /api/ namespace");
    const method = request.method ?? "GET";
    if (method === "GET" && request.body !== undefined) throw new Error("GET cannot contain a body");
    if (method !== "GET" && !request.csrfToken?.trim()) throw new Error("CSRF token required for unsafe API request");
    const url = new URL(path, this.origin);
    if (request.query) url.search = request.query.toString();
    const response = await this.transport(url, {
      method,
      credentials: "same-origin",
      redirect: "error",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(request.body === undefined ? {} : { "Content-Type": "application/json" }),
        ...(method === "GET" ? {} : { "X-CSRF-Token": request.csrfToken! }),
      },
      body: request.body === undefined ? undefined : JSON.stringify(request.body),
      signal: request.signal,
    });
    const contentType = response.headers.get("content-type") ?? "";
    if (!response.ok) {
      let code = "http-error";
      let message = `HTTP ${response.status}`;
      if (/\bapplication\/(?:problem\+)?json\b/i.test(contentType)) {
        const payload: unknown = await response.json();
        if (payload && typeof payload === "object" && !Array.isArray(payload)) {
          const error = payload as Record<string, unknown>;
          if (typeof error.code === "string") code = error.code;
          if (typeof error.message === "string") message = error.message;
        }
      }
      throw new ApiHttpError(response.status, code, message);
    }
    if (!/\bapplication\/(?:[\w.-]+\+)?json\b/i.test(contentType))
      throw new Error("API returned a non-JSON success response");
    return parse(await response.json());
  }
}
