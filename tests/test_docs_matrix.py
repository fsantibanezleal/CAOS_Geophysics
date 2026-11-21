from scripts.check_docs_matrix import numeric_tokens


def test_bilingual_numeric_parity_accepts_spanish_decimal_comma() -> None:
    assert numeric_tokens("error 19.91 and 15.8") == numeric_tokens("error 19,91 and 15,8")


def test_bilingual_numeric_parity_preserves_values_and_order() -> None:
    assert numeric_tokens("1.0, 2.5, 10") != numeric_tokens("1,0; 2,6; 10")
