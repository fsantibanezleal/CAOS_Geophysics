# Research admission adversaries

| requirement | adversarial check | gate |
|---|---|---|
| RA-001 | Declare a protocol in the wrong section, inside a code fence, or with an unknown identifier; require refusal while retaining a valid protocol/dataset positive control. | `tests/test_novel_contribution_manuscripts.py::test_adversarial_novel_id_from_an_unrelated_section_is_not_a_declaration`, `tests/test_novel_contribution_manuscripts.py::test_adversarial_fenced_novel_id_is_not_a_declaration` |
| RA-002 | Plant a stage-owned provider and engine that exit successfully if imported; require the product-owned provider boundary to refuse them. | `tests/adversarial/test_adoption_defects_0_15_001.py::test_adversarial_a_stage_cannot_bring_its_own_provider_or_engine` |
| RA-003 | Remove the configured external root or declare two notebook runtimes and require refusal. An inner-runner flag must not permit an unrelated interpreter. | `tests/test_notebook_environment.py::test_adversarial_missing_external_root_does_not_fall_back_to_local`, `tests/test_notebook_environment.py::test_adversarial_ambiguous_notebook_roles_are_refused`, `tests/test_notebook_environment.py::test_adversarial_inner_flag_cannot_select_an_unrelated_interpreter` |
