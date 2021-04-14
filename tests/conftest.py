import gc
import os
import pytest
import pyvista
from pyvista.plotting import system_supports_plotting

NO_PLOTTING = not system_supports_plotting()

@pytest.fixture()
def plotting():
    """Require plotting."""
    if NO_PLOTTING:
        pytest.skip(NO_PLOTTING, reason="Requires system to support plotting")
    yield
