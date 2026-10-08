/** Private loopback leaf harness. Real supplied view/receipt, no API impersonation. */
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { AppShell, useLangStore, applyTheme } from "@fasl-work/caos-app-shell";
import "@fasl-work/caos-app-shell/styles.css";
import { verifyMagneticView } from "../../frontend/src/api/magnetic-result";
import { MagneticSurveyResult } from "../../frontend/src/components/MagneticSurveyResult";

async function mount() {
  const params=new URLSearchParams(location.search), lang=params.get("lang")==="es"?"es":"en";
  useLangStore.setState({lang}); applyTheme(params.get("theme")==="dark"?"dark":"light");
  document.documentElement.lang=lang;
  const [value,expected]=await Promise.all([fetch("/view.json").then(r=>r.json()),fetch("/receipt.json").then(r=>r.json())]);
  const verified=await verifyMagneticView(value,expected);
  const exportBundle=()=>{const link=document.createElement('a');link.href='/export.zip';link.download='magnetic-numeric.zip';link.click();};
  createRoot(document.getElementById("root")!).render(<BrowserRouter><AppShell config={{product:{name:"Magnetic result local QA"},routes:[{path:"/",en:"Result",es:"Resultado"}],links:{github:"https://github.com/fsantibanezleal/CAOS_Geophysics"},version:"0.04.001",footer:{disclaimer:{en:"Private local leaf verification; no authenticated API or field acceptance",es:"Verificación local privada; sin aceptación de API autenticada ni campo"}}}}>
    <div className="page-body wide"><MagneticSurveyResult value={verified} onExport={exportBundle}/></div>
  </AppShell></BrowserRouter>);
}
void mount().catch(error=>{document.getElementById("root")!.textContent=String(error);console.error(error);});
