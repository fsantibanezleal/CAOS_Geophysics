import type { Citation } from "@fasl-work/caos-app-shell";

export const CITATIONS: Citation[] = [
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
