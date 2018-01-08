# This file is part of QSM-blender-addons.
# 
# QSM-blender-addons is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# QSM-blender-addons is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with QSM-blender-addons.  If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Tree model (QSM) and leaf model (L-QSM) importer",
    "category": "Import-Export",
    "author": "Markku Åkerblom",
    "version": (0, 7, 0),
    "blender": (2, 79 ,0),
    "location": "View 3D > Tool Shelf > QSM",
    "description": "Addon that imports Quantitative Structure Models as either individual cylinders, or as continuous surfaces. A branch is either a collection of Bezier line segments (cylinders) or a Bezier curve. Each type of Bezier curve is lofted by applying a bevel object such as a Bezier circle. The add-on can also import leaf models in Wavefront OBJ format. A single leaf should be either a triangle or a rectangle.",
    'support': 'TESTING',
}

import bpy
import sys
import os
import math
import bmesh
import mathutils
from mathutils import Vector, Matrix
import datetime

# Print progress in the console every Nth row.
def print_progress(NLine, iLine, d, last):
    
    # Current percentage with precision d.
    p = float(math.floor(d*iLine/NLine))/d

    # Display if first line, or if percentage has changed.
    if iLine == 0 or p > last:

        # Update last percentage.
        last = p

        # Number of digits in line count.
        w = len(str(NLine))

        # Message string.
        msg = "Processing line %" + str(w) + "i of %i (%2i%%)"

        # Format message with current numbers.
        msg = msg % (iLine+1, NLine,p*100)

        # Display message.
        sys.stdout.write(msg + chr(8) * len(msg))
        sys.stdout.flush()

    return last

class QSMPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""

    bl_label = "QSM Import"
    bl_idname = "SCENE_PT_qsm"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "QSM"
    bl_context = "objectmode"

    # Layout of the QSM import panel.
    def draw(self, context):

        layout = self.layout
        scene = context.scene

        # Data variable for searching materials.
        data = bpy.data

        # Import mode as a button selector.
        row = layout.row()
        row.prop(scene, "qsmImportMode", expand=True)
                
        
        # Input file.
        row = layout.row()
        row.prop(scene, "qsm_file_path")

        # Stem material select.
        row = layout.row()
        row.prop_search(scene, "qsmStemMaterial", data, "materials")

        # Branch material select.
        row = layout.row()
        row.prop_search(scene, "qsmBranchMaterial", data, "materials")

        layout.separator()

        # Branch separation.
        row = layout.row()
        row.prop(scene, "qsmSeparation")

        #layout.separator()

        # UI elements for mesh objects.
        if scene.qsmImportMode == 'mesh_cylinder':

            # Vertex count inputs.
            row = layout.row()
            layout.label("Vertex count:")

            row = layout.row(align=True)
            row.prop(scene,"qsmVertexCountMin", text='Min')
            row.prop(scene,"qsmVertexCountMax", text='Max')

        # UI elements for bezier objects.
        elif scene.qsmImportMode == 'bezier_cylinder' or \
             scene.qsmImportMode == 'bezier_branch':

             # Bevel object generation.
            row = layout.row()
            row.prop(scene, "qsmGenerateBevelObject")

            if not scene.qsmGenerateBevelObject:

                # Bevel object selector.
                row = layout.row()
                row.prop_search(scene, "qsmBevelObject", scene, "objects")
        
        layout.separator()

        # Colormap update button.
        if scene.qsmImportMode == 'mesh_cylinder':
            row = layout.row()
            row.operator("qsm.update_colourmap")

        # Import buttons.
        row = layout.row()
        row.operator("qsm.qsm_import")



    
class LeafModelPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""

    bl_label = "Leaf model import"
    bl_idname = "SCENE_PT_leaf_model"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'QSM'
    bl_context = "objectmode"

    # Layout of the leaf model import panel.
    def draw(self, context):

        layout = self.layout
        scene = context.scene 

        # Data variable for searching materials.
        data = bpy.data
        
        # Input file.
        row = layout.row()
        row.prop(scene, "leaf_model_file_path")

        # Bevel object selector.
        row = layout.row()
        row.prop_search(scene, "leafModelMaterial", data, "materials")     
        
        # Leaf vertex count selector.
        #row = layout.row()
        #row.prop(scene,"leaf_model_vertex_count")

        layout.separator()

        # Boolean: generate UVs.
        row = layout.row()
        row.prop(scene, "leafUvGeneration")

        if scene.leafUvGeneration:
            layout.separator()

            # Dropdown: UV type.
            row = layout.row()
            row.prop(scene, "leafUvType", expand=False)

            if scene.leafUvType == 'custom':

                # Mesh selector: UV source mesh.
                row = layout.row()
                row.prop_search(scene, "leafUvSource", bpy.data, "meshes")

        layout.separator()
        
        # Import button.
        row = layout.row()
        row.operator("leaf.import_leaves")




