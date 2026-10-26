import {describe,it,expect} from 'vitest';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {parseRepresentation,parseResult} from './contract';
import schema from './schema_qr.json';

// Independent small representation controls, NOT a numerical/native fit.
const literals=(spec:Record<string,unknown[]>)=>Object.fromEntries(Object.entries(spec).map(([key,v])=>[key,v[1]]));
const diagnostics=()=>({data_term:2,regularization_term:3,objective:5,gradient_denominator:2,
  stationarity_inf:1e-10,stationarity_relative:5e-11,coefficient_error_bound_nT:0});
const capacity=()=>({rows:4,sources:2,augmented_rows:6,lwork:4,augmented_matrix_bytes:96,triangular_matrix_bytes:32,
  extra_peak_bytes:8*(4*6*2+4*2*2+8*6+16*2+4)+33554432,factorization_work_bound:8*6*2*2+8*2*2*2,
  augmented_buffer_slots:4,triangular_buffer_slots:4});
describe('separate QR representation guards',()=>{
  it('keeps literal new epoch separate from legacy solver policies',()=>{
    expect(parseRepresentation('QRPolicy',literals(schema.QRPolicy),3)).toEqual(literals(schema.QRPolicy));
    expect(()=>parseRepresentation('QRPolicy',literals(schema.QRPolicy),2)).toThrow();
    expect(()=>parseRepresentation('QRPolicy',{...literals(schema.QRPolicy),istop:1},3)).toThrow();
  });
  it('enforces exact objective/gradient equation and unchanged1e-9 boundary',()=>{
    expect(parseRepresentation('OriginalDiagnostics',diagnostics(),3)).toEqual(diagnostics());
    for(const wrong of [{...diagnostics(),objective:4},{...diagnostics(),stationarity_relative:1e-8},
      {...diagnostics(),gradient_denominator:0},{...diagnostics(),stationarity_relative:0}])
      expect(()=>parseRepresentation('OriginalDiagnostics',wrong,3)).toThrow();
  });
  it('independently enforces all dense allocation equation fields',()=>{
    expect(parseRepresentation('DenseCapacity',capacity(),3)).toEqual(capacity());
    for(const wrong of [{...capacity(),sources:5},{...capacity(),lwork:3},{...capacity(),extra_peak_bytes:33554432},
      {...capacity(),factorization_work_bound:1},{...capacity(),augmented_rows:4}])
      expect(()=>parseRepresentation('DenseCapacity',wrong,3)).toThrow();
  });
});

const actualPath=process.env.GEOPHYSICS_M03_QR_RESULT;
describe.skipIf(!actualPath)('actual retained QR Result/3 bytes (not field8201)',()=>{
  const load=()=>{
    const bytes=readFileSync(actualPath!);
    expect(createHash('sha256').update(bytes).digest('hex')).toBe('275ae3a46c287f4d44db95608bff0fb674e7f4bf752a47e75c56be768f0d4c76');
    return JSON.parse(bytes.toString('utf8'));
  };
  it('reads actual97 fits and retains actual UNRESOLVED predictive evidence',()=>{
    const result=parseResult(load());expect(result.schema).toBe('magnetic-line-survey-result/3');
    expect(result.fit.fit_count).toBe(97);expect(result.inventory.original_rows).toBe(363);
    expect(result.verdict.overall).toBe('unresolved');expect(result.evaluation.rmse_nT).toBe(22.49315689444791);
  });
  it('refuses actual-document numerical/custody/epoch mutations without tolerance weakening',()=>{
    const original=load();const cases=[
      (v:typeof original)=>{v.fit.fit_count=25;},(v:typeof original)=>{v.fit.solve.istop=1;},
      (v:typeof original)=>{v.fit.solve.condition_upper_bound=1e8;},
      (v:typeof original)=>{v.fit.solve.original_diagnostics.stationarity_relative=1e-8;},
      (v:typeof original)=>{v.policy_epoch='resolution_v2';},(v:typeof original)=>{delete v.execution;},
      (v:typeof original)=>{v.fit.scaled_coefficients.sha256='A'.repeat(64);},
      (v:typeof original)=>{v.fit.solve.engine_identity.blas[0].sha256='0'.repeat(64);},
    ];
    for(const mutate of cases){const value=structuredClone(original);mutate(value);expect(()=>parseResult(value)).toThrow();}
  });
});
