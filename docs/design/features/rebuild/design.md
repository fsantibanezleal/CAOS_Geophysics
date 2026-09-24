# Replacement interfaces

The catalogue gives case metadata and six variant references. Every reference loads a single typed result. A result contains the family-specific model geometry, acquisition data, actual forward response, and a method dictionary. Renderers consume arrays and units, never recreate the physics. A method carries model, predicted, residual, metrics, objective history and optional time frames. Camera controls change only the viewpoint and never mutate a geophysical field angle. The selected method and reconstruction are independent from the viewing camera.

Geometry constructors and physical solvers are separate scripts. SimPEG supplies integral sensitivity matrices; SciPy supplies regularized optimization. PyTorch/Deepwave supplies gradients and GPU computation. All official engines are called in the production bake. Tests use temporary output directories.
