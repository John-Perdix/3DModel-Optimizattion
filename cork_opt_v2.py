import bpy
import sys
import os
import math
import pathlib
import time

start_time = time.time()


# Initial arguments
input_path = "D:\\develop\\maxim-corky\\SourceCode\\CorkPython\\blender_to_low_poly\\input\\2.gltf"

images_output_path = "D:\\develop\\maxim-corky\\SourceCode\\CorkPython\\blender_to_low_poly\\output\\"
#images_output_path = "C:\\Users\\TLEAL\\Desktop\\blend\\output\\"

cork_name = "2"

texture_size = 2048


# Workflow options
resolution = texture_size

# Remesh options: 'VOXEL', 'QUAD', 'DECIMATE', 'NONE'
remesher = 'DECIMATE'
remesh_percent = 5  # For DECIMATE, percentage of reduction (e.g., 1.0 means 1%)

RECALCULATE_LOW_POLY_NORMALS = True

LOW_POLY_UV_ISLAND_MARGIN = 0 # island_margin=0.05

# UV Unwrap options: 'SMART', 'NONE'
samples = 128
uv_unwrap_method = 'SMART'
scene = bpy.data.scenes["Scene"]  # replace "Scene" with your scene name if different
scene.render.engine = "CYCLES"
scene.cycles.device = 'GPU'
scene.cycles.samples = samples


# Bake options
bake_method = 'TRANSFER'  # 'TRANSFER', 'ACTIVE', 'NONE'
cage_settings = 'MANUAL'    # 'AUTO', 'MANUAL'
extrusion = 0.02           # Used if cage_settings is 'MANUAL'
ray_distance = 0.03     # Used if cage_settings is 'MANUAL'
is_normal_bake_on = True
is_diffuse_bake_on = True


def apply_modifiers(obj):
    ctx = bpy.context.copy()
    ctx['object'] = obj
    for _, m in enumerate(obj.modifiers):
        try:
            ctx['modifier'] = m
            bpy.ops.object.modifier_apply(modifier=m.name)
        except RuntimeError:
            print(f"Error applying {m.name} to {obj.name}, removing it instead.")
            obj.modifiers.remove(m)

    for m in obj.modifiers:
        obj.modifiers.remove(m)
        
""" # Modified apply_modifiers function to handle exceptions and remove unsupported modifiers
def apply_modifiers(obj):
    # Make a copy of the modifier list because we'll modify it during iteration
    modifiers = list(obj.modifiers)
    
    for m in modifiers:
        try:
            # Only support modifiers that can be applied on mesh data
            if obj.type == 'MESH':
                # Apply the modifier directly to the mesh
                mesh = obj.data
                depsgraph = bpy.context.evaluated_depsgraph_get()
                obj_eval = obj.evaluated_get(depsgraph)
                mesh_from_mod = obj_eval.to_mesh()
                
                obj.data = mesh_from_mod
                
                # Remove the modifier after applying
                obj.modifiers.remove(m)
                
        except Exception as e:
            print(f"Error applying {m.name} to {obj.name}, removing it instead: {e}")
            obj.modifiers.remove(m) """

    
