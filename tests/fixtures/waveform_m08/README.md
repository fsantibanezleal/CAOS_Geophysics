# Authored waveform controls (not provider observations)

The JSON recipe is sealed before native engines or Ridgecrest sources are inspected. Tests construct actual MiniSEED2 integer records and StationXML 1.2 bytes from this recipe, preserving their actual hashes. They are authored controls, never field eligibility or calibration evidence. The constant 1000 counts/(m/s) response is an analogue filter-typed PolesZeros stage with explicit InputUnits/OutputUnits, normalization one and empty pole/zero lists; a bare gain does not supply units.

Independent direct DFT, window sums, analytic transfer and scalar biquad checks use the frozen tolerances in the approved validation plan. No authored arrays are substituted for native scientific results. Native-malformed decoding, CLI/export reopening and resource supervision remain held separately; native-free negative scans do not close those gates.
