# ==============================================================================
# Implements pure pursuit path tracking algorithm.
# 
# References
# * https://dingyan89.medium.com/three-methods-of-vehicle-lateral-control-pure-pursuit-stanley-and-mpc-db8cc1d32081
# 
from pxr import Gf
import numpy as np
import math

# /scene/WizardVehicle1/Vehicle/LeftWheel1References/Render 
# /scene/WizardVehicle1/Vehicle/LeftWheel1References/Wheel_FL
# 
# /scene/WizardVehicle1/Vehicle/RightWheel1References/Render
# /scene/WizardVehicle1/Vehicle/RightWheel1References/Wheel_FR
# 
# /scene/WizardVehicle1/Vehicle/LeftWheel2References/Render
# /scene/WizardVehicle1/Vehicle/LeftWheel2References/WHeel_RL
# 
# /scene/WizardVehicle1/Vehicle/RightWheel2References/Render
# /scene/WizardVehicle1/Vehicle/RightWheel2References/Wheel_RR
# 
# 

class PurePursuitPathTracker():
    def __init__(self, max_steer_angle_radians):
        self._max_steer_angle_radians = max_steer_angle_radians

    def _steer_value_from_angle(self, angle):
        return np.clip(angle / self._max_steer_angle_radians, -1.0, 1.0)

    def on_step(self, front_axle_pos, rear_axle_pos, forward, dest_pos, curr_pos):
        lookahead = dest_pos - rear_axle_pos
        forward = front_axle_pos - rear_axle_pos

        lookahead_dist = np.linalg.norm(lookahead)
        forward_dist = np.linalg.norm(forward)
        if lookahead_dist == 0.0 or forward_dist == 0.0:
            raise Exception("Pure pursuit: invalid state")

        lookahead.Normalize()
        forward.Normalize()
        
        dot = lookahead[0] * forward[0] + lookahead[2] * forward[2]
        cross = lookahead[0] * forward[2] - lookahead[2] * forward[0]
        alpha = math.atan2(cross, dot)

        steer_angle = math.atan(2.0 * forward_dist * math.sin(alpha) / lookahead_dist)
        return self._steer_value_from_angle(steer_angle)

