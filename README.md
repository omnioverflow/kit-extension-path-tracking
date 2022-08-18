# Vehicle Path Tracking Extension

## About

Path tracking extension allows an instance of omni.physxvehicle to
follow a defined path (Usd BasisCurves) via a path tracking algorithm inspired
by a classic Pure Pursuit algorithm.

![Vehicle Path Tracking Preview](exts/omni.path_tracking/data/preview.PNG)
Figure. Preview of Vehicle Path Tracking Extension

###
System Requirements

- Code 2022.1.3+ or Create 2022.1.5+
- Pyhton 3.7+ (should be the case by default when using Kit's embedded CPython 3.7)

### Limitations

* Pure Pursuit Tracking algorithm is kinematic and therefore does not take into 
account allo of the vehicle physics dynamics, such as tire slipping etc.
* No unit tests; occasional bugs might exist.
* Styling could be extracted into a deicated place, such as `style.py`

## Installing Extension

It is possible to configure extension search path inside Omniverse Code or Create:
1. `Window` -> `Extension Manager` -> ⚙️ `Gear Icon` -> `Extension Search Path`
2. Add git url as an new search path: `git://github.com/iirthw/kit-extension-path-tracking?branch=main&dir=exts`

After configuring extension search path, start the extension:
1. `Window` -> `Extension Manager`
2. Find and enable path tracking extension

## Getting Started

### Launch a Path Tracking on a preset scene
### Create your custom setup

### Multiple Vehicles

## References

### Credits