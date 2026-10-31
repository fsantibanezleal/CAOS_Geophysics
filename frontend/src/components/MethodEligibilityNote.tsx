export function MethodEligibilityNote({ lane, reason, reasonFields, es }: {
  lane: string; reason: string; reasonFields?: string[]; es: boolean;
}) {
  return <p className="project-note" role="status">
    {es ? "No disponible" : "Unavailable"} · {lane} · {reason}
    {reasonFields?.length ? <><br />{es ? "Campos que debe revisar" : "Fields to review"}: {reasonFields.map((field, index) =>
      <span key={field}>{index > 0 ? ", " : ""}<code>{field}</code></span>)}</> : null}
  </p>;
}
