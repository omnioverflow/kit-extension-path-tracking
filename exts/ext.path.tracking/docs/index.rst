omni.path.tracking
########################

Omniverse Vehicle Path tracking extension allows a physics-enabled vehicle created
with a PhysX Vehicle extension (omni.physx.vehicle) to move and automatically track a user-defined path.
User-defined path is represented by an instance of USD BasisCurves, and a path tracking algorithm
is inspired by a classic Pure Pursuit algorithm.


The fastest way to evaluate how vehicle path tracking extension works is to use a preset vehicle and curve.
In order to get started with the preset configuration please proceed as follows:
1. Click `Load a preset scene` button
2. Click `Start scenario` button

---

Extension supports path tracking for any Omniverse PhysX Vehicle.
One could load a template vehicle using the extension ui, or using a conventional method via `Create`->`Physics`->`Vehicle`.
It is also straightforward to add a custom mesh and materials to a physics vehicle.

You can create a curve for vehicle path tracking using either of the following methods:
- `Create`->`BasisCurves`->`From Bezier`
- `Create`->`BasisCurves`->`From Pencil`

---

Once a physics vehicle and a path to be tracked defined by USD BasisCurves is created, select the WizardVehicle and the BasisCruves prims in the stage (via Ctrl-click)
and click `Attach Selected` button. Note that is very important to select specifically `WizardVehicle` prim in the scene,
not `WizardVehicle/Vehicle` for instance.

If vehicle-to-curve attachment was successful it should be reflected on the
extension UI.

When vehicle-to-curve attachment(s) is created, proceed by clicking `Start Scenario` button.

If you want to get rid of all already existing vehicle-to-curve attachments please click `Clear All Attachments`.