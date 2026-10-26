/** Parent-mounted owned composition, not a replacement Workbench or default grant. */
import {useEffect,useMemo,useRef,useState} from 'react';
import {SurveyIntakePanel} from './SurveyIntakePanel';
import {SurveyInstrument,type SurveySourceChoice} from './SurveyInstrument';
import type {MagneticLineSurveyApi} from './api';
import {SurveyActionGate} from './actionCustody';

export function SurveyWorkflowLeaf({api,projectId,sources}:{api:MagneticLineSurveyApi;projectId:string;sources:SurveySourceChoice[]}) {
  const [published,setPublished]=useState<{project:string;source:SurveySourceChoice}[]>([]),[active,setActive]=useState(false);
  const gate=useRef(new SurveyActionGate()),[pendingAction,setPendingAction]=useState(false);
  const claimAction=()=>{
    const lease=gate.current.claim(projectId);if(!lease)return null;
    setPendingAction(true);
    return {project:lease.project,release:()=>{
      const released=lease.release();if(released)setPendingAction(false);return released;
    }};
  };
  useEffect(()=>{setPublished([]);setActive(false);},[projectId]);
  const choices=useMemo(()=>[...sources,...published.filter(v=>v.project===projectId&&!sources.some(s=>s.id===v.source.id)).map(v=>v.source)],
    [sources,published,projectId]);
  return <>
    <SurveyIntakePanel api={api} projectId={projectId} disabled={active||pendingAction} claimAction={claimAction}
      onDataset={source=>setPublished(prior=>[...prior,{project:projectId,source}])}/>
    <SurveyInstrument api={api} projectId={projectId} sources={choices} onActivityChange={setActive}
      actionsDisabled={pendingAction} claimAction={claimAction}/>
  </>;
}