def recalculate_normals(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.editmode_toggle()



# utility functions
def calc_avg_voxel_size(obj):
    obj_mesh = obj.data
    obj_vertices = obj_mesh.vertices
    obj_edges = obj_mesh.edges

    edge_count = len(obj_edges)
    edge_sum = 0.0

    # how many edges will be used to calculate average
    accuracy_count = samples

    for interval in range(accuracy_count):
        # get edge number at spaced out intervals for better estimation
        edge_number = int(edge_count * interval / accuracy_count)
        # get vertex numbers of chosen edge
        vert1 = obj_edges[edge_number].vertices[0]
        vert2 = obj_edges[edge_number].vertices[1]
        # calculate distance between vertices to get edge length
        edge_sum += math.dist(obj_vertices[vert1].co, obj_vertices[vert2].co)

    # calculate average
    avg_voxel_size = edge_sum / accuracy_count

    return avg_voxel_size


def new_node(nodes, location, name="ShaderNodeTexImage", image=None):
    node = nodes.new(type=name)
    node.location = location
    if image is not None:
        node.image = image
    node.select = False
    return node


def new_image(name: str, non_color=False, use_float=False):
    image = bpy.data.images.new(
        name=name,
        width=int(resolution),
        height=int(resolution),
        float_buffer=use_float,
    )
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    else:
        image.colorspace_settings.name = "sRGB"  # Ensure baked colors are in sRGB
    return image


def save_image(image):
    path = images_output_path
    if path == ".\\Autolow\\":
        # save images in 'AutoLow' folder
        path = pathlib.Path(bpy.path.abspath("//") + "AutoLow")
        path.mkdir(exist_ok=True)
        path = str(path)

    #image.filepath = os.path.join(path, image.name + ".png")
    image.filepath_raw = path + "\\" + image.name + ".png"
    image.file_format = "PNG"
    image.save()

    
def make_cage(lowpoly, cage_extrusion=extrusion):
    # Copy low-poly mesh to create the cage
    cage = copy_obj(lowpoly)
    cage.name = "cage"
    recalculate_normals(cage)
    set_active(cage)
    
    # Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Select all vertices
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Move vertices along their normals
    bpy.ops.transform.shrink_fatten(value=cage_extrusion)
    
    # Exit Edit Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Deselect the cage
    cage.select_set(False)
    
    return cage


def bake(bake_type, highpoly, lowpoly):
    # check if multires normal baking should be done
    is_bake_multires = remesher != "NONE" and bake_type == "NORMAL"

    # select objects for baking
    if bake_method == "TRANSFER" and not is_bake_multires:
        highpoly.select_set(True)
    set_active(lowpoly)

    # bake
    if is_bake_multires:
           
        print("Baking normal map from high-poly to low-poly...")
        bpy.ops.object.select_all(action='DESELECT')
        highpoly.select_set(True)
        lowpoly.select_set(True)
        bpy.context.view_layer.objects.active = lowpoly
        bpy.ops.object.bake(
            type='NORMAL',
            #use_selected_to_active=True,
            #use_clear=True,
            normal_space='TANGENT',
                            margin=16  # Increased margin to avoid texture bleed
        )
    else:
        # regular bake
        bpy.ops.object.bake(
            type=bake_type,
            pass_filter={'COLOR'},  # Make sure we're only baking color
            use_clear=True,
            margin=2  # Increased margin to avoid texture bleed
        )


def copy_obj(object):
    new = object.copy()
    # copy data so new obj is not an instance
    new.data = object.data.copy()
    new.animation_data_clear()
    bpy.context.collection.objects.link(new)
    deselect_all()
    set_active(new)
    return new


def deselect_all():
    for obj in bpy.context.selected_objects:
        obj.select_set(False)


def set_active(object):
    object.select_set(True)
    bpy.context.view_layer.objects.active = object
    
    
def remesh_process(lowpoly):
    if remesher == "VOXEL":
        # voxel remesh
        avg_voxel_size = calc_avg_voxel_size(lowpoly)
        lowpoly.data.remesh_voxel_size = avg_voxel_size * (100 / remesh_percent)
        bpy.ops.object.voxel_remesh()

    elif remesher == "QUAD":
        # quad remesh
        lowpoly_mesh = lowpoly.data
        lowpoly_vertices = lowpoly_mesh.vertices
        lowpoly_facecount = len(lowpoly_mesh.polygons)
        lowpoly_target_faces = int(lowpoly_facecount * (remesh_percent / 100))
        vertex_count = len(lowpoly_vertices)

        bpy.ops.object.quadriflow_remesh(target_faces=lowpoly_target_faces)

        # if the vertex count is the same after remeshing, the remesh probably failed
        # it's likely that the reason is that the mesh isn't manifold
        if len(lowpoly_vertices) == vertex_count:
            # voxel remesh to make mesh manifold
            lowpoly.data.remesh_voxel_size = calc_avg_voxel_size(lowpoly)
            bpy.ops.object.voxel_remesh()
            bpy.ops.object.quadriflow_remesh(target_faces=lowpoly_target_faces)

    elif remesher == "DECIMATE":
        # decimate
        decimate = lowpoly.modifiers.new("Autolow_Decimate", "DECIMATE")
        decimate.ratio = remesh_percent / 100
        bpy.ops.object.modifier_apply(modifier=decimate.name)


def uv_unwrap_process():
    method = uv_unwrap_method
    if method == "SMART":
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=20, area_weight=0, island_margin=LOW_POLY_UV_ISLAND_MARGIN, correct_aspect=True, scale_to_bounds=True)
        bpy.ops.object.editmode_toggle()


