import type { Citation } from "@fasl-work/caos-app-shell";

/** Merge into the existing root registry when the parent mounts this course. */
export const MAGNETIC_CITATIONS: Citation[] = [
  {id:"simpeg0252magnetic",label:"SimPEG 0.25.2 magnetic simulation",citation:"SimPEG developers. Simulation3DIntegral, scalar induced magnetization and component Jacobian. Version 0.25.2, official source.",url:"https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/simulation.py"},
  {id:"simpeg0252regularization",label:"SimPEG 0.25.2 WeightedLeastSquares",citation:"SimPEG developers. WeightedLeastSquares, explicit alpha coefficients, active-cell regularization mesh and reference model. Version 0.25.2, official source.",url:"https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/base.py"},
  {id:"simpeg0252sparse",label:"SimPEG 0.25.2 Sparse",citation:"SimPEG developers. SparseSmallness and Sparse, component gradients and model-dependent IRLS weights. Version 0.25.2, official source.",url:"https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/sparse.py"},
  {id:"choclo032magnetic",label:"Choclo 0.3.2 magnetic components",citation:"Choclo developers. Independent rectangular-prism magnetic component functions. Version 0.3.2, official source. Component checks do not supply field-survey truth.",url:"https://raw.githubusercontent.com/fatiando/choclo/v0.3.2/choclo/prism/_magnetic.py"},
];
