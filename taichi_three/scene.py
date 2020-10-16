import taichi as ti
import taichi_glsl as ts
from .transform import *
from .light import *


@ti.data_oriented
class Scene:
    def __init__(self):
        self.lights = []
        self.cameras = []
        self.shadows = []
        self.models = []

    def set_light_dir(self, ldir):
        # changes light direction input to the direction
        # from the light towards the object
        # to be consistent with future light types
        if not self.lights:
            light = Light(ldir)
            self.add_light(light)
        else:
            self.light[0].set(ldir)

    def add_model(self, model):
        model.scene = self
        self.models.append(model)

    def add_camera(self, camera):
        camera.scene = self
        self.cameras.append(camera)

    def add_shadow_camera(self, shadow):
        shadow.scene = self
        self.shadows.append(shadow)

    def add_light(self, light):
        light.scene = self
        self.lights.append(light)

    @ti.kernel
    def render_shadows(self):
        if ti.static(len(self.shadows)):
            for shadow in ti.static(self.shadows):
                shadow.render(self)

    @ti.kernel
    def render(self):
        if ti.static(len(self.cameras)):
            for camera in ti.static(self.cameras):
                camera.render(self)

        else:
            ti.static_print('Warning: no cameras')
