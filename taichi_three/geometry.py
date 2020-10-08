import math
import taichi as ti
import taichi_glsl as ts


@ti.func
def plucker(a, b):
    l0 = a[0] * b[1] - b[0] * a[1]
    l1 = a[0] * b[2] - b[0] * a[2]
    l2 = a[0] - b[0]
    l3 = a[1] * b[2] - b[1] * a[2]
    l4 = a[2] - b[2]
    l5 = b[1] - a[1]
    return l0, l1, l2, l3, l4, l5

@ti.func
def plucker_sideop(a, b):
    res = a[0] * b[4] + a[1] * b[5] + a[2] * b[3] + a[3] * b[2] + a[4 ] * b[0] + a[5] * b[1]
    return res

# https://members.loria.fr/SLazard/ARC-Visi3D/Pant-project/files/Line_Triangle.html
# https://www.cnblogs.com/flyuz/p/9471031.html
def plucker_bcoor(u, v, a, b, c):
    ea = plucker(c, b)
    eb = plucker(a, c)
    ec = plucker(b, a)
    L = plucker(u, v)
    sa = plucker_sideop(L, ea)
    sb = plucker_sideop(L, eb)
    sc = plucker_sideop(L, ec)
    return sa, sb, sc


@ti.func
def intersect_triangle(model, camera, I, orig, dir, face):
    posa, posb, posc = model.pos[face[0, 0]], model.pos[face[1, 0]], model.pos[face[2, 0]]
    texa, texb, texc = model.tex[face[0, 1]], model.tex[face[1, 1]], model.tex[face[2, 1]]
    nrma, nrmb, nrmc = model.nrm[face[0, 2]], model.nrm[face[1, 2]], model.nrm[face[2, 2]]

    posa = model.L2W @ posa
    posb = model.L2W @ posb

    sa, sb, sc = plucker_bcoor(orig, orig + dir, posa, posb, posc)
    if sa >= 0 and sb >= 0 and sc >= 0:
        pos = posa * sa + posb * sb + posc * sc
        tex = texa * sa + texb * sb + texc * sc
        nrm = nrma * sa + nrmb * sb + nrmc * sc
        # TODO: depth-test
        camera.fb.update(I, model.pixel_shader(pos, tex, nrm, nrm, nrm))


# http://www.opengl-tutorial.org/cn/intermediate-tutorials/tutorial-13-normal-mapping/
@ti.func
def compute_tangent(dp1, dp2, duv1, duv2):
    IDUV = ti.Matrix([[duv1.x, duv1.y], [duv2.x, duv2.y]]).inverse()
    DPx = ti.Vector([dp1.x, dp2.x])
    DPy = ti.Vector([dp1.y, dp2.y])
    DPz = ti.Vector([dp1.z, dp2.z])
    T = ti.Vector([0.0, 0.0, 0.0])
    B = ti.Vector([0.0, 0.0, 0.0])
    T.x, B.x = IDUV @ DPx
    T.y, B.y = IDUV @ DPy
    T.z, B.z = IDUV @ DPz
    return T, B


