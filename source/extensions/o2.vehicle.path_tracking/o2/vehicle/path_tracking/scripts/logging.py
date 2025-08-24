"""Logging utilities for the O2 Vehicle Path Tracking extension sample."""

import carb


def redirect_carb_logs_to_stdout():
    """Redirect Carb logs to standard output."""
    carb_settings = carb.settings.get_settings()
    carb_settings.set("/log/enableStandardStreamOutput", True)
    carb_settings.set("/log/outputStream", "stdout")
    carb_settings.set("/log/outputStreamLevel", carb.logging.LEVEL_INFO)
    carb_settings.set("/log/level", carb.logging.LEVEL_INFO)
    carb_settings.set("/log/flushStandardStreamOutput", True)