class ImportLeafModel(bpy.types.Operator):
    """Import leaves as planes"""

    bl_idname = "leaf.import_leaves"
    bl_label = "Import leaf model"
    
    # Operator for importing leaf model.
    def execute(self, context):

        print('Importing leaves.')

        # Current scene for reading parameters for importing.        
        scene = context.scene
        
        # Path to input file.
        filestr = scene.leaf_model_file_path

        # Check for empty filepath.
        if len(filestr) == 0:
            self.report({'ERROR_INVALID_INPUT'},'Missing input file path.')
            print('Cancelled.')
            return {'CANCELLED'}

        # Convert to absolute path.
        file_path = bpy.path.abspath(filestr)

        # Check that file exists.
        if not os.path.isfile(file_path):
            self.report({'ERROR_INVALID_INPUT'},'No file with given path.')
            print('Cancelled.')
            return {'CANCELLED'}

        # Check if UVs are to be generated.
        fUvGeneration = scene.leafUvGeneration

        if fUvGeneration:
            if scene.leafUvType == 'custom':
                SourceName = scene.leafUvSource

                UvSource = bpy.data.meshes.get(SourceName)

                if not UvSource:
                    self.report({'ERROR_INVALID_INPUT'},'Custom UV generation selected, but UV mesh not found.')
                    print('Cancelled.')
                    return {'CANCELLED'}


        # Record start time.
        start = datetime.datetime.now()
        
        # Use built-in OBJ-importer with fixed parameters.
        bpy.ops.import_scene.obj \
          (
            filepath=file_path,
            axis_forward='Y',
            axis_up='Z',
            filter_glob="*.obj;*.mtl",
            use_edges=True,
            use_smooth_groups=True,
            use_split_objects=False,
            use_split_groups=False,
            use_groups_as_vgroups=False,
            use_image_search=False,
            split_mode='OFF',
            global_clamp_size=0
          )

        # Selected material for leaves.
        matname = scene.leafModelMaterial

        # Check if material selected.
        if len(matname) == 0:
            print('No material set.')
            mat = None
        else:
            # Try to get material by input name.
            mat = bpy.data.materials.get(matname)

            # Print warning if does not exist.
            if not mat:
                print('Material not found.')
        

        # Get imported objects, assumed to be selected.
        selected_obj = bpy.context.selected_objects[:]

        # Flag: skip UV generation due to input errors.
        fSkipUv = False
        
        if fUvGeneration:

            # Name of the UV map to be created. Using "Overlapping" because
            # all leaves are overlayed in UV coordinates, to allow simple 
            # UV mapping of a single leaf image.
            MapName = 'Overlapping'

            leafUvType = scene.leafUvType

            
            if leafUvType == 'isosceles_triangle':
                # UV vertex locations for a isosceles triangle.
                uv_verts = [Vector((1,0)), Vector((0.5,1)), Vector((0,0))]
            
            elif leafUvType == 'square':
                # UV vertex locations for a square.
                uv_verts = [Vector((1,0)), Vector((1,1)),Vector((0,1)), Vector((0,0))]

            elif leafUvType == 'custom':

                # Initialize array.
                uv_verts = []

                # Copy local (x,y)-coordinates of source mesh.
                for v in UvSource.vertices:
                    x = v.co[0]
                    y = v.co[1]
                    uv_verts.append(Vector((x,y)))                    

            else:
                # Otherwise, the selection is illegal.
                self.report({'WARNING'},'Unknown UV generation type selected. UV generation skipped.')
                fSkipUv = True

            # Number of vertices in input UV map.
            NVert = len(uv_verts)
            
                           

        # Iterate over selected objects.
        for obj in selected_obj:
            
            # Mesh of selected object.
            me = obj.data

            # Set material if exists.
            if mat:
                me.materials.append(mat)

            # UV map creation.
            if fUvGeneration and xnot fSkipUv: 
            
                # Create new UV map.
                me.uv_textures.new(MapName)
                
                # Create a bmesh from mesh data for UV map manipulation.
                bm = bmesh.new()
                bm.from_mesh(me)
                
                # Create UV layer.
                uv_layer = bm.loops.layers.uv[0]
                
                # Initialize lookup table.
                bm.faces.ensure_lookup_table()
                
                # Number of leaves.
                NFace = len(bm.faces)

                # Iterate over leaves.
                for iFace in range(NFace):

                    # Number of vertices in face.
                    NFaceVert = len(bm.faces[iFace].loops)
                    
                    # Iterate over vertices in leaf.
                    for iVert in range(NFaceVert):
                        
                        # Index of current vertex modulo set number of vertices.
                        uv_index = iVert%NVert
                        # Set UV map vertex to coordinate given by above index.
                        bm.faces[iFace].loops[iVert][uv_layer].uv = uv_verts[uv_index]
                
                # Update mesh data.
                bm.to_mesh(me)
        
        # Record end time.
        end = datetime.datetime.now()

        # Compute duration.
        delta = end - start

        # Format duration as string.
        timestr = "{:.1f}".format(delta.total_seconds())

        # Print duration.
        print('Done is ' + timestr + ' seconds.')

        return {'FINISHED'}


