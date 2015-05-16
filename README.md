# BlenderBooleanPush
Uses blenders booleans to perform a Extrude/Push without cleanup.

### Status

Yes, at the moment this is a massive kludge

- [x] auto remove modifier if not applied
- [x] view rotation passthrough (only zoom)
- [x] removed sverchok dependency (https://github.com/nortikin/sverchok/blob/master/utils/sv_bmesh_utils.py)
- doesn't update in realtime as slider moves, only once stationary
- not implemented ctrl+enter to apply
- not implemented mouse x,y position as distance instead of sliders
- not implemented multiface selection, join faces if not islands.. else gather face data separately
- remove doubles needed

This will depend on feedback, if noone uses it except me then it won't likely progress, but if there's feedback and perhaps contributions then who knows.
 

