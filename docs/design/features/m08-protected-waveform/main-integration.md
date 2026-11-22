# Shared-shell integration

The approved protected waveform feature is mounted alongside the existing
gravity station, MT and ERT/traveltime project instruments. The selected project
and `instrument` URL parameters remain independent; switching method never
changes ownership or substitutes a curated experiment. Use the existing navigation select,
styles, fonts, theme and language controls; introduce no CSS or palette.
The installed shell Tabs primitive is content-driven, not a controlled method
router; the existing selector preserves the selected method URL without inventing
an unsupported shell API or nesting all authenticated instruments.
It is passed into the active instrument sidebar, never a second page-body beside
the instrument. Rendered inspection rejected the initial sibling-button layout:
it squeezed the phone plots despite passing a document-overflow assertion.
The replacement uses the original shell/sidebar geometry with no CSS changes;
rendered tests now assert the instrument's usable width as well as no overflow.

The mount does not admit a Linux runtime or enable a job. Actual capability
comes from the validated API response and fixed selected platform context.
Keep every existing method's request, dataset, result, export and configuration
contract during the M08 merge. The explicit migration is
`0004_waveform_artifacts`; no competing physical migration head is adopted.

Verification: full strict TypeScript and original-inclusive frontend tests;
fresh migration/API tests across waveform and existing profile methods;
same-source native waveform workflow and integrated rendered owner navigation.
Those are distinct from the final VPS release and scientific acceptance.
