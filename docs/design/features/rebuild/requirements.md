# Replacement requirements

R-F01 WHEN a new family is selected, THE workbench SHALL change geometry, measurement axes and available solvers. Gate: rendered family walkthrough.

R-F02 WHEN replay iteration changes, THE workbench SHALL render the saved model for that iteration. Gate: artifact history validation and rendered replay walkthrough.

R-F03 IF a result cannot be loaded, THE app SHALL display an actionable error rather than a numerical fallback. Gate: frontend failure-state test.

R-F04 THE numerical release SHALL use finite-value and objective checks independent of UI labels. Gate: `scripts/check_artifacts.py`.
