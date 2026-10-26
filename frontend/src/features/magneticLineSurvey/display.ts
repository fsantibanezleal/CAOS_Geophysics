/** Display-only ordinal mapping; no magnetic/scientific computation. */
export function profileOrdinal(svgX:number,rows:number):number|null {
  if(!Number.isFinite(svgX)||!Number.isSafeInteger(rows)||rows<1||rows>4096)return null;
  return Math.max(0,Math.min(rows-1,Math.round((svgX-55)/560*(rows-1))));
}

export interface DisplayWindowBinding {
  job_id:string; result_sha256:string; view:'lines'|'validation'|'grid';
  selection:number; first:number;
}
/** Refuse stale asynchronous windows before React's clearing effect runs. */
export function sameDisplayWindow(saved:DisplayWindowBinding,current:DisplayWindowBinding):boolean {
  return saved.job_id===current.job_id&&saved.result_sha256===current.result_sha256&&
    saved.view===current.view&&saved.selection===current.selection&&saved.first===current.first;
}
