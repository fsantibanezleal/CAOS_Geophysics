# M13 public asset rights review

**Review date:** 2026-10-28

**Scope:** the committed STEAD browser package at `data/derived/phase/browser-assets/stead/` and its generated copy in the frontend release directory.

## Decision

The selected STEAD waveform excerpts, the benchmark summary derived from the held-out partition, and the project-authored checkpoint are approved for public distribution in this package under CC BY 4.0, subject to the attribution and change notices in `ATTRIBUTION.md`. This is a scoped repository distribution decision based on the published source declarations below. It does not assert field validity, geological truth, model accuracy beyond the recorded benchmark, or endorsement by the dataset authors.

The reviewed distribution contains 23 normalized, 60-second waveform excerpts, one retained QC-rejected record with no waveform bytes, the aggregate 6,000-trace held-out benchmark, and a 5,739,696-byte ONNX checkpoint. The package does not redistribute the 91,127,786,704-byte source HDF5 or the 402,560,190-byte source metadata file. The model was trained from scratch by this project; it is not an official PhaseNet checkpoint and contains no imported pretrained weights. The checkpoint and benchmark are released under CC BY 4.0 alongside the adapted waveform excerpts so the package does not add terms that prevent recipients from exercising the dataset license.

## Source and license evidence

1. The [STEAD source repository](https://github.com/smousavi05/STEAD) identifies CC BY 4.0 as its repository license and links users to the waveform downloads in its README. The reviewed upstream `master` revision was `e6f247cf174e4aaefe01a6fcc72a0e88296d42b4`. Its `LICENSE` has Git blob SHA-1 `da6ab6cc8f333d7e89a99812866df8f24374d47c` and SHA-256 `9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411`.
2. The [SeisBench STEAD adapter](https://github.com/seisbench/seisbench/blob/e5616ad33c00aba75d5130b44222df46b41e4094/seisbench/data/stead.py) sets the dataset citation to Mousavi et al. (2019) and its dataset license to CC BY 4.0. The reviewed source revision is `e5616ad33c00aba75d5130b44222df46b41e4094`, file blob SHA-1 `95e8aeb8879e3bf022abe912dcd9fdc4a5692900`.
3. The [SeisBench mirror license notice](https://seisbench.gfz-potsdam.de/mirror/LICENSE) says datasets have individual licenses and directs users to the dataset declarations; the notice SHA-256 observed for this review is `5601afa9da212eb94b3a15aec1a17331c4e9e74230b093ab5428405684ae4e8f`. This review uses the STEAD-specific declaration, not SeisBench's GPL-3.0 software license, as the dataset license basis.
4. The local [source receipt](../../../../data/derived/phase/stead-waveform-source.json) binds the downloaded waveform and metadata bytes by SHA-256 and records that the waveform source had no upstream checksum. The browser package manifest binds every redistributed waveform, the checkpoint, and benchmark by SHA-256.

## Required conditions and package treatment

CC BY 4.0 permits sharing and adapting licensed material, including in part, provided attribution is retained, changes are identified, the license is linked, and no endorsement or additional restriction is implied. The package attribution names all four dataset authors, gives the dataset title, DOI and source links, links CC BY 4.0, identifies the mirror, describes reordering and normalization, and states that the traces are unrestituted counts. It also distinguishes the project-trained model from official PhaseNet and says analyst picks are not ground truth. The licensor's warranty disclaimer is linked through the license and stated in the package attribution.

This decision relies on the dataset-level license declarations applying to the supplied STEAD waveform and metadata files. The source metadata has no trace-level license field, so it does not independently establish per-record ownership or additional permissions. The repository does not make broader claims about privacy, publicity, patent, trademark, or rights not granted by CC BY 4.0. If new source terms or a trace-level restriction is discovered, remove the affected asset and rebuild the manifest before public release.

## Reproduction

The asset guard `scripts/check_phase_assets.py` verifies this review reference and license evidence fields against the source and package manifests, in addition to the existing waveform/model/benchmark hash and QC checks. The task checklist marks only the asset-level distribution review complete; browser parity, benchmark scope, and overall product/deployment acceptance remain distinct gates.
