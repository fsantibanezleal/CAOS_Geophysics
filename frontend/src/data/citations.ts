import type { Citation } from '@fasl-work/caos-app-shell';

export const CITATIONS: Citation[] = [
  { id: 'cockett2015', label: 'Cockett et al. 2015', citation: 'Cockett, R. et al. (2015). SimPEG: An open source framework for simulation and gradient based parameter estimation in geophysical applications.', doi: '10.1016/j.cageo.2015.09.015' },
  { id: 'heagy2017', label: 'Heagy et al. 2017', citation: 'Heagy, L. J. et al. (2017). A framework for simulation and inversion in electromagnetics.', doi: '10.1016/j.cageo.2017.06.018' },
  { id: 'choclo', label: 'Choclo', citation: 'Choclo, fast and accurate gravity and magnetic forward modelling.', url: 'https://www.fatiando.org/choclo/dev/overview.html' },
  { id: 'mtpy', label: 'MTpy-v2', citation: 'MTpy-v2 documentation, magnetotelluric data structures and EDI workflows.', url: 'https://mtpy-v2.readthedocs.io/en/stable/index.html' },
  { id: 'goyes2024', label: 'Goyes-Peñafiel et al. 2024', citation: 'Goyes-Peñafiel, P., Waheed, U. and Arguello, H. (2024). Physics-guided neural network for magnetotelluric inversion.', url: 'https://arxiv.org/abs/2410.15274' },
  { id: 'virieux2009', label: 'Virieux and Operto 2009', citation: 'Virieux, J. and Operto, S. (2009). An overview of full-waveform inversion in exploration geophysics.', doi: '10.1190/1.3238367' },
  { id: 'deepwave', label: 'Deepwave', citation: 'Deepwave, PyTorch wave propagation and differentiable seismic modelling.', url: 'https://github.com/ar4/deepwave' },
  { id: 'devito', label: 'Devito', citation: 'Devito project, symbolic finite-difference operators for seismic modelling and inversion.', url: 'https://www.devitoproject.org/examples/seismic/tutorials/03_fwi.html' },
  { id: 'openfwi', label: 'OpenFWI', citation: 'OpenFWI, open benchmark and learned baselines for seismic inversion.', url: 'https://github.com/lanl/OpenFWI' },
  { id: 'inversionnet', label: 'Wu and Lin 2019', citation: 'Wu, Y. and Lin, Y. (2019). InversionNet: An efficient and accurate data-driven full waveform inversion framework.', doi: '10.1109/TCI.2019.2956866' },
  { id: 'pinnreview', label: 'Physics-informed inversion review', citation: 'Physics-informed neural networks for geophysical inversion: a review.', doi: '10.1190/geo2023-0615.1' },
];
