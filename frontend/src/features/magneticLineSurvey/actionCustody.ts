/** In-view HTTP action custody only, never global/native scheduling authority. */
export interface SurveyActionLease {readonly project:string;release:()=>boolean}
export class SurveyActionGate {
  private current:SurveyActionLease|null=null;
  get busy(){return this.current!==null;}
  claim(project:string):SurveyActionLease|null {
    if(!project||this.current)return null;
    let released=false;
    const lease:SurveyActionLease={project,release:()=>{
      if(released||this.current!==lease)return false;
      released=true;this.current=null;return true;
    }};
    this.current=lease;return lease;
  }
}