def bake_process(highpoly, lowpoly, c_name):
    method = bake_method
    if method != "NONE":
        # make new material
        material = bpy.data.materials.new(name="Skynetdev_Cork_Material")
        lowpoly.active_material = material
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        principled = nodes.get("Principled BSDF")
        principled.select = False
        output = nodes.get("Material Output")
        output.select = False
        
        # Adjust material properties for cork appearance
        principled.inputs['Metallic'].default_value = 0.0  # Cork is not metallic
        principled.inputs['Roughness'].default_value = 0.8  # Cork is quite rough

        # bake settings
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True  # Add this line

        if method == "TRANSFER":
            bpy.context.scene.render.bake.use_selected_to_active = True
        else:
            bpy.context.scene.render.bake.use_selected_to_active = False

        # make cage
        if cage_settings == "MANUAL":
            cage = make_cage(lowpoly)
            bpy.context.scene.render.bake.use_cage = False  #added to not use the built in cage setting
            bpy.context.scene.render.bake.max_ray_distance = ray_distance #new line for ray distance

        else:
            #Use of the auto cage from blender (Does not work well)
            bpy.context.scene.render.bake.use_cage = True
            #bpy.context.scene.render.bake.cage_extrusion = extrusion
            bpy.context.scene.render.bake.max_ray_distance = ray_distance

        # normals
        if is_normal_bake_on:
            # setup nodes
            normal_image = new_image(c_name+"_normal", non_color=True, use_float=False)
            normal_texture = new_node(nodes, (-500, -150), image=normal_image)
            normal_map = new_node(nodes, (-200, -175), "ShaderNodeNormalMap")
            links.new(normal_texture.outputs[0], normal_map.inputs[1])
            links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
            nodes.active = normal_texture

            # bake normals
            bake("NORMAL", highpoly, cage)
            #save_image(normal_image)(No need to save the images because of the glb format)

        # diffuse
        if is_diffuse_bake_on:
            # setup nodes
            diffuse_image = new_image(c_name+"_diffuse")
            diffuse_texture = new_node(nodes, (-500, 300), image=diffuse_image)
            links.new(diffuse_texture.outputs[0], principled.inputs[0])
            nodes.active = diffuse_texture

            # bake diffuse
            bake("DIFFUSE", highpoly, cage)
            #save_image(diffuse_image)(No need to save the images because of the glb format)

        # remove cage
        if cage_settings == "MANUAL":
            bpy.data.objects.remove(cage, do_unlink=True)

    

# Function to clean up the high-poly mesh
def clean_high_poly_mesh(obj):
    bpy.context.view_layer.objects.active = obj

    # Ensure the object is in Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')

    # Select all vertices
    bpy.ops.mesh.select_all(action='SELECT')

    # Remove doubles (Merge by Distance)
    bpy.ops.mesh.remove_doubles(threshold=0.0001)  # Adjust threshold as needed

    # Fill Holes
    bpy.ops.mesh.fill_holes(sides=4)  # Max sides for hole filling

    # Delete Loose Geometry
    bpy.ops.mesh.delete_loose()

    # Dissolve Degenerate Geometry
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)  # Adjust threshold as needed

    # Return to Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    

def delete_all_objects():
    # Make a copy of the objects list because we'll remove items while iterating
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

