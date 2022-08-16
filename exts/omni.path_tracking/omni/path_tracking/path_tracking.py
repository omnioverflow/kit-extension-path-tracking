# ==============================================================================
# Implements path tracking in spirit of Pure Pursuit algorithm.
# 
# References
# * Implementation of the Pure Pursuit Path tracking Algorithm,  RC Conlter:
#   https://www.ri.cmu.edu/pub_files/pub3/coulter_r_craig_1992_1/coulter_r_craig_1992_1.pdf
# * https://dingyan89.medium.com/three-methods-of-vehicle-lateral-control-pure-pursuit-stanley-and-mpc-db8cc1d32081
# 
import math
import numpy as np

class PurePursuitPathTracker():
    def __init__(self, max_steer_angle_radians):
        self._max_steer_angle_radians = max_steer_angle_radians

    def _steer_value_from_angle(self, angle):
        return np.clip(angle / self._max_steer_angle_radians, -1.0, 1.0)

    def on_step(self, front_axle_pos, rear_axle_pos, forward, dest_pos, curr_pos):
        front_axle_pos, rear_axle_pos = rear_axle_pos, front_axle_pos
        # Lookahead points to the next destination point
        lookahead = dest_pos - rear_axle_pos
        # Forward vector corrsponds to an axis segment front-to-rear
        forward = front_axle_pos - rear_axle_pos

        lookahead_dist = np.linalg.norm(lookahead)
        forward_dist = np.linalg.norm(forward)
        if lookahead_dist == 0.0 or forward_dist == 0.0:
            raise Exception("Pure pursuit aglorithm: invalid state")

        lookahead.Normalize()
        forward.Normalize()
        
        # Compute a signed angle alpha between lookahead and forward vectors,
        # left-handed rotation assumed.
        dot = lookahead[0] * forward[0] + lookahead[2] * forward[2]
        cross = lookahead[0] * forward[2] - lookahead[2] * forward[0]
        alpha = math.atan2(cross, dot)

        theta = math.atan(2.0 * forward_dist * math.sin(alpha) / lookahead_dist)
        steer_angle = self._steer_value_from_angle(theta)

        return steer_angle