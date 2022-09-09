try:
    from .test_extension_model import *
except:
    import carb
    carb.log_error("No tests for this module, check extension settings")