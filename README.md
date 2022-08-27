# Vehicle Path Tracking Extension

## 1. About

Omniverse Vehicle Path tracking extension allows a physics-enabled vehicle created
with WizardVehicle to move and track a user-defined path.
User-defined path is represented by USD BasisCurves, and a path tracking algorithm
is inspired by a classic Pure Pursuit algorithm [3].

![Vehicle Path Tracking Preview](exts/omni.path_tracking/data/preview.PNG)
Figure 1. Preview of Vehicle Path Tracking Extension

### System Requirements:

- `Code 2022.1.3+` or `Create 2022.1.5+`
- `Pyhton 3.7+` (that should be the case by default when using Omniverse Kit's embedded `CPython 3.7`)

### Limitations

For the moment the extension is simple and a number of 
shortcuts has been taken, simplification applied, including the follwoing:

* Pure Pursuit Tracking algorithm is kinematic-based and therefore certain dynamics
properties are not taken into account, such as tire slipping etc. 
* A vehicle might go off the track if proposed a physically "impossible" trajectory, or on high speeds while turning.
* Limited unit test coverage; occasional bugs might exist.

### Future Work

* Getting rid of limitations, bugfix;
* Add an implementation for automatic computation of vehicle path which satisfies certain constraints (points to be visited, obstacle avoidance);
* Add more sophisticated path tracking algorithm.

## 2. Installing Extension

Pre-requisites:
* `Git`
### Add Git URL to extension search path 

Inside Omniverse Code or Create:
1. `Window` -> `Extension Manager` -> ⚙️ `Gear Icon` -> `Extension Search Path`
2. Add git url as an new search path: `git://github.com/iirthw/kit-extension-path-tracking?branch=main&dir=exts`

### Add path to local clone to extension search path 

1. `git clone -b main $PATH_TO_DIR
2. `Window` -> `Extension Manager` -> ⚙️ `Gear Icon` -> `Extension Search Path`
3. Add path to just cloned extension as a extension search path: `$PATH_TO_DIR/exts`

After configuring extension search path, start the extension:
1. `Window` -> `Extension Manager`
2. Find in the extension list and enable path tracking extension (Figure 2)


<img src="exts/omni.path_tracking/data/img/figures/figure_01.png" alt="activating extension" style="height:400px;"/></br>
Figure 2. Activating path tracking extension in extension manager.</br>

---

## 3. Getting Started

### 3.1. Launch a Path Tracking on a preset scene

The fastest way to test path tracking extension is to use preset vehicle and curve.
In order to get started with the preset please proceed as follows (Figure 3):
1. Click `Load a preset scene` button
2. Click `Start scenario` button

<img src="exts/omni.path_tracking/data/img/figures/figure_02.png" style="width:600px" alt="extension preview"><br/>
Figure 3. Getting started with preset scene.

The extension also allows a quick way to load a ground plane, a sample physics vehicle, and a sample basis curve. See Figure 4.

<img src="exts/omni.path_tracking/data/img/figures/figure_03.png" style="width:600px" alt="extension controls"/><br/>
Figure 4. Extension helper controls.

---

### 3.2. Create your custom vehicle-to-curve attachment setup

Extension supports path tracking for any vehicle based on Omniverse Vehicle Dynamics.
One could load a template vehicle using the extension ui, or using a conventional method via `Create`->`Physics`->`Vehicle`.
It is also straightforward to add a custom mesh and materials to a physics vehicle [2].

You can create a curve for vehicle path tracking using either of the following methods (Figure 5):
- `Create`->`BasisCurves`->`From Bezier`
- `Create`->`BasisCurves`->`From Pencil`

<img src="exts/omni.path_tracking/data/img/figures/figure_04.png" style="height:500px"/>  |  <img src="exts/omni.path_tracking/data/img/figures/figure_05.png" style="height:500px"/><br/>
Figure 5. Create a custom path to track via USD BasisCurves.


---

Once a physics vehicle and a path to be tracked defined by USD BasisCurves is created, select the WizardVehicle and the BasisCruves prims (via Ctrl-click)
and click `Attach Selected` button. Note that is very important to select specifically `WizardVehicle` prim in the scene,
not `WizardVehicle/Vehicle` for instance.
Please see Figure 6 for the illustration.

<img src="exts/omni.path_tracking/data/img/figures/figure_06.png" style="width:1100px"/><br/>
Figure 6. Attachment of a path (USD BasisCurves) to a physics-enabled vehicle.

If vehicle-to-curve attachment was successful it should be reflected on the
extension UI (Figure 7).

<img src="exts/omni.path_tracking/data/img/figures/figure_07.png" style="width:600px"/><br/>
Figure 7. Successful vehicle-to-curve attachment is shown on the right side.

If you want to get rid of all already existing vehicle-to-curve attachments please click `Clear All Attachments` (Figure 8).
It is very important to clear vehicle-to-curve attachments, when changing vehicles and correspondig path to be tracked.

<img src="exts/omni.path_tracking/data/img/figures/figure_08.png" style="width:600px"/><br/>
Figure 8. Removing existing vehicle-to-curve attachment.

### 3.3. Multiple Vehicles

The extension supports multiple vehicle-to-curve atttachments.
Note, that in order for attachment to work, a pair of `WizardVehicle` and
`BasisCurve` objects should be selected and attached separately.
Results of path tracking with multiple vehicles is shown on Figure 9.

<img src="exts/omni.path_tracking/data/img/figures/figure_09_01.png" style="height:300px"/> <img src="exts/omni.path_tracking/data/img/figures/figure_09_02.png" style="height:300px"/> <img src="exts/omni.path_tracking/data/img/figures/figure_09_03.png" style="height:300px"/><br/>
Figure 9. Support of multiple vehicle-to-curve attachments.

---

## 4. References

1. [Omniverse Developer Contest] https://www.nvidia.com/en-us/omniverse/apps/code/developer-contest/
2. [Omniverse Vehicle Dynamics] https://docs.omniverse.nvidia.com/app_create/prod_extensions/ext_vehicle-dynamics.html
3. [Coutler 1992, Pure Pursuit Path Tracking Algorithm] https://www.ri.cmu.edu/pub_files/pub3/coulter_r_craig_1992_1/coulter_r_craig_1992_1.pdf
4. [CC Attribution-NonCommercialCreative Commons] Credits for Dodge Challenger car model: https://sketchfab.com/3d-models/dodge-challenger-ef40662c84eb4beb85acdfce5ac4f40e
