import nose2.tools

from typing import Union

from app.util import has_attributes


class SampleClass:
    pass


class TestUtil:
    @nose2.tools.params(
        ('SET_VALUE', True),
        (None, False),
        ('NO_ATTRIBUTE', False),
        (False, True),
        ('', True),
        (0, True),
    )
    def test_has_attributes(self, value: Union[bool, int, str, None], ans: bool) -> None:
        obj = SampleClass()
        if value != 'NO_ATTRIBUTE':
            setattr(obj, 'attr', value)

        has_attr = has_attributes(obj, 'attr')

        assert has_attr is ans
