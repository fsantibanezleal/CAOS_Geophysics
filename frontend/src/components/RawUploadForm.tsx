import { useState, type FormEvent } from "react";
import type { RawAsset } from "../api/contracts";
import { FORMAT_SPECS, UploadMetadataError, emptyUploadDraft, prepareUpload, type RawFormat, type UploadDraft } from "../api/upload-metadata";

type Declaration = ReturnType<typeof prepareUpload>;
type Props = { es: boolean; assets: RawAsset[]; busy: boolean; onSubmit: (file: File, declaration: Declaration) => Promise<void> };

export function RawUploadForm({ es, assets, busy, onSubmit }: Props) {
  const t = (en: string, spanish: string) => es ? spanish : en;
  const [draft, setDraft] = useState<UploadDraft>(emptyUploadDraft);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const spec = draft.format ? FORMAT_SPECS[draft.format] : null;
  const stationxmlAssets = assets.filter(asset => asset.detected_format === "stationxml");
  const update = <K extends keyof UploadDraft>(key: K, value: UploadDraft[K]) => setDraft(previous => ({ ...previous, [key]: value }));
  const textField = (key: keyof UploadDraft, en: string, spanish: string, props: { type?: string; placeholder?: string; required?: boolean } = {}) => (
    <label className="select-control" key={String(key)}><span>{t(en, spanish)}</span>
      <input className="select" type={props.type ?? "text"} placeholder={props.placeholder} required={props.required ?? true}
        value={draft[key] as string} onChange={event => update(key, event.target.value as UploadDraft[typeof key])} />
    </label>
  );
  const selectField = (key: keyof UploadDraft, en: string, spanish: string, options: readonly string[], labels?: Record<string, [string, string]>) => (
    <label className="select-control" key={String(key)}><span>{t(en, spanish)}</span>
      <select className="select" required value={draft[key] as string} onChange={event => update(key, event.target.value as UploadDraft[typeof key])}>
        <option value="">{t("Select…", "Seleccionar…")}</option>
        {options.map(option => <option key={option} value={option}>{labels?.[option] ? t(...labels[option]) : option}</option>)}
      </select>
    </label>
  );
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      const declaration = prepareUpload(file, draft, stationxmlAssets.map(asset => asset.asset_id));
      await onSubmit(file!, declaration);
    } catch (failure) {
      if (failure instanceof UploadMetadataError) setError(`${t("Complete or correct", "Completar o corregir")}: ${failure.fields.join(", ")}`);
      else setError(failure instanceof Error ? failure.message : t("Upload failed", "Falló la carga"));
    }
  };
  const channelCodes = (draft.geometry.channels ?? "").split(",").map(channel => channel.trim()).filter(Boolean);

  return <form className="project-form" onSubmit={submit}>
    <p className="project-note">{t("Private original-byte upload only. The receipt checks format and declared metadata, not observation QC or method eligibility.", "Carga privada de bytes originales. El recibo revisa formato y metadatos declarados, no control científico de observaciones ni elegibilidad de métodos.")}</p>
    <h3>{t("1. Original and format", "1. Original y formato")}</h3>
    <label className="select-control"><span>{t("Local original file", "Archivo original local")}</span><input className="select" type="file" required accept={spec?.extensions.join(",") ?? undefined} onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
    {file && <p className="project-note">{file.name} · {file.size.toLocaleString(es ? "es-CL" : "en-US")} bytes · {t("SHA-256 will be calculated before upload.", "SHA-256 se calculará antes de cargar.")}</p>}
    <label className="select-control"><span>{t("Declared raw format", "Formato original declarado")}</span>
      <select className="select" required value={draft.format} onChange={event => {
        const format = event.target.value as RawFormat | "";
        const next = format ? FORMAT_SPECS[format] : null;
        setDraft(previous => ({ ...previous, format, mime: next?.mimes[0] ?? "", measurementUnit: "", componentFrame: "", geometry: {}, orientation: {} }));
      }}><option value="">{t("Select format…", "Seleccionar formato…")}</option>
        {Object.entries(FORMAT_SPECS).map(([id, option]) => <option key={id} value={id}>{es ? option.es : option.en}</option>)}
      </select>
    </label>
    {spec && <>
      {selectField("mime", "Declared MIME type", "Tipo MIME declarado", spec.mimes)}
      <p className="project-note">{t("Accepted extension", "Extensión aceptada")}: {spec.extensions.join(", ")} · {t("limit", "límite")}: {spec.maxMiB} MiB</p>
    </>}

    <h3>{t("2. Provenance and rights", "2. Procedencia y derechos")}</h3>
    {textField("provider", "Provider or acquisition owner", "Proveedor o titular de adquisición")}
    {textField("doi", "DOI (if known)", "DOI (si se conoce)", { required: false })}
    {textField("citation", "Citation (if known)", "Cita (si se conoce)", { required: false })}
    <label className="select-control"><span>{t("Rights statement and permission basis", "Declaración de derechos y fundamento del permiso")}</span>
      <textarea className="select" minLength={10} required rows={3} value={draft.rightsStatement} onChange={event => update("rightsStatement", event.target.value)} />
    </label>
    {selectField("rightsDecision", "Public rights decision (does not publish this upload)", "Decisión de derechos públicos (no publica esta carga)", ["mirror", "provider-link-only", "derivative-only"], {
      mirror: ["Mirror permitted", "Se permite réplica"], "provider-link-only": ["Provider link only", "Solo enlace al proveedor"], "derivative-only": ["Derivatives only", "Solo derivados"],
    })}
    {textField("attribution", "Required attribution", "Atribución requerida")}
    <label className="project-attestation"><input type="checkbox" required checked={draft.privateStorageAttested} onChange={event => update("privateStorageAttested", event.target.checked)} />
      <span>{t("I attest I have permission to store this original privately in my account. This is separate from public redistribution rights.", "Declaro tener permiso para almacenar este original de forma privada en mi cuenta. Esto es distinto de los derechos de redistribución pública.")}</span>
    </label>

    <h3>{t("3. Physical reference and units", "3. Referencia física y unidades")}</h3>
    {selectField("coordinateReference", "Coordinate reference", "Referencia de coordenadas", ["epsg", "local"], { epsg: ["EPSG code", "Código EPSG"], local: ["Explicit local survey frame", "Marco local explícito"] })}
    {draft.coordinateReference === "epsg" && textField("epsg", "EPSG code", "Código EPSG", { type: "number" })}
    {draft.coordinateReference === "local" && textField("localCrs", "Local survey frame definition", "Definición del marco local")}
    {selectField("axisOrder", "Coordinate axis order", "Orden de ejes", ["xy", "yx", "lon_lat", "lat_lon"])}
    {textField("horizontalDatum", "Horizontal datum (exact declared name)", "Datum horizontal (nombre declarado exacto)")}
    {textField("verticalDatum", "Vertical datum", "Datum vertical")}
    {selectField("verticalPositive", "Positive vertical direction", "Dirección vertical positiva", ["up", "down"], { up: ["Up", "Arriba"], down: ["Down", "Abajo"] })}
    {selectField("horizontalUnit", "Horizontal coordinate unit", "Unidad horizontal", ["m", "km", "degree"])}
    {selectField("verticalUnit", "Vertical coordinate unit", "Unidad vertical", ["m", "ft"])}
    {spec && selectField("measurementUnit", "Measurement unit", "Unidad de medición", spec.units)}
    {textField("epochUtc", "Acquisition epoch with UTC offset (ISO 8601)", "Época de adquisición con zona UTC (ISO 8601)", { placeholder: "2026-09-27T12:00:00Z" })}
    {spec && selectField("componentFrame", "Component orientation/frame", "Orientación/marco de componentes", spec.frames)}

    {spec && <><h3>{t("4. Format geometry", "4. Geometría del formato")}</h3>
      <p className="project-note">{t("Enter exact source columns, identifiers, dimensions and channel orientations. Nothing is inferred from the file.", "Ingrese columnas, identificadores, dimensiones y orientaciones exactas. No se infieren del archivo.")}</p>
      {spec.geometry.map(geometryField => <label className="select-control" key={geometryField.key}><span>{es ? geometryField.es : geometryField.en}</span>
        {geometryField.kind === "stationxml" ? <select className="select" required value={draft.geometry[geometryField.key] ?? ""} onChange={event => update("geometry", { ...draft.geometry, [geometryField.key]: event.target.value })}>
          <option value="">{t("Choose an uploaded StationXML asset…", "Seleccionar un activo StationXML cargado…")}</option>
          {stationxmlAssets.map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.original_filename} · {asset.asset_id}</option>)}
        </select> : <input className="select" required type={geometryField.kind === "integer" || geometryField.kind === "number" ? "number" : "text"}
          step={geometryField.kind === "integer" ? "1" : geometryField.kind === "number" ? "any" : undefined}
          value={draft.geometry[geometryField.key] ?? ""} onChange={event => update("geometry", { ...draft.geometry, [geometryField.key]: event.target.value })} />}
      </label>)}
      {(draft.format === "miniseed" || draft.format === "stationxml" || draft.format === "mth5") && channelCodes.map(channel => <div className="project-channel" key={channel}>
        <strong>{channel}</strong>
        <label className="select-control"><span>{t("Azimuth (°; 0–<360)", "Acimut (°; 0–<360)")}</span><input className="select" type="number" step="any" required value={draft.orientation[channel]?.azimuth ?? ""} onChange={event => update("orientation", { ...draft.orientation, [channel]: { azimuth: event.target.value, dip: draft.orientation[channel]?.dip ?? "" } })} /></label>
        <label className="select-control"><span>{t("Dip (°; −90–90)", "Inclinación (°; −90–90)")}</span><input className="select" type="number" step="any" required value={draft.orientation[channel]?.dip ?? ""} onChange={event => update("orientation", { ...draft.orientation, [channel]: { azimuth: draft.orientation[channel]?.azimuth ?? "", dip: event.target.value } })} /></label>
      </div>)}
    </>}
    {error && <p role="alert" className="project-error">{error}</p>}
    <button className="btn primary" type="submit" disabled={busy || !file}>{busy ? t("Checking and uploading…", "Revisando y cargando…") : t("Upload original bytes", "Cargar bytes originales")}</button>
  </form>;
}
