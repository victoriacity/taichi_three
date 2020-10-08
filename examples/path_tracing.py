import taichi as ti
import taichi_three as t3
import numpy as np

ti.init(ti.cpu)

scene = t3.Scene()
obj = t3.readobj('assets/cube.obj', scale=0.8)
model = t3.Model.from_obj(obj)
scene.add_model(model)
camera = t3.RTCamera(pos=[0, 1, -1.8], res=(256, 256))
scene.add_camera(camera)
light = t3.Light([0.4, -1.5, 1.8])
scene.add_light(light)

scene.init()
gui = ti.GUI('Model', camera.res)
while gui.running:
    gui.get_event(None)
    gui.running = not gui.is_pressed(ti.GUI.ESCAPE)
    camera.from_mouse(gui)
    camera.accumate()
    gui.set_image(camera.img)
    gui.show()
