import {describe,it,expect} from 'vitest';
import {SurveyActionGate} from './actionCustody';
describe('owned in-view action lease, not native drain',()=>{
  it('claims synchronously before sibling or duplicate submission',()=>{
    const gate=new SurveyActionGate();
    expect(gate.claim('')).toBeNull();expect(gate.busy).toBe(false);
    const first=gate.claim('project-a');expect(first?.project).toBe('project-a');
    expect(gate.busy).toBe(true);expect(gate.claim('project-a')).toBeNull();
  });
  it('keeps old-project action outstanding until its actual HTTP settlement',()=>{
    const gate=new SurveyActionGate(),first=gate.claim('project-a')!;
    expect(gate.claim('project-b')).toBeNull();expect(first.project).toBe('project-a');
    expect(first.release()).toBe(true);expect(gate.claim('project-b')?.project).toBe('project-b');
  });
  it('does not allow a stale finalizer to release the next action',()=>{
    const gate=new SurveyActionGate(),first=gate.claim('project-a')!;
    expect(first.release()).toBe(true);
    const second=gate.claim('project-b')!;
    expect(first.release()).toBe(false);expect(gate.busy).toBe(true);
    expect(gate.claim('project-c')).toBeNull();expect(second.release()).toBe(true);
  });
  it('releases once on either response outcome without asserting server rollback',()=>{
    const gate=new SurveyActionGate();
    for(const project of ['failed-http','completed-http']){
      const lease=gate.claim(project)!;expect(lease.release()).toBe(true);
      expect(lease.release()).toBe(false);expect(gate.busy).toBe(false);
    }
  });
});
