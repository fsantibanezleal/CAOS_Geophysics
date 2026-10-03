# C test-first execution, not course acceptance

MAIN authorization was persisted and pushed at 3c37666772d2142dd9c0447d8be41ba9aafdd460 before test/index/UI creation. Fourteen named gates were then authored in tests/test_m01_scientific_course.py, before the producer.

Actual initial command: existing .venv-m01/Scripts/python.exe -m pytest tests/test_m01_scientific_course.py -q --junitxml=docs/design/features/m01-scientific-course/evidence/test-first-red.xml. Exit1; fourteen tests, six passed, four failed, four setup errors, zero skips; JUnit elapsed63.893 s. Original XML was moved unchanged to ignored data/raw/gravity-m01-transforms/course-c-test-first/initial-red.xml rather than publishing machine paths/tracebacks.

Four setup errors explicitly report absent actual course index/records. Two failures report absent explanatory/shared-shell components. Two additional failures were authoring errors in the new tests: the adapter helper was called with dataset instead of its parent argument, and the status check incorrectly required uppercase APPROVED rather than the recorded authorized text. They are fixed as test authoring defects, not presented as missing scientific implementation. Existing formula, plate/terrain, covariance and negative-control gates passed.

No mocked result, expected-failure annotation or synthetic field substitute was used. Subsequent numerical-only and whole-source gates must be recorded separately. Source checks and tests cannot establish rendered product QA, host admission, field eligibility or full M01 acceptance. The B preview remains historical and unchanged.
