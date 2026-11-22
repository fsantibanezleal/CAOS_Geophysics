# Integrated M01 rendering correction

Date: 2026-10-03. MAIN-owned correction under the already approved product and course implementation scope. This does not change the scientific producer, input, arrays, selection, split, masks, fixed colour limits, source pins or acceptance ledger. No native job or field admission is introduced.

The integrated nine-test browser run passed, but actual image inspection found tiny phone labels and an unhelpful colour midpoint. The previously inspected captures remain retained, not overwritten or relabelled as final. This correction must precede final course review; MAIN author checks are not an independent reviewer verdict.

## Requirements and gates

R-MCR01 THE viewer SHALL encode signed field/residual quantities about zero and nonnegative conditional SD sequentially, using only shared-shell tokens and the unchanged fixed limits.
Gate: frontend/src/test/m01-course-map.test.ts::signed and sequential encodings; frontend/e2e/m01-scientific-course.spec.ts real maps in eight language/theme/device combinations.

R-MCR02 THE viewer SHALL keep metric extents, units and colour-limit labels outside the scaled SVG at inherited shell text size, preserving equal-aspect plotted geometry and null support.
Gate: frontend/e2e/m01-scientific-course.spec.ts checks rendered legend font size and overflow; actual phone/desktop image inspection.

R-MCR03 THE viewer SHALL expose an exact selected-sample readout and a geometric selection marker without changing or filling arrays. Legend values SHALL omit binary roundoff tails.
Gate: frontend/src/test/m01-course-map.test.ts formatting and endpoints; frontend/e2e/m01-scientific-course.spec.ts keyboard and source identity assertions.

## Scientific and style basis

The [official Matplotlib colormap guidance](https://matplotlib.org/stable/users/explain/colors/colormaps.html), read on 2026-10-03, distinguishes ordered nonnegative quantities from deviations around a meaningful zero. The application's shell tokens, not a new palette or stylesheet, supply the actual colours. This is not a claim of perceptually uniform colour spacing or calibrated geological resolution. Negative and positive ranges retain their different original magnitudes; the legend positions zero at its actual numerical fraction of the fixed interval.

Use HTML labels at normal inherited font size rather than enlarge all SVG text and clip it. The existing sampled rectangles, station coordinates and null-support boundaries remain unchanged. Colour saturation affects painting only; inspection returns the original unrounded value.

## Execution status

Corrective tests and rendering are pending at this pre-implementation record. Whole M01/product acceptance, independent review and deployment remain open.
