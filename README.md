# QSM Blender Addons

[![DOI](https://zenodo.org/badge/95752817.svg)](https://zenodo.org/badge/latestdoi/95752817)

Blender addon for importing cylindrical quantitative structure models (QSM) and leaf models (L-QSM). QSM is a description of the topology and geometry of a tree. For example the [TreeQSM](https://github.com/InverseTampere/TreeQSM) method can be used to reconstruct QSMs for terrestrial laser scanning data. These tree models can be augmented with a leaf cover, with the [QSM-FaNNI](https://github.com/InverseTampere/qsm-fanni-matlab) algorithm. The QSM-blender-addon can be used to import the resulting geometry from both procedures into [Blender](https://www.blender.org/).

In the future the repository may be extended with additional addons related to QSMs. However, at the moment the repository only covers the import addon.

## Description

The import addon can be used to import cylindrical QSMs and leaf models, using a graphical user interface added to the 3D view tool shelf. The required input data formats and options are described below.

## Importing QSMs / tree models

At this time, the addon only imports QSM geometry while ignoring most of the topology. Therefore, the input data format is a TXT-file, where each line describes a single cylinder of a QSM. The order of the values on a single row, is the following:

- branch index (1)
- starting point (3)
- axis direction (3)
- length (1)
- radius (1)
- optional parameters (N)

The number of elements used to describe the property is given in parenthesis. Branch index is used to define which cylinders form a branch. The next four parameters define the cylinder geometry. The optional parameters can be used to import color data for mesh based objects, as described later. As example the following text content describes the test QSM used in the [QSM-FaNNI](https://github.com/InverseTampere/qsm-fanni-matlab) repository, in the described format.

```
1  0.0000  0.0000 0.0000  0.0000  0.0000 1.0000 1.0000 0.3000
1  0.0000  0.0000 1.0000  0.7070  0.0000 0.7070 1.4140 0.2000
1  1.0000  0.0000 2.0000  1.0000  0.0000 0.0000 1.0000 0.1000
2  0.0000  0.0000 1.0000  0.0000  0.7070 0.7070 1.4140 0.2000
2  0.0000  1.0000 2.0000  0.0000  1.0000 0.0000 1.0000 0.1000
3  0.0000  0.0000 1.0000  0.0000 -0.7070 0.7070 1.4140 0.2000
3  0.0000 -1.0000 2.0000  0.0000 -1.0000 0.0000 1.0000 0.1000
4  0.0000  0.0000 1.0000 -0.7070  0.0000 0.7070 1.4140 0.2000
4 -1.0000  0.0000 2.0000 -1.0000  0.0000 0.0000 1.0000 0.1000
```

When running Blender, the import panel will be visible in the tool shelf of the 3D view under the title *QSM Import*. The user has the option to choose the imported object type from three options: 

1. mesh object
2. cylinder-level Bezier curves
3. branch-level lofted Bezier curves

The appearance of the UI depends on the selected import type. The resulting render with all three import types with the above example data, is shown below.

![Addon mesh UI](https://github.com/InverseTampere/qsm-blender-addons/raw/master/qsm-addon-example.png)

Examples of the UI are given in the subsection. Regardless of the import type, the common inputs for the import procedure are the following:

Name | Type | Description
---|---|---
Input file | File path | Path to a input file with cylinder parameters in the above format. The *Browse* button can be used to open a graphical file browsing view.
Stem material | Material name | Material to be applied to the cylinders of the branch with the lowest branch index. If no *Branch material* is given, *Stem material* will be applied to all cylinders. Selecting a stem material is optional.
Branch material | Material name | Material to be applied to cylinders not part of the stem branch. Selecting a branch material is optional.
Branch separation | Checkbox | Import individual branches as separate Blender objects. If unchecked the import results in a single object.

Once all the parameters have been selected, the import procedure is started using the *Import* button at the bottom of the panel. The addon will create an empty that will act as the parent of either the single resulting object, when branch separation is deactivated, or all the resulting branch object, when activated.

### Mesh import

![Addon mesh UI](https://github.com/InverseTampere/qsm-blender-addons/raw/master/qsm-addon-ui-mesh.png)

The level-of-detail for imported cylinder meshes can be selected with the *Vertex count Min* and *Max* parameters. Vertex count is defined as the number of vertices on a single circular loop of a cylinder, *i.e.*, the number of faces of the cylinder envelope. The two element vector parameter can be used to set the minimum and maximum vertex counts. The vertex count value is selected for each cylinder during the import, by linearly interpolating between the minimum and maximum vertex counts. The interpolation is defined as:

```python
nvert = vmin + (vmax-vmin)*(r-rmin)/(rmax-rmin)
```

where `nvert` is the selected vertex count, `vmin` and `vmax` are the minimum and maximum vertex counts selected by the user, respectively, `r` is the radius of the given cylinder and `rmin` and `rmax` are the minimum and maximum radius values given in the input file.

Internally the addon relies on the function `bpy.ops.mesh.primitive_cylinder_add()`. When the function is called the parameter `end_fill_type` is set to `'NGON'`, thus resulting in closed cylinders, *i.e.*, cylinders with ngons as their bottom and top planes.

### Coloring meshes

As mentioned above, additional parameters can be put at the end of the lines of the input text file for color information. The values can be either a single decimal between zero and one, or three. In both cases, a custom color layer is attached to the vertex data of the resulting object. The name of the layer is `Color` and it can be accessed with the *Attribute* node in the Node editor, for example as follows:

![Material example](https://github.com/InverseTampere/qsm-blender-addons/raw/master/qsm-addon-vertex-coloring.png)

When only one value is present instead of three, that value is replicated in all three elements of the color value. With three values the vector is stored directly in the color layer.

Vertex coloring is currently not available for curve objects.

### Bezier import

![Addon Bezier UI](https://github.com/InverseTampere/qsm-blender-addons/raw/master/qsm-addon-ui-bezier.png)

With the two Bezier curve based import types, the level-of-detail does not need to be fixed upon import. Instead, a lofting object is used to define the cross-section shape around the Bezier curve defining either a single cylinder or a complete branch. If the *Create bevel object* checkbox is checked, a Bezier circle curve object is created during the import process. The resolution of the curve is set to 5 by default, and the newly generated object is parented to the QSM parent object. If the checkbox is unchecked, the user can select the lofting object with the *Bevel Object* parameter that is an object selector. The lofting object should be a curve object, *e.g.*, a Bezier circle with a unit radius. The `Resolution` of the curves spline can be used to change the level-of-detail of all the cylinders in the resulting model, in the objects *Object data* panel.

Selecting *Bezier cylinder* as the import type, creates a single Bezier spline, with two curve points at the starting and ending point of the each cylinder. The radius value of the spline will be set to the radius value of the cylinder.

Selecting *Bezier branch* as the import type, creates a single Bezier spline per each branch. Curve points are placed at the center points of each cylinder, as well as, the first point at the starting point of the first cylinder, and the last point at the ending point of the last cylinder. At the last point the curve radius is set as 10% of the radius of the last cylinder. At the other curve points the radius is set as the radius of the respective cylinder, creating smooth tapering along the curve.

## Importing leaf models

![Leaf import UI](https://github.com/InverseTampere/qsm-blender-addons/raw/master/qsm-addon-ui-leaves.png)

Leaf models are imported from a text file in the Wavefront OBJ-format, that defines vertices and indices of vertices forming faces, or in a custom Extended OBJ-format with leaf basis geometry and leaf transition parameters. Each leaf is expected to have the same basis geometry.

### Input formats

For this importer, a Wavefront OBJ format can have to types of lines:
1. Vertex definitions: "v 0.000 1.000 0.500"
2. Face definitions: "f 1 2 3"

Vertex definition line has three coordinates. Face definition lines have from 3 to *N* indices of vertices that form the face. The indices correspond to vertices in the order they have been defined previously in the file.

The *Extended OBJ* format introduces a third, custom line type *Leaf definition*, that is designated with an *L* at the beginning of the line. The line type is followed by the following 15 or 18 parameters:
1. (1-3) Twig start point
2. (4-6) Leaf start point
3. (7-9) Leaf direction (start point to leaf tip)
4. (10-12) Leaf normal
5. (13-15) Leaf scale
6. (16-18) Leaf color [optional]

The structure of an Extended OBJ format input file consists of three parts. First, the vertices of the leaf basis geometry are defined (in OBJ format). Then the faces of the basis geometry are defined similarly. After that a leaf definition line should be given for each leaf. During the import procedure the leaf definition parameters are used to transform the basis geometry to generate the final individual leaves. Using leaf transformation parameters allows the optional generation of a growth animation using shape keys, as well as, the assignment of vertex colors.

### Options

The input parameters are the following:

Name | Type | Description
---|---|---
Import format | Drowdown | Format of the input data file. Currently two options: Wavefront OBJ and a custom extension *Extended OBJ*.
Input file | File path | Path to a input file with leaf geometry. The *Browse* button can be used to open a graphical file browsing view.
Material | Material name | Material applied to the leaves. Selecting a material is optional.
Assign vertex colors | Checkbox | When checked a new vertex color layer is created during the import process.
Color source | Dropdown | Source of the vertex color data. Currently two options: 1) Randomize, *i.e.*, sample a uniform distribution for each leaf and RGB color component; 2) From file, three additional columns from the input file are used as RGB color components.
Generate shape keys | Checkbox | When checked a shape key layer named *ReverseGrowth* is created during the import process for animating leaf growth. On this shape key layer each leaf is reduced to a single point in the origin of the respective twig.
Generate UV map | Checkbox | When unchecked the UV generation process is skipped.
UV map type | Dropdown | Only visible when *Generate UV map* is checked. Two presets: 1) isosceles triangle, 2) unit square. And a custom option, where the local (x,y)-coordinates of a selected mesh are copied for each imported leaf. Please note that the order of the vertices in the input mesh is key. Extruding starting from a single vertex is probably the easiest way to control the vertex order.
UV mesh data | Mesh selector | Only visible when *UV map type* is set to *Custom*. Used to select a mesh, whose (x,y)-coordinates are copied to form the UV-map of each leaf. Note that there is no checking that the coordinates lie in the interval [0,1].

### Running the import procedure

After filling in the required parameters, the import process is initiated using the *Import leaf model* button. An example of a rendered, imported leaf model and a QSM can be seen below.

![Example render](https://github.com/InverseTampere/qsm-fanni-matlab/raw/master/src/test_result.png)

If a UV-map is selected to be generated, a map named *Overlapping* is added to the mesh data. Individual leaves of the leaf model are overlayed in the resulting UV-map, *e.g.*, to project the same image onto all of them. Note that the leaves can be colored, for example with an uniform color, even without a UV-map.

If vertex colors are set to be assigned, a vertex color layer named *Color* is added to the mesh data. The layer can be accessed in the material node editor with the Attribute node by giving the name of the vertex color layer, which in this case is "Color".

If shape key generation is active, two shape key layers are created. The *Basis* layer contains the data as it is given in the input data. On the *ReverseGrowth* layer the vertices of each leaf are reduced to single points at the respective twig starting points. When transforming or animating the value of the *ReverseGrowth* layer from zero to one, the leaves shrink from their actual size to unseen points. Running the animation in the opposite direction gives the impression of leaf growth.
