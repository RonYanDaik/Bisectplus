# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Bisect plus",
    "author": "Patrick Busch",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bisect plus",
    "description": "Bisect plus object selection for the cutting plane",
    "warning": "",
    "wiki_url": "https://github.com/Xylvier/Bisectplus/wiki",
    "category": "All",
}

import bpy
import bmesh
import mathutils.geometry

from bpy.props import (
        PointerProperty,
        StringProperty,
        FloatProperty,
        BoolProperty,
        IntProperty,
        )

from bpy.types import (
        Operator,
        Panel,
        PropertyGroup,
        )

#from Scientific.Geometry import Vector

def dump(obj):
    for attr in dir(obj):
        if hasattr(obj, attr):
            print("obj.%s = %r" % (attr, getattr(obj, attr)))  
         
def GetArrayModifiers(_obj):
    arrModifiers = []
    allModifiers = _obj.modifiers
    for mod in allModifiers:
        if(mod.name.startswith("Array")):
            arrModifiers.append(mod)
    return arrModifiers
   
#OPERATOR class
class bisectplus(Operator):
    bl_idname = 'mesh.bisectplus'
    bl_label = 'Bisect Plus'
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        objs = context.selected_objects
        return objs != [] and objs[0].type == "MESH"
    
    #@classmethod
    def doBisect(self, context, inObj, offset):
        
        objectselection_props = context.window_manager.objectselection_props
        obj = inObj
        bpy.context.view_layer.objects.active = obj
        obj.vertex_groups.clear()
        #go in EDIT MODE to see the results as it's a mesh operation
        #print("A")
        cpobj = objectselection_props.cuttingplane

        #only accept mesh
        if cpobj.type != 'MESH':
            print("Not Mesh")
            return
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        bm = bmesh.new()
        bm.from_mesh(cpobj.data)

        bm.faces.ensure_lookup_table()
        bm.faces[0].select = True
        
        if len(bm.faces) > 1:
            print("Too many FACES!")
            return

        bm.verts.ensure_lookup_table()
        v1 = cpobj.matrix_world @ bm.verts[0].co
        v2 = cpobj.matrix_world @ bm.verts[1].co
        v3 = cpobj.matrix_world @ bm.verts[2].co
        v4 = cpobj.matrix_world @ bm.verts[3].co

        nv2 = v4 - v3
        nv3 = v3 - v2
        vn = nv2.cross(nv3)
        vn.normalize()
        #dump(vn)
        face = bm.faces[0]

        origin =  cpobj.matrix_world @ face.calc_center_median()
        normal = vn
        
        #print("normal = \t\t%s" % normal)
        #print("origin = \t\t%s" % origin)
        origin+=normal*offset;
        #print("origin offset = \t\t%s" % origin)
        #keep the manual selection saved in a vertex group
        if objectselection_props.rememberselection:
            obj.vertex_groups.new(name="prebisectselection")
            bpy.ops.object.vertex_group_assign()
        
        #only works in Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')
        if objectselection_props.selectionoverride:
            #all vertices need to be selected
            for v in obj.data.vertices:
                v.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        
        #return
        #call bisect with the selected plane
        bpy.ops.mesh.bisect(
            plane_co = origin,
            plane_no = normal,
            use_fill = objectselection_props.fill,
            clear_inner = objectselection_props.clearinner,
            clear_outer = objectselection_props.clearouter,
            threshold = objectselection_props.axisthreshold,
            )

        obj.vertex_groups.new(name="bisectionloop")
        bpy.ops.object.vertex_group_assign()
        mat = obj.matrix_world
        
        sideA = obj.vertex_groups["bisectionloop"]
        sideA = obj.vertex_groups.new(name="FrontSide")
        sideB = obj.vertex_groups["bisectionloop"]
        sideB = obj.vertex_groups.new(name="BackSide")

        indexarrayA = []
        for vertex in obj.data.vertices:
            pos = mat@vertex.co
            distance = mathutils.geometry.distance_point_to_plane(pos, origin, normal)
            if distance > objectselection_props.axisthreshold:
                indexarrayA.append(vertex.index)
    
        indexarrayB = []
        for vertex in obj.data.vertices:
            pos = mat@vertex.co
            distance = mathutils.geometry.distance_point_to_plane(pos, origin, normal)
            if distance < objectselection_props.axisthreshold:
                indexarrayB.append(vertex.index)

        #only works in Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')
        sideA.add( indexarrayA, 1.0, 'REPLACE' )
        sideB.add( indexarrayB, 1.0, 'REPLACE' )
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.object.vertex_group_set_active(group='bisectionloop')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_set_active(group='FrontSide')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_deselect()
        
        bpy.ops.object.vertex_group_set_active(group='bisectionloop')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_set_active(group='BackSide')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_deselect()
    
        new_objects = []
        
        if objectselection_props.rememberselection:
            bpy.ops.object.vertex_group_set_active(group='prebisectselection')
            bpy.ops.object.vertex_group_select()
            bpy.ops.object.vertex_group_set_active(group='bisectionloop')
            bpy.ops.object.vertex_group_deselect()
            bpy.ops.object.vertex_group_set_active(group='prebisectselection')
            bpy.ops.object.vertex_group_remove()
         
        
        if objectselection_props.clearouter:
            bpy.ops.object.vertex_group_set_active(group='FrontSide')
            bpy.ops.object.vertex_group_remove()
            bpy.ops.object.vertex_group_set_active(group='BackSide')
            #Object Mode needed for the selection of the vertices
            bpy.ops.object.mode_set(mode='OBJECT')
            for v in obj.data.vertices:
                v.select = True
            bpy.ops.object.mode_set(mode='EDIT')

            bpy.ops.object.vertex_group_assign()
        if objectselection_props.clearinner:
            bpy.ops.object.vertex_group_set_active(group='BackSide')
            bpy.ops.object.vertex_group_remove()
            bpy.ops.object.vertex_group_set_active(group='FrontSide')
            #Object Mode needed for the selection of the vertices
            bpy.ops.object.mode_set(mode='OBJECT')
            for v in obj.data.vertices:
                v.select = True
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.vertex_group_assign()
            
        if objectselection_props.separatemesh:
            bpy.ops.object.vertex_group_deselect()
            print("separate begin")
            bpy.ops.object.mode_set(mode='EDIT')
            #bpy.ops.mesh.select_all( action = 'DESELECT' )
            bpy.ops.object.vertex_group_set_active(group='BackSide')
            obj.vertex_groups.active = obj.vertex_groups["BackSide"]
            bpy.ops.object.vertex_group_select()
            #return []
            #for v in obj.data.vertices:
            #    v.select = True
            something_selected = False;
            #dump(obj)
            #selected_verts = list(filter(lambda v: v.select, obj.data.vertices))
            #
            
            #vgVerts = [ v for v in obj.data.vertices if v.select ]
            #print("verts %s " % selected_verts)
            #str = "";
            #for v in obj.data.vertices:
                #for g in v.groups:
                    #dump(g)
                    #print("------------------")
                    #dump(obj.vertex_groups["BackSide"])
                    #if g.group == obj.vertex_groups["BackSide"].index:
                        #something_selected = True
                        #break;
            bpy.ops.object.mode_set(mode='OBJECT')
            for v in obj.data.vertices:
                #dump(v)
                #break;
                if v.select:
                    #print("v.select = %s " % v.select)
                    something_selected = True
                    break;
                
            #print("verts selected %s " % str)
            if something_selected:
                bpy.ops.object.mode_set(mode='EDIT')
                lo_b = [ob for ob in bpy.data.objects if ob.type == 'MESH']
                print("separating")
                bpy.ops.mesh.separate(type='SELECTED')
                lo_a = [ob for ob in bpy.data.objects if ob.type == 'MESH']
                for i in lo_b:
                    lo_a.remove(i)
                print("new_objects %s " % len(lo_a))
                new_objects = lo_a;
            else:
                print("nothing is selected")
            
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        
        bm.free()
        
        return new_objects;
    
    def bisectObjects(self,context,objects, offset):
        
        new_objects = []
        for ob in objects:
            print("processing Object %s " % ob.name)
            bpy.context.view_layer.objects.active = ob
            #dump(ob)
            ob.select_set(True)
            tnew_objects = self.doBisect(context,ob,offset)
            #dump(tnew_objects)
            
            if tnew_objects:
                print(" t new_objects %s " % len(tnew_objects))
                if len(tnew_objects):
                    new_objects=new_objects+new_objects
            #ob.select_set(False)
        
        print("new_objects %s " % len(new_objects))
        return new_objects;
    
    def execute(self, context):
        list_ob = [];
        list_ob = bpy.context.selected_objects;
        
        bpy.ops.object.select_all(action='DESELECT')
        
        for ob in list_ob:
            ob.select_set(False)
        
        objectselection_props = context.window_manager.objectselection_props
        #v1 = Vector(1, 2, 3)
        arrModifiers = GetArrayModifiers(objectselection_props.cuttingplane)
        if(len(arrModifiers) == 0):
            print("No Array modifiers found in " + context.window_manager.objectselection_props.cuttingplane.name)
            self.bisectObjects(context,list_ob,0)
        else:
            #dump(arrModifiers[0])
            
            for i in range(objectselection_props.loopCount):
                print("Slice No: %s" % i)
                tnew_objects = self.bisectObjects(context,list_ob,i*20)
                list_ob=list_ob+tnew_objects
                
            
        ##return {'FINISHED'}
        
        
        #clean up
        
        return {'FINISHED'}


