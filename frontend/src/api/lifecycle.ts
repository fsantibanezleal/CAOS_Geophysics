import { ApiClient } from "./client";
import { parseRawAsset, type RawAsset } from "./contracts";

export interface AccountView {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
}

export interface ProjectView {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface DeletionView {
  deleted: true;
  project_id: string;
  receipt_id: string;
  backup_erasure_status: "not_attempted";
  external_backup_status: "pending_reconciliation";
}

export interface RawUploadDeclaration {
  filename: string;
  mime: string;
  format: string;
  source: {
    provider: string;
    doi: string | null;
    citation: string | null;
    rights_statement: string;
    rights_decision: "mirror" | "provider-link-only" | "derivative-only";
    private_storage_permission: "attested";
    attribution: string;
    expected_bytes: number;
    expected_sha256: string;
  };
  physical: {
    coordinate_reference: "epsg" | "local";
    epsg: number | null;
    local_crs: string | null;
    axis_order: "xy" | "yx" | "lon_lat" | "lat_lon";
    horizontal_datum: string;
    vertical_datum: string;
    vertical_positive: "up" | "down";
    horizontal_unit: "m" | "km" | "degree";
    vertical_unit: "m" | "ft";
    measurement_unit: string;
    epoch_utc: string;
    component_frame: string;
    geometry: Record<string, string | number | string[] | Record<string, [number, number]>>;
  };
}

function record(value: unknown, context: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${context}: expected object`);
  return value as Record<string, unknown>;
}

function text(value: unknown, context: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${context}: expected text`);
  return value;
}

function time(value: unknown, context: string): string {
  const result = text(value, context);
  if (!/Z$|[+-]\d\d:\d\d$/.test(result) || Number.isNaN(Date.parse(result))) throw new Error(`${context}: expected timezone timestamp`);
  return result;
}

function uuid(value: unknown, context: string): string {
  const result = text(value, context);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(result)) throw new Error(`${context}: expected UUID`);
  return result;
}

export function parseAccount(value: unknown): AccountView {
  const user = record(value, "account");
  uuid(user.id, "account.id");
  text(user.email, "account.email");
  for (const key of ["is_active", "is_verified", "is_superuser"]) if (typeof user[key] !== "boolean") throw new Error(`account.${key}: expected boolean`);
  return value as AccountView;
}

export function parseProject(value: unknown): ProjectView {
  const project = record(value, "project");
  uuid(project.id, "project.id");
  text(project.name, "project.name");
  if (typeof project.description !== "string") throw new Error("project.description: expected text");
  time(project.created_at, "project.created_at");
  time(project.updated_at, "project.updated_at");
  return value as ProjectView;
}

function parseProjects(value: unknown): ProjectView[] {
  const wrapper = record(value, "projects");
  if (!Array.isArray(wrapper.projects)) throw new Error("projects: expected list");
  return wrapper.projects.map(parseProject);
}

function parseAssets(value: unknown): RawAsset[] {
  const wrapper = record(value, "assets");
  if (!Array.isArray(wrapper.assets)) throw new Error("assets: expected list");
  return wrapper.assets.map(parseRawAsset);
}

function parseDeletion(value: unknown): DeletionView {
  const deletion = record(value, "deletion");
  if (deletion.deleted !== true) throw new Error("deletion: not confirmed");
  uuid(deletion.project_id, "deletion.project_id");
  uuid(deletion.receipt_id, "deletion.receipt_id");
  if (deletion.backup_erasure_status !== "not_attempted" || deletion.external_backup_status !== "pending_reconciliation")
    throw new Error("deletion: unrecognized backup state");
  return value as unknown as DeletionView;
}

async function sha256(blob: Blob): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error("SHA-256 requires a secure browser context");
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}

function projectPath(projectId: string): string { return `/api/projects/${uuid(projectId, "project id")}`; }

export class LifecycleApi {
  constructor(private readonly api: ApiClient) {}

  private async csrf(signal?: AbortSignal): Promise<string> {
    const response = await this.api.requestJson("/api/auth/csrf", value => record(value, "csrf"), { signal });
    return text(response.csrf_token, "csrf token");
  }

