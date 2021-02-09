"""
This module contains utilities routines.
"""
from typing import Any, List, Type


def _check_type(var: Any, var_name: str, var_types: List[Type[Any]]) -> None:
    types = tuple(var_types)
    if not isinstance(var, types):
        raise TypeError(
            "Expected type for ``{}`` is {}"
            " but {} was given.".format(var_name, str(types), type(var))
        )
