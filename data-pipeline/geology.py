"""Original discrete geological constructions, ENU coordinates, no Gaussian case template."""
from __future__ import annotations

import numpy as np

# Same physical domain; refinement is not additional survey information.
VOLUME_SHAPE = (16, 24, 28)  # depth, northing, easting
VOLUME_SPACING = (80.0, 80.0, 70.0)  # easting, northing, up (m)
SEISMIC_SHAPE = (128, 96)
SEISMIC_SPACING = 12.5

CASES = [
    ("GRAVITY_INTRUSION", "gravity", "Offset intrusive stock", "Intrusión desplazada", "stock"),
    ("GRAVITY_DEEP_BODY", "gravity", "Asymmetric sedimentary basin", "Cuenca sedimentaria asimétrica", "basin"),
    ("GRAVITY_NOISY", "gravity", "Opposing density bodies", "Cuerpos de densidad opuesta", "paired"),
    ("GRAVITY_TILTED", "gravity", "Faulted dipping contact", "Contacto inclinado y fallado", "fault"),
    ("MAGNETIC_DYKE", "magnetics", "Dipping dyke swarm", "Enjambre de diques inclinados", "dykes"),
    ("MAGNETIC_REMANENCE", "magnetics", "Remanent tabular body", "Cuerpo tabular remanente", "remanent"),
    ("MAGNETIC_DEEP", "magnetics", "Deep magnetite lens", "Lente profunda de magnetita", "lens"),
    ("MAGNETIC_NOISY", "magnetics", "Cross-cutting dykes", "Diques entrecruzados", "crossing"),
    ("MT_RESISTIVE", "mt", "Resistive cover / conductive basement", "Cobertura resistiva / basamento conductor", "cap"),
    ("MT_CONDUCTIVE", "mt", "Buried conductive aquifer", "Acuífero conductor enterrado", "aquifer"),
    ("MT_MIXED", "mt", "Alternating crustal layers", "Capas corticales alternantes", "alternating"),
    ("MT_NOISY", "mt", "Deep conductor / noisy sounding", "Conductor profundo / sondeo ruidoso", "deep"),
    ("FWI_LAYERED", "seismic", "Layered reflection survey", "Perfil de reflexión estratificado", "layers"),
    ("FWI_FAULT", "seismic", "Normal fault displacement", "Desplazamiento de falla normal", "normal_fault"),
    ("FWI_CYCLE_SKIP", "seismic", "Salt dome / cycle skipping", "Domo salino / salto de ciclo", "salt"),
    ("FWI_NOISY", "seismic", "Low-velocity gas channel", "Canal de gas de baja velocidad", "channel"),
    ("JOINT_SHARED", "joint", "Shared lithological boundary", "Límite litológico compartido", "shared"),
    ("JOINT_CONFLICT", "joint", "Decoupled density / susceptibility", "Densidad y susceptibilidad desacopladas", "conflict"),
    ("LEARNED_CNN", "learned", "Oblique intrusion / inverse CNN", "Intrusión oblicua / CNN inversa", "oblique"),
    ("LEARNED_AUTOENCODER", "learned", "Ring dyke / out-of-distribution", "Dique anular / fuera de distribución", "ring"),
]

VARIANTS = [
    ("reference", "Reference survey", "Adquisición de referencia"),
    ("contrast", "Property contrast ×1.5", "Contraste de propiedad ×1.5"),
    ("noise", "Higher observation noise", "Mayor ruido de observación"),
    ("acquisition", "Changed acquisition", "Adquisición modificada"),
    ("coverage", "Reduced coverage", "Cobertura reducida"),
    ("regularization", "Stronger regularization", "Regularización mayor"),
]


def registry():
    return [dict(id=c[0], family=c[1], name=c[2], name_es=c[3], geometry=c[4], seed=4200+i) for i, c in enumerate(CASES)]


def volume_grid(refinement=2):
    from discretize import TensorMesh
    mesh = TensorMesh([[(160.0/refinement, 14*refinement)], [(160.0/refinement, 12*refinement)], [(140.0/refinement, 8*refinement)]], origin=[-1120, -960, -1120])
    return mesh


