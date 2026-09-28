export class ApiHttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly fields: string[] = [],
  ) {
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

interface WireRequest {
  method?: ApiRequest["method"];
  body?: BodyInit;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  csrfToken?: string;
  query?: URLSearchParams;
}

function apiPath(path: string): void {
  if (!/^\/api\/[a-z0-9_-]+(?:\/[a-z0-9_-]+)*$/i.test(path))
    throw new Error("API path must stay under the same-origin /api/ namespace");
}

async function responseError(response: Response): Promise<ApiHttpError> {
  let code = "http-error";
  let message = `HTTP ${response.status}`;
  let fields: string[] = [];
  if (/\bapplication\/(?:[\w.-]+\+)?json\b/i.test(response.headers.get("content-type") ?? "")) {
    const payload: unknown = await response.json().catch(() => null);
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      const error = payload as Record<string, unknown>;
      if (typeof error.code === "string") code = error.code;
      if (typeof error.message === "string") message = error.message;
      if (Array.isArray(error.fields)) fields = error.fields.filter((field): field is string => typeof field === "string");
      if (typeof error.detail === "string") { code = error.detail; message = error.detail.replaceAll("_", " "); }
      if (Array.isArray(error.detail)) {
        fields = error.detail.map(item => {
          if (!item || typeof item !== "object") return "";
          const loc = (item as { loc?: unknown }).loc;
          return Array.isArray(loc) ? loc.filter(part => typeof part === "string" || typeof part === "number").join(".") : "";
        }).filter(Boolean);
        message = "Request fields are invalid";
        code = "validation_error";
      }
    }
  }
  return new ApiHttpError(response.status, code, message, fields);
}

/** Same-origin cookie/CSRF transport. No credential or API base URL is persisted. */
export class ApiClient {
  constructor(
    private readonly origin: string,
    private readonly transport: typeof fetch = globalThis.fetch.bind(globalThis),
  ) {
    const parsed = new URL(origin);
    if (!/^https?:$/.test(parsed.protocol) || parsed.origin !== origin || parsed.pathname !== "/")
      throw new Error("API origin must be an exact HTTP(S) origin");
    if (typeof window !== "undefined" && origin !== window.location.origin)
      throw new Error("API origin must match the application origin");
  }

  private async send(path: string, request: WireRequest = {}): Promise<Response> {
    apiPath(path);
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
        ...request.headers,
        ...(method === "GET" ? {} : { "X-CSRF-Token": request.csrfToken! }),
      },
      body: request.body,
      signal: request.signal,
    });
    if (!response.ok) throw await responseError(response);
    return response;
  }

  async requestJson<T>(path: string, parse: (value: unknown) => T, request: ApiRequest = {}): Promise<T> {
    const response = await this.send(path, {
      ...request,
      headers: request.body === undefined ? undefined : { "Content-Type": "application/json" },
      body: request.body === undefined ? undefined : JSON.stringify(request.body),
    });
    if (!/\bapplication\/(?:[\w.-]+\+)?json\b/i.test(response.headers.get("content-type") ?? ""))
      throw new Error("API returned a non-JSON success response");
    return parse(await response.json());
  }

  async requestEmpty(path: string, request: WireRequest): Promise<void> {
    await this.send(path, request);
  }

  async requestForm(path: string, form: URLSearchParams, csrfToken: string): Promise<void> {
    await this.requestEmpty(path, { method: "POST", body: form, csrfToken, headers: { "Content-Type": "application/x-www-form-urlencoded" } });
  }

  async requestUpload<T>(path: string, file: Blob, mime: string, metadata: string, parse: (value: unknown) => T, csrfToken: string): Promise<T> {
    if (new TextEncoder().encode(metadata).length > 16384) throw new Error("Upload metadata exceeds 16 KiB");
    const response = await this.send(path, {
      method: "POST", body: file, csrfToken,
      headers: { "Content-Type": mime, "X-Asset-Metadata": metadata },
    });
    if (!/\bapplication\/(?:[\w.-]+\+)?json\b/i.test(response.headers.get("content-type") ?? ""))
      throw new Error("API returned a non-JSON upload receipt");
    return parse(await response.json());
  }

  async requestBlob(path: string, request: Pick<ApiRequest, "signal" | "query"> = {}): Promise<Blob> {
    const response = await this.send(path, request);
    if (/\bapplication\/(?:[\w.-]+\+)?json\b/i.test(response.headers.get("content-type") ?? ""))
      throw new Error("API returned JSON instead of downloadable bytes");
    return response.blob();
  }
}
