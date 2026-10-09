import type { Citation } from "@fasl-work/caos-app-shell";
import { M01_COURSE_CITATIONS } from "./m01-scientific-course";
import { M11_COURSE_CITATIONS } from "./m11-scientific-course";
import { MAGNETIC_CITATIONS } from "./magnetic-course-citations";

export const CITATIONS: Citation[] = [
  ...MAGNETIC_CITATIONS,
  ...M11_COURSE_CITATIONS,
  ...M01_COURSE_CITATIONS,
  { id: "processingcontract", label: "Owned processing contract", citation: "Implemented authenticated owner CSV flag-processing workflow: immutable originals, dataset/job/result identity, private worker, export verification and explicit capability boundary. Develop baseline afac8ab.", url: "https://github.com/fsantibanezleal/CAOS_Geophysics/blob/afac8ab/docs/guides/07_processing_jobs.md" },
  { id: "mtcode", label: "MT scientific implementation", citation: "Reviewed strict EDI and electromagnetic implementation: original source, complex forward recurrence, objective, local sensitivity and conditional bootstrap. Scientific baseline 7b69404.", url: "https://github.com/fsantibanezleal/CAOS_Geophysics/tree/7b69404/data-pipeline" },
  { id: "mtonline", label: "Bounded MT worker", citation: "Reviewed online M05/M06 implementation: exact-source screen binding, frozen frequency partition, training-only multistart and sensitivity controls. Compute baseline 7b69404.", url: "https://github.com/fsantibanezleal/CAOS_Geophysics/blob/7b69404/app/mt_compute.py" },
  { id: "mtcontract", label: "Online MT contract", citation: "Bounded authenticated EDI contract: source identity, result arrays, export and admission boundaries. PR100 contract at 0970a09; actual-host acceptance is separate.", url: "https://github.com/fsantibanezleal/CAOS_Geophysics/blob/0970a09/docs/data-contract/02_online-edi-mt.md" },
  { id: "mtmetadata", label: "MT Metadata EDI", citation: "MT Metadata official EDI reader for electromagnetic transfer functions; this product validates raw blocks before reader invocation.", url: "https://github.com/MTgeophysics/mt_metadata/blob/main/mt_metadata/transfer_functions/io/edi/edi.py" },
  { id: "emtffcu", label: "EMTF-FCU conventions", citation: "EMTF-FCU source documentation: Fourier sign, impedance conventions, complex-error variance and limits of rotating EDI marginal errors.", url: "https://github.com/magnetotellurics/EMTF-FCU" },
  { id: "caldwell2004", label: "Caldwell et al. 2004", citation: "Caldwell, T. G., Bibby, H. M. and Brown, C. The magnetotelluric phase tensor. Geophysical Journal International 158(2), 457-469 (2004).", doi: "10.1111/j.1365-246X.2004.02281.x" },
  { id: "clearlake", label: "USGS Clear Lake MT", citation: "Peacock, J. R., Mitchell, M. A. and Burgess, S. D. Magnetotelluric data from the Clear Lake Region, Northern California. USGS data release (2025). cl061 is a measured QC-only exclusion, not 1D geological truth.", doi: "10.5066/P14KAQ3M", url: "https://www.usgs.gov/data/magnetotelluric-data-clear-lake-region-northern-california" },
  {
    id: "allen1978",
    label: "Allen 1978",
    citation: "Allen, R. V. Automatic earthquake recognition and timing from single traces. Bulletin of the Seismological Society of America 68(5), 1521-1532 (1978).",
    doi: "10.1785/bssa0680051521",
  },
  {
    id: "diehl2009",
    label: "Diehl et al. 2009",
    citation: "Diehl, T., Deichmann, N., Kissling, E. and Husen, S. Automatic S-wave picker for local earthquake tomography. Bulletin of the Seismological Society of America 99(3), 1906-1920 (2009).",
    doi: "10.1785/0120080019",
  },
  {
    id: "zhu2019",
    label: "Zhu and Beroza 2019",
    citation: "Zhu, W. and Beroza, G. C. PhaseNet: a deep-neural-network-based seismic arrival-time picking method. Geophysical Journal International 216(1), 261-273 (2019).",
    doi: "10.1093/gji/ggy423",
  },
  {
    id: "obspytrigger",
    label: "ObsPy classic STA/LTA",
    citation: "ObsPy documentation and source: classic_sta_lta and trigger_onset, sample-window energy characteristic and thresholded onset extraction.",
    url: "https://docs.obspy.org/packages/autogen/obspy.signal.trigger.classic_sta_lta.html",
  },
  {
    id: "obspyresponse",
    label: "ObsPy channel response",
    citation: "ObsPy documentation: Inventory.get_response selects a channel response at a specified time; Stream.remove_response deconvolves the instrument response.",
    url: "https://docs.obspy.org/packages/autogen/obspy.core.inventory.inventory.Inventory.get_response.html",
  },
  {
    id: "phasenetofficial",
    label: "AI4EPS PhaseNet",
    citation: "AI4EPS official PhaseNet repository: reference implementation, data formats, prediction and training commands.",
    url: "https://github.com/AI4EPS/PhaseNet",
  },
  { id: "astic2020", label: "Astic, Heagy and Oldenburg 2020", citation: "Astic, T., Heagy, L. J. and Oldenburg, D. W. Petrophysically and geologically guided multi-physics inversion using a dynamic Gaussian mixture model. Geophysical Journal International, 224(1), 40–68.", doi: "10.1093/gji/ggaa378", url: "https://arxiv.org/abs/2002.09515" },
  {
    id: "simpeggravity",
    label: "SimPEG gravity inversion",
    citation:
      "SimPEG user tutorial: 3D gravity-anomaly inversion. Reference implementation with data weighting and regularization; the local solver differs as documented.",
    url: "https://simpeg.xyz/user-tutorials/inv-gravity-anomaly-3d/",
  },
  {
    id: "simpegmagnetic",
    label: "SimPEG magnetic inversion",
    citation:
      "SimPEG user tutorial: 3D inversion of total magnetic intensity for susceptibility.",
    url: "https://simpeg.xyz/user-tutorials/inv-magnetics-induced-3d/",
  },
  {
    id: "scipytrf",
    label: "SciPy 1.15.2 least_squares",
    citation:
      "SciPy 1.15.2 API reference: bounded nonlinear least squares and the trust-region reflective algorithm.",
    url: "https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.least_squares.html",
  },
  {
    id: "crossgradient",
    label: "SimPEG cross-gradient inversion",
    citation:
      "SimPEG tutorial: cross-gradient joint inversion of gravity and magnetic data.",
    url: "https://docs.simpeg.xyz/latest/content/user-guide/tutorials/13-joint_inversion/plot_inv_3_cross_gradient_pf.html",
  },
  {
    id: "adam",
    label: "Kingma and Ba 2014",
    citation:
      "Kingma, D. P. and Ba, J. (2014). Adam: A Method for Stochastic Optimization.",
    url: "https://arxiv.org/abs/1412.6980",
  },
  {
    id: "cockett2015",
    label: "Cockett et al. 2015",
    citation:
      "Cockett, R. et al. (2015). SimPEG: An open source framework for simulation and gradient based parameter estimation in geophysical applications.",
    doi: "10.1016/j.cageo.2015.09.015",
  },
  {
    id: "heagy2017",
    label: "Heagy et al. 2017",
    citation:
      "Heagy, L. J. et al. (2017). A framework for simulation and inversion in electromagnetics.",
    doi: "10.1016/j.cageo.2017.06.018",
  },
  {
    id: "choclo",
    label: "Choclo",
    citation:
      "Choclo, fast and accurate gravity and magnetic forward modelling.",
    url: "https://www.fatiando.org/choclo/dev/overview.html",
  },
  {
    id: "mtpy",
    label: "MTpy-v2",
    citation:
      "MTpy-v2 documentation, magnetotelluric data structures and EDI workflows.",
    url: "https://mtpy-v2.readthedocs.io/en/stable/index.html",
  },
  {
    id: "goyes2024",
    label: "Goyes-Peñafiel et al. 2025",
    citation:
      "Goyes-Peñafiel, P., Waheed, U. and Arguello, H. Physically Guided Deep Unsupervised Inversion for 1D Magnetotelluric Models.",
    doi: "10.1109/LGRS.2025.3528767",
    url: "https://arxiv.org/abs/2410.15274v3",
  },
  {
    id: "virieux2009",
    label: "Virieux and Operto 2009",
    citation:
      "Virieux, J. and Operto, S. (2009). An overview of full-waveform inversion in exploration geophysics.",
    doi: "10.1190/1.3238367",
  },
  {
    id: "deepwave",
    label: "Deepwave",
    citation:
      "Deepwave, PyTorch wave propagation and differentiable seismic modelling.",
    url: "https://github.com/ar4/deepwave",
  },
  {
    id: "devito",
    label: "Devito",
    citation:
      "Devito project, symbolic finite-difference operators for seismic modelling and inversion.",
    url: "https://www.devitoproject.org/examples/seismic/tutorials/03_fwi.html",
  },
  {
    id: "openfwi",
    label: "OpenFWI",
    citation:
      "OpenFWI, open benchmark and learned baselines for seismic inversion.",
    url: "https://github.com/lanl/OpenFWI",
  },
  {
    id: "inversionnet",
    label: "Wu and Lin 2019",
    citation:
      "Wu, Y. and Lin, Y. (2019). InversionNet: An efficient and accurate data-driven full waveform inversion framework.",
    doi: "10.1109/TCI.2019.2956866",
  },
  {
    id: "pinnreview",
    label: "Physics-informed inversion review",
    citation:
      "Physics-informed neural networks for geophysical inversion: a review.",
    doi: "10.1190/geo2023-0615.1",
  },
];
