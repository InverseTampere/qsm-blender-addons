# 2019-07-24 Version 0.9.0

- Fixed import bug, when importing mesh cylinder with single color value.
- Added option for *Advanced* growth animations.
	- User can select the number of growth groups.
	- Leaves are divided evenly into these groups and each group growth is controlled by a single shape key.
	- A custom property called *Growth* is generated for the mesh, and it drives all the shape key values, allowing simple animation of all the growth groups.
	- UI controls provided for customizing randomness of growth group start times when driven with the custom property.
- UV coordinates are now scaled to fill the unit square.

# 2018-02-09 Version 0.8.0

- Internal: updated custom setting structure to use property groups to avoid conflicts with other addons.
	- The scene object now has only one custom property for QSM import and one for leaf model import.
- Added additional leaf data import format: *Extended OBJ*.
- Added option to generate leaf growth animation with a shape key, when using the 'Extended OBJ' import format.
- Added option to assign leaf vertex colors randomly or from the input file, when using the 'Extended OBJ' import format.

# 2018-01-08 Version 0.7.0

## QSM import
- Cylinder vertex count minimum and maximum values
	- Separated parameters into two separate properties internally and cleaned UI.
	- Implemented conditions 3 <= min, max <= 50 and min <= max.
	- Changed default value of both min and max to 16.
- The QSM and leaf import panels now only show in object mode.
- Added error msg when given input path does not point to a file.
- Added option to generate curve bevel object, i.e., a unit Bezier circle parented to the QSM parent.

## Leaf model import
- Redesigned the UV-map generation process.
	- Option to skip UV generation (default).
	- UV-map shape has to presets and a custom option.
	- Custom maps can be generated based on a user-selectable mesh (x,y)-coordinates.

# 2017-12-08 Version 0.6.0

- Added documentation with images.
- Added three element custom coloring option.
- Updated Blender version to 2.79.

# 2017-06-29 Version 0.5.0

- Initial version.
- Implements three import modes:
	- mesh cylinder
	- cylinder-level lofted Bezier curves
	- branch-level lofted Bezier curves.
- Missing full documentation.