#ui class
class OBJECTSELECTION_Panel(Panel):
    bl_idname = 'OBJECTSELECTION_PT_Panel'
    bl_label = 'Bisect Plus'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bisectplus'
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        
        box = column.box()
        
        cell_props = context.window_manager.objectselection_props
        
        obj = context.active_object
        cell_props.bisecttarget = obj.name
        label = box.label(text="Currently selected target:")

        box1 = box.box()
        box1.label(text=obj.name,icon='OBJECT_DATAMODE')

        cplabeltxt = "Select a cutting plane:"
        if cell_props.cuttingplane:
            cplabeltxt = "Selected cutting plane:"

        box.label(text=cplabeltxt)
        box.prop(cell_props, "cuttingplane")
        box.prop(cell_props, "rememberselection")
        box.prop(cell_props, "selectionoverride")
        column.separator()
        box.prop(cell_props, "fill")
        box.prop(cell_props, "clearinner")
        box.prop(cell_props, "clearouter")
        box.prop(cell_props, "separatemesh")
        box.prop(cell_props, "separateloop")
        box.prop(cell_props, "loopCount")
        box.prop(cell_props, "axisthreshold")
        
        if cell_props.cuttingplane:
            column.separator()
            column.operator("mesh.bisectplus", icon='NONE', text="Ready to bisect")

    @classmethod
    def poll(cls, context):
        #using selected_objects to only show the ui if the object is a mesh
        #and the operation can be done on it
        objs = context.selected_objects
        return objs != [] and objs[0].type == "MESH"