class ImportQSM(bpy.types.Operator):
    """Import QSM as a collection of individual cylinders"""

    bl_idname = "qsm.qsm_import"
    bl_label = "Import"

    def createQSMParent(self, scene):

        # Create empty parent object for the resulting object(s).
        EmptyParent = bpy.data.objects.new('TreeParent', None)
        EmptyParent.empty_draw_size = 1
        EmptyParent.empty_draw_type = 'PLAIN_AXES'
        EmptyParent.location = Vector((0.0,0.0,0.0))
        
        # Link empty to scene.
        scene.objects.link(EmptyParent)

        # Return parent object.
        return EmptyParent

    # Function to create mesh cylinder by copying the data
    # of a base object, and then transforming it.
    def addMeshCylinder(self, baseobj, cp, rot, h, r):

        # Copy base object and data.
        ob = baseobj.copy()
        ob.data = baseobj.data.copy()

        # Translate to center point.
        ob.location = cp

        # Scale to match cylinder radius and length.
        ob.scale = (r,r,h)

        # Set rotation.
        ob.rotation_euler = rot

        # Link new object to scene.
        bpy.context.scene.objects.link(ob)

        # Return new object.
        return ob

    # Function to import a QSM as mesh cylinders.
    def import_as_mesh_cylinders(self, context, file_path, EmptyParent, 
                                 fBranchSeparation,
                                 matStem, matBranch):

        print('Importing QSM as mesh cylinders.')
        
        # Current scene to read properties.
        scene = context.scene
        
        # Number of imported branches.
        NBranch = 0
        # Index of last branch in input file.
        iLastBranch = 0

        # Flag: should the cylinder index be stored in a vertex layer.
        # Allows updating vertex colour afterwards.
        fIdColor = True

        # Minimum vertex count in cylinder rings.
        vmin = scene.qsmVertexCountMin
        # Maximum vertex count.
        vmax = scene.qsmVertexCountMax

        # Number of different vertex counts.
        vcount = vmax - vmin + 1

        # Initialize list of base objects that will be copied for optimization.
        baseobj = []

        # Generate a base object for each vertex count.
        for v in range(0,vcount):

            # Number of vertices in the rings of the current base object cylinder.
            nvert = vmin+v

            # Add a cylinder primitive with the built-in operator.
            bpy.ops.mesh.primitive_cylinder_add(vertices=nvert,
                                                radius=1,
                                                depth=1,
                                                end_fill_type='NGON',
                                                view_align=False,
                                                enter_editmode=False,
                                                location=(0.0,0.0,0.0),
                                                rotation=(0.0,0.0,0.0))

            # Get newly generated base object.
            ob = context.selected_objects[0]
            # Deselect.
            ob.select = False

            # Get mesh data of base object.
            me = ob.data

            # Translation vector.
            point = Vector((0.0,0.0,-0.5))

            # Move base object so that the starting point is at the origin.
            mat = Matrix.Translation(ob.matrix_world.translation - point)
            me.transform(mat)

            # Update mesh data.
            me.update()
            # Do opposite transition in object mode to get object origin corrected.
            ob.matrix_world.translation = point

            # Create bmesh object to set the shading of the envelope faces as smooth.
            bm = bmesh.new() 
            bm.from_mesh(me)

            # Iterate over the faces other than the last two which are the caps.
            for f in bm.faces[-(nvert+2):]:
                if f.select:
                    if len(f.verts) == 4:
                        # Set shading smooth.
                        f.smooth = True

            # Update mesh data and delete bmesh.
            bm.to_mesh(me)
            bm.free()

            # Add base object to list.
            baseobj.append(ob)

        # Minimum vertex count must be at least three.
        if vmin < 3:
            vmin = 3

        # Maximum count must be greater than the minimum.
        if vmax < vmin:
            vmax = vmin

        with open(file_path) as lines:
            
            # File line count.
            NLine = 0

            # Last displayed percentage.
            PLast = 0

            # Iterate through the file rows, recording the count and 
            # minimum and maximum radius values.
            for line in lines:

                # Increase counter.
                NLine = NLine + 1

                # Split file line into parameter array.
                params = line.split()

                # Ignore rows with too few parameters.
                if len(params) < 9:
                    continue

                # Get radius parameter of row.
                r = float(params[8])

                # Initialize min and max on first row.
                if NLine == 1:
                    rmin = r
                    rmax = r
                else:
                    # Update extremes if necessary.
                    if r < rmin:
                        rmin = r
                    if r > rmax:
                        rmax = r
            
            # Number of digits to use in object naming.
            NDigit = len(str(NLine))
            
            # Return to file beginning for second iteration.
            lines.seek(0)

            # List of objects that are later joined to form either a branch or the full QSM.
            allobj = []

            # Index of current cylinder.
            iCyl = 0
            
            # Iterate over rows in input file.
            for iLine, line in enumerate(lines):

                # Split row into parameters.
                params = line.split()

                # Ignore rows with too few parameters.
                if len(params) < 9:
                    continue

                # Increase number of cylinders.
                iCyl += 1
        
                # Print progress in the console every nth row.
                PLast = print_progress(NLine, iLine, 10, PLast)

                # Store parameters.
                iBranch = int(float(params[0]))
                sp = Vector((float(params[1]), float(params[2]), float(params[3])))
                ax = Vector((float(params[4]), float(params[5]), float(params[6])))
                h  = float(params[7])
                r  = float(params[8])

                # Convert axis to Euler rotation.
                rot = ax.to_track_quat('Z', 'Y').to_euler()

                # Select number of vertices based on linear interpolation of radius.
                nvert = vmin + (vmax-vmin)*(r-rmin)/(rmax-rmin)
                # Convert result to an integer by rounding.
                nvert = int(round(nvert))

                # Index of base object based on vertex count.
                iObj = nvert - vmin

                # Flag: file contains an additional row to use as colourmap values.
                fVertColor = False

                # Check if extra column for colourmap exists.
                if len(params) > 9:
                    fVertColor = True
                    VertColor = float(params[9])
                    if len(params) > 11:
                        VertColor = Vector((float(params[9]), float(params[10]), float(params[11])))

                # If this is the first branch, or the index differs form the previous row.
                if NBranch == 0 or iBranch != iLastBranch:

                    # Update index of previous branch.
                    iLastBranch = iBranch
                    # Increase branch count.
                    NBranch += 1

                    # If multiple objects are created, use unique object and mesh names
                    # by numbering them.
                    if fBranchSeparation:
                        meshname = "branch_" + str(NBranch).zfill(NDigit)
                        objname  = "branch_" + str(NBranch).zfill(NDigit)
                    else:
                        meshname = "qsm_mesh"
                        objname   = "qsm"

                    # Start a new branch if this is the first one, or if the user
                    # has selected to separate branches.
                    if NBranch == 1 or fBranchSeparation:

                        # If separate branches and not the first one.
                        if NBranch > 1:

                            # Select all objects in last branch.
                            for ob in allobj:
                                ob.select = True

                            # Set one of them as active.
                            scene.objects.active = allobj[0]
                            # Join the objects.
                            bpy.ops.object.join()
                            # Apply object scale.
                            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                            # Deselect resulting object.
                            allobj[0].select = False
                            # Initialize array for next branch.
                            allobj = []
                        
                        # Add current cylinder by copying and modifying the base object.
                        ob = self.addMeshCylinder(baseobj[iObj],sp,rot,h,r)
                        
                        # Set name and parent.
                        ob.name = objname
                        ob.parent = EmptyParent

                        # Get mesh data.
                        me = ob.data
                        # Set mesh name.
                        me.name = meshname

                        # Add stem material to object if it is the first branch,
                        # or if branch material is not set (same material for all branches),
                        # and if stem material is set.
                        if iBranch == 1 or not matBranch:
                            if matStem:
                                me.materials.append(matStem)
                        
                        # Add branch material if material is set and it is different from the
                        # stem material.
                        if matBranch and (matStem != matBranch):
                            me.materials.append(matBranch)

                    # No need to change object even though the branch index changed.
                    else:
                        ob = self.addMeshCylinder(baseobj[iObj],sp,rot,h,r)

                # Still on same branch index.
                else:
                    ob = self.addMeshCylinder(baseobj[iObj],sp,rot,h,r)

                # Add new object to list of cylinders in current branch.
                allobj.append(ob)

                # Get mesh data of new cylinder.
                me = ob.data
                # Create a bmesh object for colourmap creation from mesh data.
                bm = bmesh.new() 
                bm.from_mesh(me)

                # If cylinder ID should be stored on the model.
                if fIdColor:
                    # Get or create new layer for index colouring.
                    layer = bm.verts.layers.int.get("CylinderId")
                    if not layer:
                        layer = bm.verts.layers.int.new("CylinderId")
                    
                    # Iterate over mesh vertices and set index colouring value to
                    # index of the cylinder.
                    for v in bm.verts:
                        v[layer] = iCyl

                # If vertex colour information is present in the input file
                # add colour layer and assign colour for each vertex.
                if fVertColor:
                    # Get or create new layer for input colourmap.
                    colors = bm.loops.layers.color.get("Color")
                    if not colors:
                        colors = bm.loops.layers.color.new("Color")
                       
                    # Iterate over vertices and set vertex colour by
                    # repeating the input value three times.
                    for v in bm.verts:
                        for loop in v.link_loops:
                            if len(VertColor) > 1:
                                loop[colors] = VertColor
                            else:
                                loop[colors] = [VertColor] * 3

                # Update mesh data and delete bmesh.
                bm.to_mesh(me)
                bm.free()
                
            # Select all cylinders of last object.
            for ob in allobj:
                ob.select = True

            # Set active object.
            scene.objects.active = allobj[0]

            # Join all cylinders in list.
            bpy.ops.object.join()
            # Apply object scale.
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


        # As clean-up, remove the base objects and their mesh data.
        for ob in baseobj:
            scene.objects.unlink(ob)
            bpy.data.objects.remove(ob)

        return {'FINISHED'}


    # Function to import a QSM as Bezier cylinders.
    def import_as_bezier_cylinders(self, context, file_path, EmptyParent, fBranchSeparation, 
                                   matStem, matBranch, BevelObject):

        print('Importing QSM as Bezier cylinders.')
        
        # Current scene to read properties.
        scene = context.scene
        
        # Number of branches.
        NBranch = 0
        # Index of last branch.
        iLastBranch = 0

        # Length of right and left control handles.
        len_r = 0.45
        len_l = 0.45

        with open(file_path) as lines:
            
            # Count number of lines in file.
            NLine = sum(1 for line in lines)
            
            # Number of digits to use in object naming.
            NDigit = len(str(NLine))
            
            # If file did not have any lines.
            if NLine <= 0:
                self.report({'ERROR_INVALID_INPUT'},'Selected file is empty.')
                return {'CANCELLED'}

            # Return to file beginning.
            lines.seek(0)

            # Last displayed percentage.
            PLast = 0
            
            # Iterate over file rows.
            for iLine, line in enumerate(lines):

                # Split row into parameters.
                params = line.split()

                # Ignore rows with too few parameters.
                if len(params) < 9:
                    continue
        
                # Print progress in the console every nth row.
                PLast = print_progress(NLine, iLine, 10, PLast)

                # Get cylinder parameters.
                iBranch = int(float(params[0]))
                sp = (float(params[1]), float(params[2]), float(params[3]))
                ax = (float(params[4]), float(params[5]), float(params[6]))
                h  = float(params[7])
                r  = float(params[8])

                # If the first branch or branch index has changed.
                if NBranch == 0 or iBranch != iLastBranch:

                    # Update last index.
                    iLastBranch = iBranch
                    # Increase branch count.
                    NBranch += 1

                    # If multiple objects are created, use unique object and mesh names
                    # by numbering them.
                    if fBranchSeparation:
                        curvename = "branch_" + str(NBranch).zfill(NDigit)
                        objname   = "branch_" + str(NBranch).zfill(NDigit)
                    else:
                        curvename = "qsm_curve"
                        objname   = "qsm"

                    # Start a new branch if this is the first one, or if the user
                    # has selected to separate branches.
                    if NBranch == 1 or fBranchSeparation:

                        # Create Bezier curve for new branch.
                        curvedata = bpy.data.curves.new(name=curvename, type='CURVE')
                        curvedata.dimensions = '3D'
                        # Set bevel object.
                        curvedata.bevel_object = BevelObject
                        curvedata.use_fill_caps = True

                        # Add stem material to object if it is the first branch,
                        # or if branch material is not set (same material for all branches),
                        # and if stem material is set.
                        if iBranch == 1 or not matBranch:
                            if matStem:
                                curvedata.materials.append(matStem)
                        
                        # Add branch material if material is set and it is different from the
                        # stem material.
                        if matBranch and (matStem != matBranch):
                            curvedata.materials.append(matBranch)

                        # Create new object with the curve data.
                        objectdata = bpy.data.objects.new(objname, curvedata)
                        # Position to origin.
                        objectdata.location = (0,0,0)
                        # Parent to created empty.
                        objectdata.parent = EmptyParent
                        # Link to scene.
                        bpy.context.scene.objects.link(objectdata)
                        # Set as selected.
                        objectdata.select = True

                # For each cylinder add a new Bezier spline into the curve data.
                polyline = curvedata.splines.new('BEZIER')
                # Add an extra point to have two in total.
                polyline.bezier_points.add(1)
                # Set order to one as the cylinder axis will be linear.
                polyline.resolution_u = 1

                # Create the starting (i == 0) and ending (i == 1) points of the spline.
                for i in (0,1):

                    # Position on axis (0 = bottom, 1 = top).
                    hf = i

                    # Position of curve point.
                    co    = [sp_i+h*ax_i*hf              for sp_i,ax_i in zip(sp,ax)]
                    # Position of left handle.
                    left  = [sp_i+h*ax_i*hf-len_l*ax_i*h for sp_i,ax_i in zip(sp,ax)]
                    # Position of right handle.
                    right = [sp_i+h*ax_i*hf+len_r*ax_i*h for sp_i,ax_i in zip(sp,ax)]

                    # Set Bezier curve point properties.
                    polyline.bezier_points[i].co = co
                    polyline.bezier_points[i].handle_left = left
                    polyline.bezier_points[i].handle_right = right

                    # Set curve point radius.
                    polyline.bezier_points[i].radius = r

                    # Assign proper materials from the splots.
                    if iBranch == 1:
                        if matStem:
                            polyline.material_index = 0
                    else:
                        if matBranch or matStem:
                            polyline.material_index = len(curvedata.materials)

                    # Set curve resolution.
                    polyline.resolution_u = 1
                    polyline.use_endpoint_u = True


    # Function to add a branch-level Bezier spline to the given
    # curve data, from the given cylinder parameters.
    def addBezierCurve(self,curvedata, SP, AX, H, R):
        

        # Number of curve points = cylinder count + start point + end point.
        NPoint = len(R) + 2

        # Create new spline.
        polyline = curvedata.splines.new('BEZIER')
        # Add curve points to get NPoint points.
        polyline.bezier_points.add(NPoint - 1)

        # Iterate over cylinders in the input parameter lists.
        for i in range(0,NPoint):

            # Base of first cylinder.
            if i == 0:
                # Use normal radius.
                rf = 1 # Radius scaler
                # Point at the bottom of the cylinder.
                hf = 0 # Position along cylinder axis.
                j = 0  # Index of curve point.

                # Shorter handles as there are more than one curve point
                # "on" the first cylinder.
                len_r = 0.25 # Length of right handle.
                len_l = 0.25 # Length of left handle.

            # Tip of last cylinder.
            elif i == NPoint - 1:
                # Taper to 10% of radius.
                rf = 0.1
                # Point at the end of the cylinder.
                hf = 1
                # Last curve point.
                j = len(SP) - 1

                # Shorter handles as there are more than one curve point
                # "on" the last cylinder.
                len_l = 0.25
                len_r = 0.25

            # Curve points in the middle of the cylinders.
            else:
                # Normal radius.
                rf = 1
                # Point at the center of cylinder.
                hf = 0.5
                j = i - 1

                # Normal handle length, unless its the left handle of the
                # first cylinder, or the right handle of the last cylinder.
                len_r = 0.45
                len_l = 0.45

                # Middle of the first cylinder.
                if i == 1:
                    len_l = 0.25

                # Middle of the last cylinder.
                if i == NPoint - 2:
                    len_r = 0.25

            # Get parameters of current cylinder.
            sp = SP[j] # Start point
            ax = AX[j] # Axis
            h  = H[j]  # Length
            r  = R[j]  # Radius

            # Compute curve point location.
            co    = [sp_i+h*ax_i*hf              for sp_i,ax_i in zip(sp,ax)]
            # And handle locations.
            left  = [sp_i+h*ax_i*hf-len_l*ax_i*h for sp_i,ax_i in zip(sp,ax)]
            right = [sp_i+h*ax_i*hf+len_r*ax_i*h for sp_i,ax_i in zip(sp,ax)]

            # Set curve point properties and radius.
            polyline.bezier_points[i].co = co
            polyline.bezier_points[i].handle_left = left
            polyline.bezier_points[i].handle_right = right
            polyline.bezier_points[i].radius = r*rf

        # Set curve resolution based on the number of curve points. 
        # At most the resolution can be 10.
        polyline.resolution_u = min(NPoint - 2,10)
        polyline.use_endpoint_u = True

        # Return new spline.
        return polyline


    
    # Function to import a QSM as branch-level bevelled Bezier curves.
    def import_as_bezier_curves(self, context, file_path, EmptyParent, 
                                fBranchSeparation,
                                matStem, matBranch, BevelObject):

        print('Importing QSM as Bezier curves.')
        
        # Current scene to read properties.
        scene = context.scene
        
        # Number of branches.
        NBranch = 0
        # Index of last branch.
        iLastBranch = 0

        # Initialize arrays to collect branch cylinder parameters.
        sp = []
        ax = []
        h  = []
        r  = []

        with open(file_path) as lines:
            
            # Count number of lines in file.
            NLine = sum(1 for line in lines)
            
            # Number of digits to use in object naming.
            NDigit = len(str(NLine))
            
            # If file had any rows.
            if NLine > 0:

                # If multiple objects are created, use unique object and mesh names
                # by numbering them.
                if fBranchSeparation:
                    curvename = "branch_" + str(1).zfill(NDigit)
                    objname   = "branch_" + str(1).zfill(NDigit)
                else:
                    curvename = "qsm_curve"
                    objname   = "qsm"

                # Create new curve to hold splines.
                curvedata = bpy.data.curves.new(name=curvename, type='CURVE')
                curvedata.dimensions = '3D'
                # Set bevel object and fill caps.
                curvedata.bevel_object = BevelObject
                curvedata.use_fill_caps = True

                # Add stem material to first object.
                if matStem:
                    curvedata.materials.append(matStem)
                
                # Add branch material to first object if present.
                if matBranch and (matStem != matBranch):
                    curvedata.materials.append(matBranch)

                # Create new object with curve data.
                objectdata = bpy.data.objects.new(objname, curvedata)
                # Set position to origin.
                objectdata.location = (0,0,0)
                # Parent to created empty.
                objectdata.parent = EmptyParent
                # Set selected.
                objectdata.select = True

                # Link to scene.
                scene.objects.link(objectdata)

            # Otherwise the file was empty.
            else:
                self.report({'ERROR_INVALID_INPUT'},'Selected file is empty.')
                return {'CANCELLED'}
            
            # Move back to file beginning.
            lines.seek(0)

            # Last displayed percentage.
            PLast = 0
            
            # Iterate over file rows.
            for iLine, line in enumerate(lines):

                # Split row into parameters.
                params = line.split()

                # Ignore rows with too few parameters.
                if len(params) < 9:
                    continue

                # Print progress in the console every nth row.
                PLast = print_progress(NLine, iLine, 10, PLast)

                # Get cylinder parameters.
                iBranch = int(float(params[0]))

                # On first branch.
                if NBranch < 1:
                    # Set count to one.
                    NBranch = 1
                    # Set last index to first index.
                    iLastBranch = iBranch


                # If new branch begins, complete the last branch.
                if iBranch != iLastBranch:

                    # Add new spline with the cylinder parameter arrays.
                    polyline = self.addBezierCurve(curvedata, sp, ax, h, r)

                    # If the branch index of the branch to complete is one,
                    # assign stem material.
                    if iLastBranch == 1:
                        polyline.material_index = 0
                    # Otherwise, assign last material slot, which is stem
                    # material if its the only material and branch material
                    # if it is present.
                    else:
                        polyline.material_index = len(curvedata.materials)

                    # Update last branch to current value.
                    iLastBranch = iBranch
                    # Increase branch count.
                    ++NBranch

                    # Empty parameter arrays.
                    sp[:] = []
                    ax[:] = []
                    h[:]  = []
                    r[:]  = []

                    # If branches are separated, create new object with a
                    # name based on index.
                    if fBranchSeparation:
                        curvename = "branch_" + str(NBranch).zfill(NDigit)
                        objname   = "branch_" + str(NBranch).zfill(NDigit)

                        # New curve data.
                        curvedata = bpy.data.curves.new(name=curvename, type='CURVE')
                        curvedata.dimensions = '3D'
                        curvedata.bevel_object = BevelObject
                        curvedata.use_fill_caps = True

                        # Add branch material to rest of the objects if present.
                        if matBranch:
                            curvedata.materials.append(matBranch)
                        # Otherwise use stem material if given.
                        elif matStem:
                            curvedata.materials.append(matStem)

                        # New object with curve data.
                        objectdata = bpy.data.objects.new(objname, curvedata)
                        # Position to origin.
                        objectdata.location = (0,0,0)
                        # Parent to empty.
                        objectdata.parent = EmptyParent
                        # Set selected.
                        objectdata.select = True

                        # Link to current scene.
                        scene.objects.link(objectdata)


                # Append cylinder parameters from current file row to parameter
                # arrays.
                sp.append( (float(params[1]), float(params[2]), float(params[3])) )
                ax.append( (float(params[4]), float(params[5]), float(params[6])) )
                h.append( float(params[7]) )
                r.append( float(params[8]) )

            # Complete final branch.
            polyline = self.addBezierCurve(curvedata, sp, ax, h, r)

            # If the branch index of the branch to complete is one,
            # assign stem material.
            if iBranch == 1:
                polyline.material_index = 0
            # Otherwise, assign last material slot, which is stem
            # material if its the only material and branch material
            # if it is present.
            else:
                polyline.material_index = len(curvedata.materials)


    # Main function of the QSM import operator. 
    def execute(self,context):

        # Record start time to compute duration.
        start = datetime.datetime.now()

        # Current scene for properties.
        scene = context.scene

        # Path to input file.
        filestr = scene.qsm_file_path

        # Check for empty filepath.
        if len(filestr) == 0:
            self.report({'ERROR_INVALID_INPUT'},'Missing input file path.')
            print('Cancelled.')
            return {'CANCELLED'}

        # Convert to absolute path.
        file_path = bpy.path.abspath(filestr)

        # Check that file exists.
        if not os.path.isfile(file_path):
            self.report({'ERROR_INVALID_INPUT'},'No file with given path.')
            print('Cancelled.')
            return {'CANCELLED'}

        # Import mode: mesh / bezier
        mode = scene.qsmImportMode
        # Flag: separate objects for each branch.
        fBranchSeparation = scene.qsmSeparation

        # Create empty parent for QSM object(s).
        EmptyParent = self.createQSMParent(scene)

        # If curve-based mode, check that bevel object is given and
        # exists.
        if mode == 'bezier_cylinder' or mode == 'bezier_branch':

            if scene.qsmGenerateBevelObject:

                # Get bevel object by name. This object is set as the bevel object
                # of all the Bezier curves.
                bpy.ops.curve.primitive_bezier_circle_add(radius=1,
                                                          view_align=False, 
                                                          enter_editmode=False, 
                                                          location=(0, 0, 0))

                # Selected object is the added curve.
                BevelObject = context.selected_objects[0]

                # Bevel object name.
                BevelObject.name = 'BevelObject'
                BevelObject.parent = EmptyParent
                BevelObject.data.resolution_u = 5
            else:
                # Bevel object name.
                bevel_object_name = scene['qsmBevelObject']
                # Get bevel object by name. This object is set as the bevel object
                # of all the Bezier curves.
                BevelObject = bpy.data.objects.get(bevel_object_name)

                # Check that bevel object exists.
                if not BevelObject:
                    self.report({'ERROR_INVALID_INPUT'},'Missing bevel object.')
                    print('Cancelled.')
                    return {'CANCELLED'}

                # Check that the object is a curve object.
                if BevelObject.type != 'CURVE':
                    self.report({'ERROR_INVALID_INPUT'},'Bevel object has to be a curve.')
                    print('Cancelled.')
                    return {'CANCELLED'}

        # Get stem material name.
        matname = scene.qsmStemMaterial

        # Check that values is not empty.
        if len(matname) == 0:
            # Warn that no material set.
            print('No stem material set.')
            matStem = None
        else:
            # Try to get material with given name.
            matStem = bpy.data.materials.get(matname)

            # Warn if not found.
            if not matStem:
                print('Stem material not found.')

        # Get branch material name.
        matname = scene.qsmBranchMaterial

        # Check that values is not empty.
        if len(matname) == 0:
            print('No branch material set.')
            matBranch = None
        else:
            # Try to get material with given name.
            matBranch = bpy.data.materials.get(matname)

            # Warn if not found.
            if not matBranch:
                print('Branch material not found.')

        # Mesh cylinder.
        if mode == 'mesh_cylinder':
            self.import_as_mesh_cylinders(context, file_path, EmptyParent, 
                                          fBranchSeparation,
                                          matStem, matBranch)
        # Cylinder-level Bezier curves.
        elif mode == 'bezier_cylinder':
            self.import_as_bezier_cylinders(context, file_path, EmptyParent, 
                                            fBranchSeparation,
                                            matStem, matBranch, BevelObject)
        # Branch-level Bezier curves.
        elif mode == 'bezier_branch':
            self.import_as_bezier_curves(context, file_path, EmptyParent, 
                                         fBranchSeparation,
                                         matStem, matBranch, BevelObject)

        # Record end time.
        end = datetime.datetime.now()
        # Compute duration.
        delta = end - start
        # Format duration as string.
        timestr = "{:.1f}".format(delta.total_seconds())

        # Display import duration in the console.
        sys.stdout.write("Processing finished in " + timestr + " sec" + " "*100+"\n")
        sys.stdout.flush()

        return {'FINISHED'}


