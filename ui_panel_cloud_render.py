bl_info = {
    "name": "Cloud Render",
    "author": "irfanpule",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Render Properties > Cloud Render",
    "description": "To Easy Render on your cloud",
    "warning": "",
    "wiki_url": "",
    "category": "Render",
}


import bpy
import requests
import time
from requests.compat import urljoin


import bpy
import time


class CRAPIResponse:
    error = None
    data = {}
    message = ""
    

class CRAPI:
    login_url = ""
    upload_url = ""
    render_url = ""
    response = CRAPIResponse()
    auth = None
    
    def __init__(self, host, username, password):
        self.login_url = urljoin(host, "/api/check-auth/")
        self.upload_url = urljoin(host, "/api/upload-file/")
        self.render_url = urljoin(host, "/api/render/")
        self.auth = (username, password)
    
    def _response_handler(self, response):
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            self.response.error = False
            self.response.data = data
            self.response.message = data.get("message", "success")
        elif response.status_code == 500:
            self.response.error = True
            self.response.data = {}
            self.response.message = "Error 500. Server Error"
        elif response.status_code == 403:
            data = response.json()
            self.response.error = True
            self.response.data = {}
            message = data.get("message") or data.get("detail")
            self.response.message = message
        else:
            data = response.json()
            self.response.error = False
            self.response.data = data
            message = data.get("message") or data.get("detail")
            self.response.message = message
        print(response.text, "reponsenya")
        return self.response
            
    def login(self):
        resp = requests.get(self.login_url, auth=self.auth)
        print(self.auth, self.login_url)
        return self._response_handler(resp)
    
    def upload_file(self, project_name, file):
        data = {
            "name": project_name,
            "file": file
        }
        files = {'file': open(file, 'rb')}
        resp = requests.post(self.upload_url, data=data, files=files, auth=self.auth)
        return self._response_handler(resp)
    
    def get_spec_server(self, project_id):
        url = urljoin(self.render_url, project_id)
        resp = requests.get(url, auth=self.auth)
        return self._response_handler(resp)
    
    def rendering(self, project_id, start_frame, end_frame, total_thread, option_cycles):
        data = {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "total_thread": total_thread,
            "option_cycles": option_cycles
        }
        url = urljoin(self.render_url, project_id)
        resp = requests.post(url, data=data, auth=self.auth)
        return self._response_handler(resp)


class CRProperties(bpy.types.PropertyGroup):
    cr_host: bpy.props.StringProperty(name="Host", default="http://localhost:5555/")
    cr_password: bpy.props.StringProperty(name="Password", subtype='PASSWORD')
    cr_project_name: bpy.props.StringProperty(name="Project Name")
    cr_username: bpy.props.StringProperty(name="Username")
    cr_file: bpy.props.StringProperty(name="File", default=bpy.data.filepath, subtype='FILE_PATH')
    cr_project_id: bpy.props.StringProperty(name="Project Id")
    cr_start_frame: bpy.props.IntProperty(name="Start Frame", soft_min=1, default=1)
    cr_end_frame: bpy.props.IntProperty(name="End Frame")


class CRLoginOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.cr_login"
    bl_label = "Check Authentication"

    def execute(self, context):
        host = context.scene.cr_tools.cr_host
        username = context.scene.cr_tools.cr_username
        password = context.scene.cr_tools.cr_password
        if username == "" or password == "":
            self.report({"WARNING"}, "Username or Password can't null")
            return {"CANCELLED"}
        
        crapi = CRAPI(host, username, password)
        crapi.login()
        if crapi.response.error:
            self.report({"WARNING"}, crapi.response.message)
            return {"CANCELLED"}

        self.report({"INFO"}, crapi.response.message)
        return {"FINISHED"}

    
class CRUploadProjectOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.cr_upload_file"
    bl_label = "Upload File"

    def execute(self, context):
        print("uploading")
        host = context.scene.cr_tools.cr_host
        username = context.scene.cr_tools.cr_username
        password = context.scene.cr_tools.cr_password
    
        project_name = context.scene.cr_tools.cr_project_name
        username = context.scene.cr_tools.cr_username
        file = context.scene.cr_tools.cr_file
        if project_name == "" or username == "" or file == "":
            self.report({"WARNING"}, "Project Name or Username or File can't null")
            return {"CANCELLED"}
        
        crapi = CRAPI(host, username, password)
        crapi.upload_file(project_name, file)
        if crapi.response.error:
            self.report({"WARNING"}, crapi.response.message)
            return {"CANCELLED"}

        self.report({"INFO"}, crapi.response.message)
        context.scene.cr_tools.cr_project_id = crapi.response.data['id']
        context.scene.cr_tools.cr_start_frame = 1
        context.scene.cr_tools.cr_end_frame = context.scene.frame_end
        return {"FINISHED"}

    
class CRRenderingOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.cr_rendering"
    bl_label = "Render"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        print("rendering")
        host = context.scene.cr_tools.cr_host
        username = context.scene.cr_tools.cr_username
        password = context.scene.cr_tools.cr_password
    
        project_id = context.scene.cr_tools.cr_project_id
        start_frame = context.scene.cr_tools.cr_start_frame
        end_frame = context.scene.cr_tools.cr_end_frame
        
        crapi = CRAPI(host, username, password)
        crapi.rendering(project_id, start_frame, end_frame, 4, "CPU")
        if crapi.response.error:
            self.report({"WARNING"}, crapi.response.message)
            return {"CANCELLED"}
        print(project_id, "project Id")
        
        self.report({"INFO"}, crapi.response.message)
        return {"FINISHED"}



class CRPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Cloud Render"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        crtools = scene.cr_tools
        
        # Create input host server
        layout.label(text="Credential:")
        row = layout.row()
        row.prop(crtools, "cr_host")
        row = layout.row()
        row.prop(crtools, "cr_username")
        row = layout.row()
        row.prop(crtools, "cr_password")
        row = layout.row()
        row.operator("object.cr_login")
        
        # Create input detail project
        layout.label(text="Detail Project:")
        row = layout.row()
        row.prop(crtools, "cr_project_name")
        row = layout.row()
        row.prop(crtools, "cr_file")
        row = layout.row()
        row.operator("object.cr_upload_file")
        
        # Create input render option.
        layout.label(text="Select frames:")

        row = layout.row()
        
        row.prop(crtools, "cr_start_frame")
        row.prop(crtools, "cr_end_frame")
        
        row = layout.row()
        row.scale_y = 2.0
        row.operator("object.cr_rendering")


classes = [
    CRProperties, CRPanel, CRLoginOperator, CRUploadProjectOperator, CRRenderingOperator
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cr_tools = bpy.props.PointerProperty(type=CRProperties)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
