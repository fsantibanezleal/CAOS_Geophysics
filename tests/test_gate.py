from geophysicslab.core.gate import classify_lane


def test_native_heavy_lane_is_precompute():
    verdict = classify_lane(pure_python=False, wheels={"numpy", "torch"}, run_ms=20, trace_bytes=100)
    assert verdict["lane"] == "precompute"
    assert verdict["reasons"]
