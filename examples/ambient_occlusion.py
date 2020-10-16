import taichi as ti
import taichi_three as t3
import numpy as np

ti.init(ti.cpu)

scene = t3.Scene()
obj = t3.readobj('assets/torus.obj', scale=0.8)
model = t3.Model(t3.Mesh.from_obj(obj))
model.material = t3.Material(t3.CookTorrance(
    color=t3.Texture(ti.imread('assets/cloth.jpg')),
    ambient=t3.Texture(ti.imread('assets/pattern.jpg')),
    ))
scene.add_model(model)
camera = t3.Camera()
camera.ctl = t3.CameraCtl(pos=[0, 1, -1.8])
scene.add_camera(camera)
ambient_light = t3.AmbientLight()
scene.add_light(ambient_light)

gui = ti.GUI('Model', camera.res)
while gui.running:
    gui.get_event(None)
    gui.running = not gui.is_pressed(ti.GUI.ESCAPE)
    camera.from_mouse(gui)
    scene.render()
    gui.set_image(camera.img)
    gui.show()
