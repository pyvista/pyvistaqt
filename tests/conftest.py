import pytest
from pyvista.plotting import system_supports_plotting

NO_PLOTTING = not system_supports_plotting()


def _check_qt_installed():
    try:
        from qtpy import QtCore  # noqa
    except ModuleNotFoundError:
        return False
    else:
        return True


@pytest.fixture()
def plotting():
    """Require plotting."""
    if NO_PLOTTING:
        pytest.skip(NO_PLOTTING, reason="Requires system to support plotting")
    yield


@pytest.fixture()
def no_qt():
    """Require plotting."""
    if _check_qt_installed():
        pytest.skip(reason="Requires that Qt is not installed")
    yield