  /** Also serves as an availability probe before showing authentication controls. */
  async probe(signal?: AbortSignal): Promise<AccountView | null> {
    await this.csrf(signal);
    try { return await this.me(signal); }
    catch (error) {
      if (error instanceof Error && "status" in error && error.status === 401) return null;
      throw error;
    }
  }

  me(signal?: AbortSignal): Promise<AccountView> { return this.api.requestJson("/api/auth/me", parseAccount, { signal }); }

  async register(email: string, password: string): Promise<AccountView> {
    return this.api.requestJson("/api/auth/register", parseAccount, { method: "POST", csrfToken: await this.csrf(), body: { email, password } });
  }

  async requestVerification(email: string): Promise<void> {
    await this.api.requestEmpty("/api/auth/verify/request-token", { method: "POST", csrfToken: await this.csrf(), body: JSON.stringify({ email }), headers: { "Content-Type": "application/json" } });
  }

  async verify(token: string): Promise<AccountView> {
    return this.api.requestJson("/api/auth/verify/verify", parseAccount, { method: "POST", csrfToken: await this.csrf(), body: { token } });
  }

  async login(email: string, password: string): Promise<AccountView> {
    await this.api.requestForm("/api/auth/cookie/login", new URLSearchParams({ username: email, password }), await this.csrf());
    return this.me();
  }

  async logout(): Promise<void> {
    await this.api.requestEmpty("/api/auth/cookie/logout", { method: "POST", csrfToken: await this.csrf() });
  }

  async forgotPassword(email: string): Promise<void> {
    await this.api.requestEmpty("/api/auth/reset-password/forgot-password", { method: "POST", csrfToken: await this.csrf(), body: JSON.stringify({ email }), headers: { "Content-Type": "application/json" } });
  }

  async resetPassword(token: string, password: string): Promise<void> {
    await this.api.requestEmpty("/api/auth/reset-password/reset-password", { method: "POST", csrfToken: await this.csrf(), body: JSON.stringify({ token, password }), headers: { "Content-Type": "application/json" } });
  }

  projects(signal?: AbortSignal): Promise<ProjectView[]> { return this.api.requestJson("/api/projects", parseProjects, { signal }); }

  async createProject(name: string, description: string): Promise<ProjectView> {
    return this.api.requestJson("/api/projects", parseProject, { method: "POST", csrfToken: await this.csrf(), body: { name, description } });
  }

  assets(projectId: string, signal?: AbortSignal): Promise<RawAsset[]> { return this.api.requestJson(`${projectPath(projectId)}/assets`, parseAssets, { signal }); }

  receipt(projectId: string, assetId: string): Promise<RawAsset> {
    return this.api.requestJson(`${projectPath(projectId)}/assets/${uuid(assetId, "asset id")}`, parseRawAsset);
  }

  async upload(projectId: string, file: File, declaration: Omit<RawUploadDeclaration, "filename" | "source"> & { source: Omit<RawUploadDeclaration["source"], "expected_bytes" | "expected_sha256"> }): Promise<RawAsset> {
    const hash = await sha256(file);
    const metadata: RawUploadDeclaration = {
      ...declaration,
      filename: file.name,
      source: { ...declaration.source, expected_bytes: file.size, expected_sha256: hash },
    };
    return this.api.requestUpload(`${projectPath(projectId)}/assets`, file, declaration.mime, JSON.stringify(metadata), parseRawAsset, await this.csrf());
  }

  async download(projectId: string, asset: RawAsset): Promise<Blob> {
    const expected = `${projectPath(projectId)}/assets/${uuid(asset.asset_id, "asset id")}/download`;
    if (asset.project_id !== projectId || asset.download_url !== expected) throw new Error("Receipt download path disagrees with selected project");
    const blob = await this.api.requestBlob(expected);
    if (blob.size !== asset.byte_count || await sha256(blob) !== asset.sha256) throw new Error("Downloaded bytes disagree with the upload receipt");
    return blob;
  }

  exportProject(projectId: string): Promise<Blob> { return this.api.requestBlob(`${projectPath(projectId)}/export`); }

  async deleteProject(projectId: string): Promise<DeletionView> {
    const result = await this.api.requestJson(projectPath(projectId), parseDeletion, { method: "DELETE", csrfToken: await this.csrf() });
    if (result.project_id !== projectId) throw new Error("Deletion receipt disagrees with selected project");
    return result;
  }
}
