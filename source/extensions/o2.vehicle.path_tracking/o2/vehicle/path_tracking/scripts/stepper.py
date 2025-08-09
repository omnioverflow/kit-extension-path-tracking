"""
Stepper class for tracking simulation steps in Omniverse Kit.
Based on Nvidia's sample from omni.physx.vehicle Physics extension.
"""

import math
import threading

import omni.kit
import omni.physx
import omni.timeline
import omni.usd
from omni.physx.bindings._physx import SimulationEvent


class Scenario:
    """Scenario class for tracking simulation steps."""

    def __init__(self, seconds_to_run, time_step=1.0 / 60.0):
        self._target_iteration_count = math.ceil(seconds_to_run / time_step)

    def get_iteration_count(self):
        """Get the target iteration count for the scenario."""
        return self._target_iteration_count

    def on_start(self):
        """Hook called when the simulation starts. Override in subclass."""
        raise NotImplementedError("Subclasses must implement on_start()")

    def on_end(self):
        """Hook called when the simulation ends. Override in subclass."""
        raise NotImplementedError("Subclasses must implement on_end()")

    def on_step(self, _delta_time, _total_time):
        """Hook called on each simulation step. Override in subclass."""
        raise NotImplementedError("Subclasses must implement on_step()")


class SimStepTracker:
    """Tracks simulation steps and manages the scenario lifecycle."""

    def __init__(self, scenario, scenaario_done_signal):
        self._scenario = scenario
        self._target_iteration_count = scenario.get_iteration_count()
        self._scenaario_done_signal = scenaario_done_signal

        self._physx = omni.physx.get_physx_interface()
        self._physx_sim_event_subscription = self._physx.get_simulation_event_stream_v2().create_subscription_to_pop(
            self._on_simulation_event
        )

        self._has_started = False
        self._reset_on_next_resume = False

        self._physx_step_event_subscription = None
        self._iteration_count = 0
        self._total_time = 0

    def abort(self):
        """Abort the simulation."""
        if self._has_started:
            self._on_stop()

        self._physx_sim_event_subscription = None

        self._physx = (
            None  # should release automatically (note: explicit release call results in double release being reported)
        )

        self._scenaario_done_signal.set()

    def stop(self):
        """Stop the simulation."""
        self._scenario.on_end()
        self._scenaario_done_signal.set()

    def reset_on_next_resume(self):
        """Reset the scenario on the next resume."""
        self._reset_on_next_resume = True

    def _on_stop(self):
        self._has_started = False
        self._physx_step_event_subscription = None  # should unsubscribe automatically
        self._scenario.on_end()

    def _on_simulation_event(self, event):
        if event.type == int(SimulationEvent.RESUMED):
            if not self._has_started:
                self._scenario.on_start()
                self._iteration_count = 0
                self._total_time = 0
                self._physx_step_event_subscription = self._physx.subscribe_physics_step_events(self._on_physics_step)
                self._has_started = True
            elif self._reset_on_next_resume:
                self._reset_on_next_resume = False

                # the simulation step callback is still registered and should remain so, thus no unsubscribe
                self._has_started = False
                self._scenario.on_end()

                self._scenario.on_start()
                self._iteration_count = 0
                self._total_time = 0
                self._has_started = True
        # elif event.type == int(SimulationEvent.PAUSED):
        #     self._on_pause()
        elif event.type == int(SimulationEvent.STOPPED):
            self._on_stop()

    def _on_physics_step(self, dt):
        if self._has_started:
            if self._iteration_count < self._target_iteration_count:
                self._scenario.on_step(dt, self._total_time)
                self._iteration_count += 1
                self._total_time += dt
            else:
                self._scenaario_done_signal.set()


class StageEventListener:
    """Listens to stage events and manages simulation state."""

    def __init__(self, sim_step_tracker):
        self._sim_step_tracker = sim_step_tracker
        self._stage_event_subscription = (
            omni.usd.get_context().get_stage_event_stream().create_subscription_to_pop(self._on_stage_event)
        )
        self._stage_is_closing = False
        self.restart_after_stop = False

    def cleanup(self):
        """Cleanup the stage event listener."""
        self._stage_event_subscription = None

    def is_stage_closing(self):
        """Check if the stage is closing."""
        return self._stage_is_closing

    def _on_stage_event(self, event):
        # Check out omni.usd docs for more information regarding
        # omni.usd.StageEventType in particular.
        # https://docs.omniverse.nvidia.com/py/kit/source/extensions/omni.usd/docs/index.html
        if event.type == int(omni.usd.StageEventType.CLOSING):
            self.stop(stageIsClosing=True)
        elif event.type == int(omni.usd.StageEventType.SIMULATION_STOP_PLAY):
            if self.restart_after_stop:
                omni.timeline.get_timeline_interface().play()
        elif event.type == int(omni.usd.StageEventType.SIMULATION_START_PLAY):
            self.restart_after_stop = False
        elif event.type == int(omni.usd.StageEventType.ANIMATION_STOP_PLAY):
            pass

    def stop(self, stageIsClosing=False):
        """Stop the simulation."""
        self._stage_is_closing = stageIsClosing
        self._sim_step_tracker.stop()


class ScenarioManager:
    """Manages the scenario lifecycle and tracks simulation steps."""

    def __init__(self, scenario):
        self._scenario = scenario
        self._setup(scenario)

    def _setup(self, scenario):
        self._init_done = False
        scenario_done_signal = threading.Event()
        self._sim_step_tracker = SimStepTracker(scenario, scenario_done_signal)
        self._stage_event_listener = StageEventListener(self._sim_step_tracker)

    def stop_scenario(self):
        """Stop the current scenario."""
        self._stage_event_listener.stop()

    def cleanup(self):
        """Cleanup the scenario manager."""
        self._stage_event_listener.cleanup()
        self._sim_step_tracker.abort()

    @property
    def scenario(self):
        """Get the current scenario."""
        return self._scenario

    @scenario.setter
    def set_scenario(self, scenario):
        self.stop_scenario()
        self._setup(scenario)
