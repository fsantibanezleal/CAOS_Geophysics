/** Check owned magnetic leaf against explicitly supplied existing packages. */
import { resolve, dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const i=process.argv.indexOf("--packages"); if(i<0||!process.argv[i+1])throw Error("Explicit --packages required");
const packages=resolve(process.argv[i+1]), repo=resolve(dirname(fileURLToPath(import.meta.url)),"..");
const ts=(await import(pathToFileURL(join(packages,"typescript/lib/typescript.js")).href)).default;
const options={strict:true,noEmit:true,noUnusedLocals:true,noUnusedParameters:true,skipLibCheck:true,esModuleInterop:true,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,moduleResolution:ts.ModuleResolutionKind.Bundler,jsx:ts.JsxEmit.ReactJSX,baseUrl:packages,typeRoots:[join(packages,"@types")],types:["react","node"],lib:["lib.es2022.d.ts","lib.dom.d.ts","lib.dom.iterable.d.ts"]};
const files=["frontend/src/api/magnetic-result.ts","frontend/src/api/magnetic-processing.ts","frontend/src/components/MagneticSurveyResult.tsx","frontend/src/components/MagneticSurveyCourse.tsx","frontend/src/data/magnetic-survey-course.ts","frontend/src/test/magnetic-model-states.test.ts","tests/ui/magnetic_leaf.tsx"].map(p=>join(repo,p));
options.paths={react:["@types/react/index.d.ts"],"react/*":["@types/react/*"],"react-dom/*":["@types/react-dom/*"]};
const host=ts.createCompilerHost(options);
host.resolveModuleNames=(names,containing)=>names.map(name=>ts.resolveModuleName(name,containing,options,host).resolvedModule??ts.resolveModuleName(name,join(packages,"__m04_type_resolution__.ts"),options,host).resolvedModule);
const program=ts.createProgram(files,options,host), diagnostics=ts.getPreEmitDiagnostics(program);
if(diagnostics.length){console.error(ts.formatDiagnosticsWithColorAndContext(diagnostics,{getCurrentDirectory:()=>repo,getCanonicalFileName:x=>x,getNewLine:()=>"\n"}));process.exitCode=1;}else console.log("Owned magnetic frontend strict type check passed (existing explicit runtime, no install).");