class ObjectSelectionProperties(PropertyGroup):
    bisecttarget: StringProperty(
            name="",
            description="Selected Object to be bisected with the cutting plane,\nhas to be a 'Mesh'",
            )
    
    cuttingplane: PointerProperty(
            name="",
            description="Must be a single face Plane Object to cut.",
            type=bpy.types.Object,
            )
            
    rememberselection: BoolProperty(
            name="Remember manual selection",
            description="Your selection before the operation will be restored,\nafter the operation is done.",
            default=True,
            )   
    
    selectionoverride: BoolProperty(
            name="Override selection",
            description="Overrides your eventual selection and selects all vertices,\nthat way the bisection will go through the entire object.\n\nDon't activate if you have a manual selection!",
            default=False,
            )

    fill: BoolProperty(
            name="Fill",
            description="Fill in the cut\nbeware of new faces if used without clear inner or outer",
            default=False,
            )
            
    clearinner: BoolProperty(
            name="Clear Inner",
            description="Remove geometry behind the plane",
            default=False,
            )
            
    clearouter: BoolProperty(
            name="Clear Outer",
            description="Remove geometry in front of the plane",
            default=False,
            )
            
    separatemesh: BoolProperty(
            name="Separate",
            description="Separate Geometry",
            default=False,
            )
            
    separateloop: BoolProperty(
            name="Separate Loop",
            description="Separate Geometry",
            default=False,
            ) 
                   
    loopCount: IntProperty(
            name="Count:",
            description="How many times",
            default=1,
            min=0,
            max=100,
            )
                    
    axisthreshold: FloatProperty(
            name="Axisthreshold:",
            description="Preserves the geometry along the cutline",
            default=0.0001,
            min=0.00001,
            max=1.0,
            precision=4,
            )

            
classes = (
    ObjectSelectionProperties,
    bisectplus,
    OBJECTSELECTION_Panel,
    )

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.WindowManager.objectselection_props = PointerProperty(
        type=ObjectSelectionProperties
    )

def unregister():
    del bpy.types.WindowManager.objectselection_props

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__" :
    #unregister()
    register()
