import sys
from math import copysign
import bpy
import bgl
import blf
import bmesh
from mathutils import Vector, Matrix
from collections import defaultdict

# from sverchok.utils import sv_bmesh_utils

from .bmesh_utils import (
    pydata_from_bmesh,
    bmesh_from_pydata
)


def new_obj(bm, named_object, named_mesh, force_reuse=True):
    meshes = bpy.data.meshes
    scene = bpy.context.scene
    objects = bpy.data.objects

    if named_mesh in meshes:
        me = meshes.get(named_mesh)
    else:
        me = meshes.new(named_mesh)

    bm.to_mesh(me)
    bm.free()

    if named_object in objects:
        obj = objects[named_object]
        obj.data = me
    else:
        obj = objects.new(named_object, me)
        scene.objects.link(obj)

    return obj


def generate_draw_geometry(caller, context):
    bm = bmesh.new()

    obj = bpy.context.active_object
    me = obj.data
    me.update()
    bm.from_mesh(me)

    original_face = bm.faces.active
    verts = [v.co.copy() for v in original_face.verts]
    face_normal = original_face.normal.copy()
    bm.free()
    del bm
    return verts, face_normal, obj.matrix_world.copy()


def generate_boolean_geom(verts, normal, scalar):
    scn = bpy.context.scene

    bm = bmesh.new()
    final_verts = []
    num_verts = len(verts)
    faces = []
    face1 = []
    face2 = []
    ftwix = []
    for idx, v in enumerate(verts):

        #  bool(0.0) == False,  bool(0.00001) == True
        if bool(scn.BGL_FUDGE_FACTOR):
            # this pushes the start face a little back, to allow numeric issues with
            # the face being ontop of the face to remove from. some fudging seems necessary..
            fudge_vert = v + (-normal * copysign(scn.BGL_FUDGE_FACTOR, scalar))
            final_verts.append(fudge_vert)
        else:
            final_verts.append(v)
        face1.append(idx)
    for idx, v in enumerate(verts, num_verts):
        final_verts.append(v + (normal * scalar))
        face2.append(idx)
    for idx, _ in enumerate(verts):
        idx_1 = idx
        idx_2 = (idx + 1) % num_verts
        idx_3 = ((idx + 1) % num_verts) + num_verts
        idx_4 = idx + num_verts
        ftwix.append([idx_1, idx_2, idx_3, idx_4])
    faces.append(face1)
    faces.append(face2)
    faces.extend(ftwix)
    return final_verts, faces


def attache_boolean_modifier(obj_a, obj_b):
    if obj_a and obj_a.type == 'MESH':
        # if modifier present, remove
        if 'sv_bool' in obj_a.modifiers:
            sk = obj_a.modifiers['sv_bool']
            obj_a.modifiers.remove(sk)

        a = obj_a.modifiers.new(type='BOOLEAN', name='sv_bool')
        a.operation = 'INTERSECT'
        if obj_b:
            a.object = obj_b


def draw_callback_px(self, context, res):

    verts, fnorm, fmatrix = res
    scn = context.scene
    scalar = scn.BGL_OFFSET_SCALAR

    # 50% alpha, 2 pixel width line
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(context.scene.BGL_DEMO_PROP_THICKNESS)
    bgl.glColor4f(0.8, 0.3, 0.9, 1.0)
    bgl.glBegin(bgl.GL_LINE_LOOP)
    for vert in verts:
        co = fmatrix * (vert + (fnorm * scalar))
        bgl.glVertex3f(*co)

    bgl.glEnd()

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


class ModalDrawOperator(bpy.types.Operator):

    bl_idname = "view3d.bgl_demo_modal_operator"
    bl_label = "Simple Modal View3D Operator"

    def modal(self, context, event):
        context.area.tag_redraw()
        scn = context.scene

        if event.type in {'MIDDLEMOUSE'}:
            return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        if event.type in {'RET'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.modifier_apply(apply_as='DATA', modifier="sv_bool")
            context.active_object.show_wire = False
            context.active_object.show_all_edges = False
            bpy.ops.object.mode_set(mode='EDIT')
            return {'FINISHED'}

        scalar = scn.BGL_OFFSET_SCALAR
        VB, PB = generate_boolean_geom(self.verts, self.normal, scalar)

        bm = bmesh_from_pydata(VB, [], PB)
        n_obj = new_obj(bm, "ExtractObject", "Extract_mesh")
        n_obj.hide = True

        obj = bpy.context.active_object
        attache_boolean_modifier(obj, n_obj)

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':

            bpy.ops.object.mode_set(mode='OBJECT')

            scn = context.scene
            scn.BGL_OFFSET_SCALAR = -0.001
            scn.BGL_DEMO_PROP_THICKNESS = 5
            scn.BGL_FUDGE_FACTOR = True

            res = generate_draw_geometry(self, context)
            self.verts = res[0]
            self.normal = res[1]
            self.scalar = res[2]

            args = (self, context, res)

            draw_handler_add = bpy.types.SpaceView3D.draw_handler_add
            self._handle = draw_handler_add(
                draw_callback_px, args, 'WINDOW', 'POST_VIEW')

            context.active_object.show_wire = True
            context.active_object.show_all_edges = True
            context.window_manager.modal_handler_add(self)

            obj = bpy.context.active_object
            attache_boolean_modifier(obj, None)

            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


class HelloWorldPanel(bpy.types.Panel):

    """Creates a Panel in the Object properties window"""
    bl_label = "Hello World Panel"
    bl_idname = "OBJECT_PT_hello"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_context = "object"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(context.scene, 'BGL_DEMO_PROP_THICKNESS', text='thickness')
        col.prop(context.scene, 'BGL_OFFSET_SCALAR', text='amount')
        col.prop(context.scene, 'BGL_FUDGE_FACTOR', text='fudge')
        col.operator("view3d.bgl_demo_modal_operator")
