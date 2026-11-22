import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { existsSync } from "node:fs";
import { isAbsolute, resolve, dirname } from "node:path";

function external(name:string){
  const value=process.env[name];
  if(!value||!isAbsolute(value))throw new Error(`${name} must explicitly select external storage`);
  const root=resolve(value);
  for(let parent=root;;parent=dirname(parent)){
    if(existsSync(resolve(parent,".git")))throw new Error(`${name} must be outside any checkout`);
    if(parent===dirname(parent))break;
  }
  return root;
}
export default defineConfig({base:"/",publicDir:false,cacheDir:external("GEOPHYSICS_QA_CACHE"),plugins:[react()],
  build:{outDir:external("GEOPHYSICS_QA_DIST"),emptyOutDir:false,rollupOptions:{input:"qa-waveform.html"}},
});
