import { ApiClient } from "./client";
import { ProcessingApi } from "./processing";
import { bindEdiDataset, bindMtResult, parseEdiDataset, parseMtResult, validateMtParameters, verifyMtBundle, type EdiDataset } from "./mt-contracts";
import { M05_METHOD, M06_METHOD, isMtJob, parseProjectDatasetReceipt, parseProjectProcessingJob, processingId as id, processingObject as obj, processingText as text, same, type EdiDatasetReceipt, type MtProcessingJob, type MtInverseParameters } from "./processing-contracts";

export class MtProcessingApi extends ProcessingApi {
  constructor(private readonly mtClient: ApiClient) {super(mtClient);}
  private async token(signal?: AbortSignal) {const token=await this.mtClient.requestJson("/api/auth/csrf",v=>obj(v,"csrf"),{signal}); return text(token.csrf_token,"CSRF");}
  private root(project: string){return `/api/projects/${id(project)}`;}
  private path(project:string,job:string){return `${this.root(project)}/jobs/${id(job)}`;}
  async validateEdi(project:string,asset:string,signal?:AbortSignal) {
    const receipt=await this.mtClient.requestJson(`${this.root(project)}/datasets`,parseProjectDatasetReceipt,{method:"POST",csrfToken:await this.token(signal),body:{asset_id:id(asset)},signal});
    if(receipt.modality!=="edi_transfer_function")throw new Error("MT validation returned gravity"); same(receipt.project_id,project,"envelope project");same(receipt.raw_asset_id,asset,"envelope raw asset");return receipt;
  }
  async ediDataset(project:string,receipt:EdiDatasetReceipt,signal?:AbortSignal){same(receipt.project_id,project,"EDI project"); const dataset=await this.mtClient.requestJson(`${this.root(project)}/datasets/${id(receipt.dataset_id)}`,parseEdiDataset,{signal});bindEdiDataset(dataset,receipt);return dataset;}
  async submitMt(project:string,receipt:EdiDatasetReceipt,method:typeof M05_METHOD|typeof M06_METHOD,parameters:Record<string,never>|MtInverseParameters,signal?:AbortSignal) {
    same(receipt.project_id,project,"MT project"); if(method===M06_METHOD)validateMtParameters(parameters); else same(parameters,{},"M05 parameters");
    const result=await this.mtClient.requestJson(`${this.root(project)}/jobs`,parseProjectProcessingJob,{method:"POST",csrfToken:await this.token(signal),body:{dataset_id:receipt.dataset_id,method_id:method,parameters},signal});
    if(!isMtJob(result))throw new Error("MT submission returned gravity"); same(result.project_id,project,"submitted project");same(result.dataset_id,receipt.dataset_id,"submitted dataset");same(result.dataset_sha256,receipt.sha256,"submitted dataset hash");same(result.method_id,method,"submitted MT method");same(result.request.parameters,parameters,"submitted MT parameters");same(result.request.raw_asset_id,receipt.raw_asset_id,"submitted original");same(result.request.raw_sha256,receipt.raw_sha256,"submitted original hash");return result;
  }
  async mtResult(project:string,job:MtProcessingJob,dataset:EdiDataset,receipt:EdiDatasetReceipt,signal?:AbortSignal){same(job.project_id,project,"job project");same(dataset.project_id,project,"dataset project");bindEdiDataset(dataset,receipt);same(job.dataset_sha256,receipt.sha256,"dataset hash");if(job.state!=="succeeded")throw new Error("Non-success MT job has no result");const result=await this.mtClient.requestJson(`${this.path(project,job.job_id)}/result`,parseMtResult,{signal});bindMtResult(result,job,dataset);return result;}
  async mtExport(project:string,job:MtProcessingJob,dataset:EdiDataset,receipt:EdiDatasetReceipt,signal?:AbortSignal){same(job.project_id,project,"job project");same(dataset.project_id,project,"dataset project");bindEdiDataset(dataset,receipt);same(job.dataset_sha256,receipt.sha256,"dataset hash");if(job.state!=="succeeded")throw new Error("Non-success MT job has no export");const blob=await this.mtClient.requestBlob(`${this.path(project,job.job_id)}/export`,{signal});await verifyMtBundle(blob,job,dataset);return blob;}
}