# Operator for updating the colourmap information of a mesh based QSM object,
# without re-importing the geometry.
class UpdateMeshQSMColorMap(bpy.types.Operator):
    """Read colourmap values from file and update selected mesh object vertex colors"""

    bl_idname = "qsm.update_colourmap"
    bl_label = "Update colourmap"

    # Main function of the colourmap update operator.
    def execute(self,context):

        print('Importing QSM as Bezier cylinders.')

        # Record start time to compute duration.
        start = datetime.datetime.now()
        
        # Current scene for properties.
        scene = context.scene

        # Object to update should be selected.
        ob = bpy.context.selected_objects[0]

        # If no selection or selected object is not a mesh.
        if not ob:
            self.report({'ERROR_INVALID_INPUT'},'No object selected.')
            return {'CANCELLED'}
        elif ob.type != 'MESH':
            self.report({'ERROR_INVALID_INPUT'},'Selected object is not a mesh.')
            return {'CANCELLED'}

        # Path to input file.
        file_path = bpy.path.abspath(scene['qsm_file_path'])

        # Check that file exists.
        if not os.path.isfile(file_path):
            self.report({'ERROR_INVALID_INPUT'},'No file with given path.')
            print('Cancelled.')
            return {'CANCELLED'}

        # Mesh data of selected object.
        me = ob.data
        # Create bmesh object for data modification.
        bm = bmesh.new()
        bm.from_mesh(me)

        # Get integer layer that contains cylinder ID information,
        # crucial for updating.
        layer = bm.verts.layers.int.get("CylinderId")

        # If layer does not exist, unable to update.
        if not layer:
            self.report({'ERROR_INVALID_INPUT'},'Selected object does not contain cylinder id info.')
            return {'CANCELLED'}

        with open(file_path) as lines:
            
            # Count number of lines in file.
            NLine = sum(1 for line in lines)
            
            # Number of digits to use in object naming.
            NDigit = len(str(NLine))
            
            # Return to file beginning.
            lines.seek(0)

            # (Vector) array to hold colourmap values of each cylinder.
            CylinderColors = []
            
            # Iterate over file rows.
            for iLine, line in enumerate(lines):

                # Split cylinder parameter on current row.
                params = line.split()

                # Ignore rows with too few parameters.
                if len(params) < 9:
                    continue
        
                # Display progress every 100th row.
                if iLine == 0 or iLine%100 == 1:
                    msg = "Processing line %i of %i" % (iLine+1, NLine)
                    sys.stdout.write(msg + chr(8) * len(msg))
                    sys.stdout.flush()

                # Append new colourmap value to array.
                if len(params) > 11:
                    CylinderColors.append(Vector((float(params[9]), float(params[10]), float(params[11]))))
                else:
                    CylinderColors.append(float(params[9]))

            # Get colour layer that holds colourmap data.
            colors = bm.loops.layers.color.get("Color")
            # If layer does not exist, create new.
            if not colors:
                colors = bm.loops.layers.color.new("Color")
            
            # Iterate over vertices in mesh.
            for v in bm.verts:

                # Cylinder index is read from CylinderId layer.
                iCyl = v[layer]

                # Update colour layer with new colour value.
                for loop in v.link_loops:
                    if len(CylinderColors[iCyl-1]) > 1:
                        loop[colors] = CylinderColors[iCyl-1]
                    else:
                        loop[colors] = [CylinderColors[iCyl-1]] * 3

        # Update mesh data.
        bm.to_mesh(me)
        # Free bmesh.
        bm.free()

        # Record end time.
        end = datetime.datetime.now()
        # Compute duration.
        delta = end - start
        # Format duration as string.
        timestr = "{:.1f}".format(delta.total_seconds())

        # Display import duration in the console.
        sys.stdout.write("Processing finished in " + timestr + " sec" + " "*len(msg)+"\n")
        sys.stdout.flush()

        return {'FINISHED'}


