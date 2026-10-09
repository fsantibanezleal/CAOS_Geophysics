# Induced magnetic forward calculation

An induced model describes dimensionless SI susceptibility in explicitly declared
prisms under a specified uniform background field. It is not a magnetic survey
correction, an inverse solution or a demonstration of field geology.

[The ordinary local calculation](magnetic-forward/01_induced-prism.md) explains
the actual SimPEG/Geoana operator, physical units, independent Choclo and volume
integration controls, the distinction between linear TMI and scalar magnitude,
and the reproducible local test lane. Its strict request accepts native NumPy
arrays, not uploaded bytes or a serialized survey.

The [intrinsic contract](../design/features/m04-induced-prism/contracts.md) and
[frozen validation criteria](../design/features/m04-induced-prism/validation.md)
govern this forward unit. Susceptibility inversion, L2/IRLS selection, held-out
prediction, authenticated field inputs, durable storage and an online user-data
workflow are separate required capabilities, not implied by a forward result.
