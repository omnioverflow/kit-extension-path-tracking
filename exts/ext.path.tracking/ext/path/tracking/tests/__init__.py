# pylint: disable=missing-module-docstring
# flake8: noqa
try:
    from .test_extension_model import *
except:  # pylint: disable=bare-except
    import carb

    carb.log_error("No tests for this module, check extension settings")
