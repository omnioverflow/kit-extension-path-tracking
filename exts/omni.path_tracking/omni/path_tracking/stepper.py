import omni.kit
import omni.physx
import omni.usd
import omni.timeline

from omni.physx.bindings._physx import SimulationEvent

import math
import threading

# ==============================================================================
# Scenario
# ==============================================================================
class Scenario:
    def __init__(self, secondsToRun, timeStep = 1.0 / 60.0):
        self._targetIterationCount = math.ceil(secondsToRun / timeStep)

    def get_iteration_count(self):
        return self._targetIterationCount

    # override in subclass as needed
    def on_start(self):
        pass

    def on_end(self):
        pass

    def on_step(self, deltaTime, totalTime):
        pass

# ==============================================================================
# SimStepTracker
# ==============================================================================
class SimStepTracker:
    def __init__(self, scenario, scenarioDoneSignal):
        self._scenario = scenario
        self._targetIterationCount = scenario.get_iteration_count()
        self._scenarioDoneSignal = scenarioDoneSignal

        self._physx = omni.physx.get_physx_interface()
        self._physxSimEventSubscription = self._physx.get_simulation_event_stream_v2().create_subscription_to_pop(
            self._on_simulation_event
        )

        self._hasStarted = False
        self._resetOnNextResume = False

    def abort(self):
        # note: closing a stage sends the SimulationEvent.STOPPED event now. Thus, it would not be necessary
        #       anymore to check and trigger the stop logic. However, this method is kept general in case
        #       it gets called on other occasions in the future.
        if self._hasStarted:
            self._on_stop()

        self._physxSimEventSubscription = None

        self._physx = (
            None
        )  # should release automatically (note: explicit release call results in double release being reported)

        self._scenarioDoneSignal.set()

    def stop(self):
        self._scenario.on_end()
        self._scenarioDoneSignal.set()

    def reset_on_next_resume(self):
        self._resetOnNextResume = True

    def _on_stop(self):
        self._hasStarted = False
        self._physxStepEventSubscription = None  # should unsubscribe automatically
        self._scenario.on_end()

    def _on_simulation_event(self, event):
        if event.type == int(SimulationEvent.RESUMED):
            if not self._hasStarted:
                self._scenario.on_start()
                self._iterationCount = 0
                self._totalTime = 0
                self._physxStepEventSubscription = self._physx.subscribe_physics_step_events(self._on_physics_step)
                self._hasStarted = True
            elif self._resetOnNextResume:
                self._resetOnNextResume = False

                # the simulation step callback is still registered and should remain so, thus no unsubscribe
                self._hasStarted = False
                self._scenario.on_end()

                self._scenario.on_start()
                self._iterationCount = 0
                self._totalTime = 0
                self._hasStarted = True
        # elif event.type == int(SimulationEvent.PAUSED):
        #     self._on_pause()
        elif event.type == int(SimulationEvent.STOPPED):
            self._on_stop()

    def _on_physics_step(self, dt):
        if self._hasStarted:
            # print(f"step: {self._iterationCount}\n")

            if self._iterationCount < self._targetIterationCount:
                self._scenario.on_step(dt, self._totalTime)
                self._iterationCount += 1
                self._totalTime += dt
            else:
                self._scenarioDoneSignal.set()

# ==============================================================================
# StageEventListener
# ==============================================================================
class StageEventListener:
    def __init__(self, simStepTracker):
        self._simStepTracker = simStepTracker
        self._stageEventSubscription = (
            omni.usd.get_context().get_stage_event_stream().create_subscription_to_pop(self._on_stage_event)
        )
        self._stageIsClosing = False
        self.restart_after_stop = False

    def cleanup(self):
        self._stageEventSubscription = None

    def is_stage_closing(self):
        return self._stageIsClosing

    def _on_stage_event(self, event):
        # Check out omni.usd docs for more information regarding 
        # omni.usd.StageEventType in particular.
        # https://docs.omniverse.nvidia.com/py/kit/source/extensions/omni.usd/docs/index.html
        if event.type == int(omni.usd.StageEventType.CLOSING):
            self._stop(stageIsClosing=True)
        elif event.type == int(omni.usd.StageEventType.SIMULATION_STOP_PLAY):
            if self.restart_after_stop:
                omni.timeline.get_timeline_interface().play()
        elif event.type == int(omni.usd.StageEventType.SIMULATION_START_PLAY):
            self.restart_after_stop = False
        # elif event.type == int(omni.usd.StageEventType.ANIMATION_STOP_PLAY):
        #     print("[StageEventListener] omni.usd.StageEventType.ANIMATION_STOP_PLAY")
    
    def _stop(self, stageIsClosing=False):
        self._stageIsClosing = stageIsClosing
        self._simStepTracker.stop()

# ==============================================================================
# ScenarioManager
# ==============================================================================
class ScenarioManager:
    def __init__(self, scenario):
        self._setup(scenario)

    def _setup(self, scenario):
        self._init_done = False
        scenarioDoneSignal = threading.Event()
        simStepTracker = SimStepTracker(scenario, scenarioDoneSignal)
        self._stageEventListener = StageEventListener(simStepTracker)

    def _run_scenario_internal(self, scenario, resetAtEnd):
        """
        Obsolete way to run a scenario using a helper thread.
        This was taken from the Omniverse sample code. Not sure if it makes sense
        to have a separate thread blocked, whose only responsibility would be
        to stop the simulation timeline.
        """
        scenarioDoneSignal = threading.Event()
        simStepTracker = SimStepTracker(scenario, scenarioDoneSignal)
        self._stageEventListener = StageEventListener(simStepTracker)

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()

        while True:
            scenarioDoneSignal.wait()
            scenarioDoneSignal.clear()

            if self._stageEventListener.is_stage_closing():
                timeline.stop()
                break
            else:
                # scenario has finished -> stop or pause. Pressing play after that should restart the scenario
                if resetAtEnd:
                    timeline.stop()
                else:
                    timeline.pause()
                    simStepTracker.reset_on_next_resume()

        self._stageEventListener.cleanup()
        del self._stageEventListener
        del simStepTracker

    def run_scenario(self):
        timeline = omni.timeline.get_timeline_interface()
        if (timeline.is_playing()):
            # Request restart and then stop the timeline. 
            # In such case, when the timeline is going to be stopped (asynchronously),
            # it will be automatically restarted in the event listener.
            self._stageEventListener.restart_after_stop = True
            timeline.stop()
        else:
            timeline.play()
        # else:
        #     self._init_done = True
        #     omni.timeline.get_timeline_interface().play()

    def run_scenario_force_play(self):
        timeline = omni.timeline.get_timeline_interface()
        if (timeline.is_playing()):
            # Request restart and then stop the timeline. 
            # In such case, when the timeline is going to be stopped (asynchronously),
            # it will be automatically restarted in the event listener.
            self._stageEventListener.restart_after_stop = True
            timeline.stop()
        # force play
        timeline.play()

    @staticmethod
    def play():
        omni.timeline.get_timeline_interface().play()

    def stop_scenario(self):
        self._stageEventListener._stop()

    def set_scenario(self, scenario):
        self.stop_scenario()
        self._setup(scenario)