def min_update(self, context):
    mi = context.scene.qsmVertexCountMin
    ma = context.scene.qsmVertexCountMax

    if mi > ma:
        context.scene.qsmVertexCountMax = mi

def max_update(self, context):
    mi = context.scene.qsmVertexCountMin
    ma = context.scene.qsmVertexCountMax

    if mi > ma:
        context.scene.qsmVertexCountMin = ma

def register():

    # QSM import modes for UI selector.
    qsm_import_modes = [
        ("mesh_cylinder",   "Mesh cylinder",   "Cylinder-level mesh elements"),
        ("bezier_cylinder", "Bezier cylinder", "Cylinder-level Bezier curves"),
        ("bezier_branch",   "Bezier branch",   "Branch-level Bezier curves"),
    ]

    # Import mode variable.
    bpy.types.Scene.qsmImportMode = bpy.props.EnumProperty \
      (
      name="QSM Import Mode",
      description="Import mode determines the resulting object type",
      items=qsm_import_modes
      )

    # Flag: add new bezier circle as bevel object
    bpy.types.Scene.qsmGenerateBevelObject = bpy.props.BoolProperty \
      (
      name = "Create bevel object",
      description = "If checked, a new object will be created as the bevel object of all branches.",
      default = True,
      subtype = 'NONE',
      )

    # Bevel object for curve based modes.
    bpy.types.Scene.qsmBevelObject = bpy.props.StringProperty \
      (
      name="Bevel Object",
      description="Object that is asigned as the bevel object of each curve",
      )

    # Name of the stem material.
    bpy.types.Scene.qsmStemMaterial = bpy.props.StringProperty \
      (
      name="Stem material",
      description="Material to apply to stem after import"
      )

    # Name of the branch material.
    bpy.types.Scene.qsmBranchMaterial = bpy.props.StringProperty \
      (
      name="Branch material",
      description="Material to apply to branches after import"
      )

    # Flag: separate object for each branch.
    bpy.types.Scene.qsmSeparation = bpy.props.BoolProperty \
      (
      name = "Branch separation",
      description = "If enabled each branch results in a separate object.",
      default = False,
      subtype = 'NONE',
      )

    # Path to input file with cylinder parameters.
    bpy.types.Scene.qsm_file_path = bpy.props.StringProperty \
      (
      name = "Input file",
      default = "",
      description = "TXT-file containing the cylinder parameters",
      subtype = 'FILE_PATH'
      )

    # Path to input file with leaf model parameters.
    bpy.types.Scene.leaf_model_file_path = bpy.props.StringProperty \
      (
      name = "Input file",
      default = "",
      description = "TXT-file containing the leaf parameters",
      subtype = 'FILE_PATH'
      )

    # Name of the leaf material.
    bpy.types.Scene.leafModelMaterial = bpy.props.StringProperty \
      (
      name="Material",
      description="Material to apply to object(s) after import"
      )

    # Leaf model vertex count.
    bpy.types.Scene.leaf_model_vertex_count = bpy.props.IntProperty \
      (
      name = "Vertex count",
      default = 4,
      min = 3,
      max = 4,
      description = "Number of vertices in a single leaf",
      subtype = 'UNSIGNED'
      )

    # Minimum cylinder ring vertex count.
    bpy.types.Scene.qsmVertexCountMin = bpy.props.IntProperty \
      (
      name = "Vertex count minimum",
      default = 16,
      min = 3,
      max = 50,
      subtype = 'NONE',
      description = "Minimum number of vertices in mesh cylinders",
      update = min_update
      )

    # Minimum and maximum cylinder ring vertex count.
    bpy.types.Scene.qsmVertexCountMax = bpy.props.IntProperty \
      (
      name = "Vertex count maximum",
      default = 16,
      min = 3,
      max = 50,
      subtype = 'NONE',
      description = "Maximum number of vertices in mesh cylinders",
      update = max_update
      )

    # Leaf UV

    # Flag: generate UV map for leaves.
    bpy.types.Scene.leafUvGeneration = bpy.props.BoolProperty \
      (
      name = "Generate UV map",
      description = "Generate UV map for imported leaves.",
      default = False,
      subtype = 'NONE',
      )

    # Array for leaf UV map presents and custom option.
    leaf_uv_modes = [
        ("isosceles_triangle",   "Isosceles triangle",   "Isosceles triangle"),
        ("square",   "Unit square",   "Unit square"),
        ("custom",   "Custom",   "Custom vertices from object"),
    ]

    # Dropdown: UV map types.
    bpy.types.Scene.leafUvType = bpy.props.EnumProperty \
      (
      name="UV map type",
      description="Leaf UV map type",
      items=leaf_uv_modes
      )

    # Mesh to base UV map on.
    bpy.types.Scene.leafUvSource = bpy.props.StringProperty \
      (
      name="UV mesh data",
      description="Object to base the generated UV map on.",
      )

    # Register classes.

    # Update colourmap operator.
    bpy.utils.register_class(UpdateMeshQSMColorMap)
    # QSM import operator.
    bpy.utils.register_class(ImportQSM)
    # Leaf import operator.
    bpy.utils.register_class(ImportLeafModel)
    # QSM panel
    bpy.utils.register_class(QSMPanel)
    # Leaf panel.
    bpy.utils.register_class(LeafModelPanel)







def unregister():
    # Delete custom properties from scene.
    del bpy.types.Scene.qsmImportMode
    del bpy.types.Scene.qsmBevelObject
    del bpy.types.Scene.qsmStemMaterial
    del bpy.types.Scene.qsmBranchMaterial
    del bpy.types.Scene.qsm_file_path
    del bpy.types.Scene.qsmSeparation
    del bpy.types.Scene.leaf_model_file_path
    del bpy.types.Scene.leafModelMaterial
    del bpy.types.Scene.leaf_model_vertex_count
    del bpy.types.Scene.qsmVertexCountMin
    del bpy.types.Scene.qsmVertexCountMax
    del bpy.types.Scene.qsmGenerateBevelObject
    del bpy.types.Scene.leafUvType
    del bpy.types.Scene.leafUvGeneration
    del bpy.types.Scene.leafUvSource

    # Unregister classes.
    bpy.utils.unregister_class(LeafModelPanel)
    bpy.utils.unregister_class(QSMPanel)
    bpy.utils.unregister_class(ImportQSM)
    bpy.utils.unregister_class(UpdateMeshQSMColorMap)
    bpy.utils.unregister_class(ImportLeafModel)






if __name__ == "__main__":
    register()