def main():
    global resolution, texture_size, input_path, images_output_path, output_path
    # Parse command-line arguments
    import argparse

    parser = argparse.ArgumentParser(description='Automate mesh simplification and texture baking.')
    parser.add_argument('--input', required=True, help='Path to the input high-poly glTF model.')
    parser.add_argument('--output', required=True, help='Path to the output folder for the low-poly glTF model.')
    parser.add_argument('--texture-size', type=int, default=2048, help='Size of the baked texture (e.g., 2048 for 2048x2048).')
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    
    

    # Resolve paths to absolute paths
    input_path = os.path.abspath(bpy.path.abspath(args.input))
    images_output_path = os.path.abspath(bpy.path.abspath(args.output))
    texture_size = args.texture_size
    # Workflow options
    resolution = texture_size
    
    cork_name = pathlib.Path(input_path).stem
    
    
    print("input_path = ", input_path)
    print("images_output_path = ", images_output_path)
    print("texture_size = ", texture_size)
    print("cork_name = ", cork_name)
    
    output_path = os.path.join(images_output_path, cork_name+'.gltf')
    print("output_path = ", output_path)
    

    # Ensure output directories exist
    os.makedirs(os.path.dirname(images_output_path), exist_ok=True)
    
    
    # **Set scene color management to 'Standard'**
    bpy.context.scene.view_settings.view_transform = 'Standard'

    # Example usage:
    delete_all_objects()

    # Import high-poly glTF model
    bpy.ops.import_scene.gltf(filepath=input_path)
    

    # Get the high-poly mesh
    high_poly_objs = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    if not high_poly_objs:
        print("No mesh found in the imported glTF file.")
        sys.exit()

    high_poly = high_poly_objs[0]
    #high_poly.name = "HighPoly"
        
    
    highpoly = high_poly
    
    #for highpoly in objects:
    highpoly.hide_set(False)
    lowpoly = copy_obj(highpoly)
    original_name = lowpoly.name
    lowpoly.name = cork_name +"_LowPoly"


    remesh_process(lowpoly) #Remesh/Decimate the lowpoly
    if len(lowpoly.data.polygons) == 0:
        print("ERROR: The mesh has 0 polygons after remeshing")
        sys.exit(1)
    
    if RECALCULATE_LOW_POLY_NORMALS:
        # *** Add Weighted Normal Modifier to improve normals ***
        # Set lowpoly as active object
        bpy.context.view_layer.objects.active = lowpoly

        # Add the Weighted Normal Modifier
        weighted_normal_modifier = lowpoly.modifiers.new(name='WeightedNormal', type='WEIGHTED_NORMAL')

        # Set properties (adjust as needed)
        weighted_normal_modifier.keep_sharp = False  # Set to True if you want to keep sharp edges
        weighted_normal_modifier.weight = 50  # Default value, adjust between 1-100
        weighted_normal_modifier.mode = 'FACE_AREA'  # Options: 'FACE_AREA', 'FACE_AREA_WITH_ANGLE', 'CORNER_ANGLE'
        #weighted_normal_modifier.use_face_influence = True

        # Apply the Weighted Normal modifier
        bpy.ops.object.modifier_apply(modifier=weighted_normal_modifier.name)
        
    
    
    uv_unwrap_process()
    bake_process(highpoly, lowpoly, cork_name)

    highpoly.hide_set(True)

    #Test check for modifiers in the object

    

    #Remove modifiers from the object
    lowpoly.modifiers.clear()
    
    # Select only low-poly for export
    bpy.ops.object.select_all(action='DESELECT')
    lowpoly.select_set(True)
    bpy.context.view_layer.objects.active = lowpoly

    # Export only selected (low-poly) mesh
    print("Exporting low-poly model...")
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        use_selection=True,
        export_materials='EXPORT',
        export_format='GLB',
        export_image_format='AUTO',
        export_texture_dir=os.path.dirname(output_path),
        check_existing=False
    )


    # Export the low-poly mesh
    #export_low_poly_mesh(low_poly, output_path)

    # Clean up high-poly mesh if desired
    #bpy.data.objects.remove(high_poly, do_unlink=True)

    # Print completion message
    print("Processing complete. Low-poly mesh exported to:", output_path)


if __name__ == "__main__":
    main()

end_time = time.time()  # record end

elapsed_time = end_time - start_time
print(f"Elapsed time: {elapsed_time:.2f} seconds")