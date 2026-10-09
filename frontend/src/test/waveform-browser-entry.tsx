// Isolated integration-test mount, excluded from the production HTML/router.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { AppShell, applyTheme, readTheme, useShellLang, type ShellConfig } from "@fasl-work/caos-app-shell";
import "@fasl-work/caos-app-shell/styles.css";
import "../styles.css";
import { architecture } from "../architecture";
import { WaveformProjectWorkbench } from "../components/WaveformProjectWorkbench";
import { ProjectDrawer } from "../components/ProjectDrawer";

applyTheme(readTheme());
const config: ShellConfig = {
  product: { name: "Inverse Earth Studio" },
  routes: [{path:"/",en:"Waveform QA",es:"QA de ondas"}],
  links: { github:"https://github.com/fsantibanezleal/CAOS_Geophysics" },
  version:"0.04.001", architecture, fixedRoutes:["/"],
  visibility: "public",
  contain: true,
  license: {
    en: "Apache-2.0 code and CC-BY-4.0 content",
    es: "Código Apache-2.0 y contenido CC-BY-4.0",
  },
  footer: {disclaimer:{en:"Isolated loopback integration test; not a public activation.",es:"Prueba aislada local; no es activación pública."}},
};
function IntegrationMount(){
  const es=useShellLang()==="es", [manage,setManage]=useState(false);
  const [project,setProject]=useState(new URLSearchParams(location.search).get("project")??"");
  return <><WaveformProjectWorkbench key={project} projectId={project} es={es} onManage={()=>setManage(true)} onCurated={()=>setManage(true)}/>
    {manage&&<ProjectDrawer es={es} onClose={()=>setManage(false)} onOpenWorkbench={id=>{setProject(id);setManage(false);history.replaceState(null,"",`/?project=${id}`);}} onOwnerCleared={()=>setProject("")}/>}</>;
}
createRoot(document.getElementById("root")!).render(<BrowserRouter><AppShell config={config}><IntegrationMount/></AppShell></BrowserRouter>);