def properties(kind, centers, contrast=1.0):
    x, y, u = centers.T
    depth = -u
    rho = np.zeros_like(x)
    chi = np.zeros_like(x)
    def ell(cx, cy, cz, ax, ay, az):
        return ((x-cx)/ax)**2 + ((y-cy)/ay)**2 + ((depth-cz)/az)**2 < 1
    if kind == "stock":
        rho[ell(-330, 220, 570, 410, 320, 460)] = .48
        rho[(abs(x+220) < 140) & (abs(y-220)<170) & (depth<470)] = .32
    elif kind == "basin":
        base = 180 + 520*np.clip(1-((x+200)/1200)**2, 0, 1)*np.clip(1-((y-140)/1000)**2, 0, 1)
        rho[(depth<base) & (depth>100)] = -.38
    elif kind == "paired":
        rho[ell(-550,-250,370,290,350,250)] = .60
        rho[(abs(x-430)<260)&(abs(y-220)<350)&(depth>430)&(depth<880)] = -.32
    elif kind == "fault":
        contact = 370 + .24*x + np.where(y>0,240,0)
        rho[(depth>contact)&(depth<contact+210)] = .42
    elif kind == "dykes":
        for offset, amp in [(-460,.035),(180,.025),(630,.018)]:
            chi[(abs(x-.35*depth-.28*y-offset)<95)&(depth>150)&(depth<950)] = amp
    elif kind == "remanent":
        chi[(abs(depth-(440+.27*x))<100)&(abs(y+120)<440)&(abs(x)<820)] = .026
    elif kind == "lens":
        chi[ell(360,-230,840,510,310,190)] = .065
    elif kind == "crossing":
        chi[(abs(x-.65*y+150)<100)&(depth<800)] = .028
        chi[(abs(y+.65*x-210)<110)&(depth>280)&(depth<990)] = .045
    elif kind == "shared":
        mask=(depth>380+.18*x+.15*y)&(depth<660+.18*x+.15*y)
        rho[mask]=.40
        chi[mask]=.027
    elif kind == "conflict":
        rho[ell(-480,250,510,370,400,360)]=.45
        chi[(abs(x-400-.2*depth)<130)&(abs(y+200)<610)&(depth>120)]=.035
    elif kind == "oblique":
        rho[(abs(x+.7*y-.3*depth+100)<160)&(abs(y)<730)&(depth>210)&(depth<950)] = .46
    elif kind == "ring":
        r=np.sqrt(((x-170)/1.25)**2+(y+100)**2)
        rho[(r>340)&(r<530)&(depth>220)&(depth<790)] = .50
    else:
        raise ValueError(f"No geological constructor for {kind}")
    return rho*contrast, chi*contrast


def mt_model(kind, contrast=1.0):
    cases={"cap":([900,120,18],[180,600]), "aquifer":([120,7,500],[280,420]),
           "alternating":([80,500,9,350,35],[150,450,700,1400]), "deep":([100,600,4,220],[400,1600,800])}
    rho,h=cases[kind]
    return np.asarray(rho,dtype=float)*contrast,np.asarray(h,dtype=float)


def seismic_model(kind, contrast=1.0, nx=128, nz=96, spacing=12.5):
    x=np.arange(nx)*spacing
    z=np.arange(nz)*spacing
    X,Z=np.meshgrid(x,z,indexing="ij")
    if kind == "layers":
        v=np.where(Z<260,1750,np.where(Z<610,2200,2850)).astype(float)
    elif kind == "normal_fault":
        offset=np.where(X>760,200,0)
        v=np.where(Z<260+offset,1800,np.where(Z<570+offset,2300,3000)).astype(float)
    elif kind == "salt":
        v=1800+Z*.9
        mask=((X-850)/360)**2+((Z-760)/630)**2<1
        v[mask]=3650
    elif kind == "channel":
        v=np.where(Z<290,1800,np.where(Z<670,2350,2950)).astype(float)
        mask=(abs(Z-(510+95*np.sin(X/240)))<90)&(X>260)&(X<1360)
        v[mask]=1550
    else:
        raise ValueError(kind)
    return (1800+(v-1800)*contrast).astype(np.float32)
