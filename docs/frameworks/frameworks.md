# Frameworks

Each engine selected by the research review has a card, an explicit role, and a pinned requirement where the local environment supports it.

- [SimPEG](simpeg.md): modular geophysical simulation and gradient-based inversion.
- [Choclo](choclo.md): fast potential-field kernels.
- [MTpy](mtpy.md): EDI and magnetotelluric data structures.
- [PyTorch](pytorch.md): differentiable MT and learned spatial tools with the local GPU lane.
- [Deepwave](deepwave.md): PyTorch wave propagation for differentiable seismic experiments.
- [Devito](devito.md): symbolic finite-difference cross-check for acoustic FWI.

The compact browser mirror does not import native scientific libraries. This separation is deliberate: a heavy solver cannot be mislabeled as a browser method, and the browser remains useful when the host is CPU-only.
