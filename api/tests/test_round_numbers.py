from tools.maths import supress_notation


def test_supress_notation():
    assert supress_notation(8e-5, 5) == "0.00008"