@ti.func
def render_triangle(model, camera, face):
    scene = model.scene
    L2W = model.L2W
    posa, posb, posc = model.pos[face[0, 0]], model.pos[face[1, 0]], model.pos[face[2, 0]]
    texa, texb, texc = model.tex[face[0, 1]], model.tex[face[1, 1]], model.tex[face[2, 1]]
    nrma, nrmb, nrmc = model.nrm[face[0, 2]], model.nrm[face[1, 2]], model.nrm[face[2, 2]]
    posa = camera.untrans_pos(L2W @ posa)
    posb = camera.untrans_pos(L2W @ posb)
    posc = camera.untrans_pos(L2W @ posc)
    nrma = camera.untrans_dir(L2W.matrix @ nrma)
    nrmb = camera.untrans_dir(L2W.matrix @ nrmb)
    nrmc = camera.untrans_dir(L2W.matrix @ nrmc)

    pos_center = (posa + posb + posc) / 3
    if ti.static(camera.type == camera.ORTHO):
        pos_center = ts.vec3(0.0, 0.0, 1.0)

    dpab = posa - posb
    dpac = posa - posc
    dtab = texa - texb
    dtac = texa - texc

    normal = ts.cross(dpab, dpac)

    # NOTE: the normal computation indicates that a front-facing face should
    # be COUNTER-CLOCKWISE, i.e., glFrontFace(GL_CCW);
    # this is to be compatible with obj model loading.
    if ts.dot(pos_center, normal) <= 0:

        tan, bitan = compute_tangent(-dpab, -dpac, -dtab, -dtac)

        clra = model.vertex_shader(posa, texa, nrma, tan, bitan)
        clrb = model.vertex_shader(posb, texb, nrmb, tan, bitan)
        clrc = model.vertex_shader(posc, texc, nrmc, tan, bitan)

        A = camera.uncook(posa)
        B = camera.uncook(posb)
        C = camera.uncook(posc)
        scr_norm = ts.cross(A - C, B - A)
        if scr_norm != 0:
            B_A = (B - A) / scr_norm
            A_C = (A - C) / scr_norm

            # screen space bounding box
            M = int(ti.floor(min(A, B, C) - 1))
            N = int(ti.ceil(max(A, B, C) + 1))
            M = ts.clamp(M, 0, ti.Vector(camera.res))
            N = ts.clamp(N, 0, ti.Vector(camera.res))
            for X in ti.grouped(ti.ndrange((M.x, N.x), (M.y, N.y))):
                # barycentric coordinates using the area method
                X_A = X - A
                w_C = ts.cross(B_A, X_A)
                w_B = ts.cross(A_C, X_A)
                w_A = 1 - w_C - w_B

                # https://gitee.com/zxtree2006/tinyrenderer/blob/master/our_gl.cpp
                if ti.static(camera.type != camera.ORTHO):
                    bclip = ts.vec3(w_A / posa.z, w_B / posb.z, w_C / posc.z)
                    bclip /= bclip.x + bclip.y + bclip.z
                    w_A, w_B, w_C = bclip

                # draw
                eps = ti.get_rel_eps() * 0.2
                is_inside = w_A >= -eps and w_B >= -eps and w_C >= -eps
                if not is_inside:
                    continue
                zindex = 1 / (posa.z * w_A + posb.z * w_B + posc.z * w_C)
                if zindex < ti.atomic_max(camera.fb['idepth'][X], zindex):
                    continue

                clr = [a * w_A + b * w_B + c * w_C for a, b, c in zip(clra, clrb, clrc)]
                camera.fb.update(X, model.pixel_shader(*clr))


@ti.func
def render_particle(model, camera, index):
    scene = model.scene
    L2W = model.L2W
    a = model.pos[index]
    r = model.radius[index]
    a = camera.untrans_pos(L2W @ a)
    A = camera.uncook(a)

    rad = camera.uncook(ts.vec3(r, r, a.z), False)

    M = int(ti.floor(A - rad))
    N = int(ti.ceil(A + rad))
    M = ts.clamp(M, 0, ti.Vector(camera.res))
    N = ts.clamp(N, 0, ti.Vector(camera.res))

    for X in ti.grouped(ti.ndrange((M.x, N.x), (M.y, N.y))):
        pos = camera.cook(float(ts.vec3(X, a.z)))
        dp = pos - a
        dp2 = dp.norm_sqr()

        if dp2 > r**2:
            continue

        dz = ti.sqrt(r**2 - dp2)
        zindex = 1 / (a.z - dz)

        if zindex < ti.atomic_max(camera.fb['idepth'][X], zindex):
            continue

        n = ts.vec3(dp.xy, -dz)
        normal = ts.normalize(n)
        view = ts.normalize(a + n)

        color = model.colorize(pos, normal)
        camera.fb['img'][X] = color
        camera.fb['normal'][X] = normal
