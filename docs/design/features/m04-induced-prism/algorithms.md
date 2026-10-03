# Induced prism equations and algorithm

Status: proposed precise numerical semantics.

For inclination I and declination D in radians, the ENU unit field is
f=(cos(I)sin(D), cos(I)cos(D), -sin(I)). Background B0=F*f in nT.
Cell susceptibility chi is dimensionless SI; ideal uniform induced magnetization
is M=chi*(1e-9 B0)/mu0 in A/m. Self-demagnetization, anisotropic susceptibility
and remanence are excluded assumptions, not facts proven from a good fit.

For exterior receiver r and source q, integrate the volume dipole kernel:
b(r)=mu0/(4pi) integral[3(M dot R)R/|R|^5 - M/|R|^3]dV,
R=r-q. Choclo returns tesla; convert to nT once by1e9. SimPEG/Geoana evaluates
the separate analytic prism corner formula using susceptibility and the declared
nT background directly; do not convert chi into density or apply1/1000.

Let component sensitivity K have shape(N,3,n_active). Then b=K chi,
linear anomaly d=f dot b, linear Jacobian J[i,j]=sum_a f[a]*K[i,a,j].
Exactly evaluated scalar magnitude anomaly is |B0+b|-F, not |b| and not d.
Compute its stable form (2*B0 dot b + b dot b)/(|B0+b|+F), avoiding cancellation
from subtracting two large nearly equal norms. F>0 makes denominator positive.
Compute secondary ratio |b|/F and exact-linear difference; reject nonfinite
derived values, never round them to zero. No Jacobian of exact magnitude is
promised. For b=0 both quantities are zero; susceptibility linearity applies
to b,d,J, not generally to the exact scalar magnitude anomaly.

Ordering is independent of field orientation: receiver-major components east,
north,up, and active cells ascending full x-fast index. At horizontal north
(I=0,D=0), f=(0,1,0); horizontal east (0,90), f=(1,0,0); down (90,0),
f=(0,0,-1) within floating-point angular precision. Explicit angles are retained,
not replaced with those rounded cardinal vectors in production.

No inverse solve, statistical correction or hidden weak-anomaly eligibility
screen is part of this algorithm. Wrong-field and remanent controls quantify
model mismatch under independent known controls; they cannot automatically
classify a field survey as induced or uniquely recover magnetization direction.
