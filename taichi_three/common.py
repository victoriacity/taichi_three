import numpy as np
import taichi as ti
import functools


def create_field(dim, dtype, shape=None, initial=None, **kwargs):
    if dim is None:
        return dtype(shape, **kwargs)
    if dim == 0:
        dim = ()
    if not isinstance(dim, (list, tuple)):
        dim = [dim]
    if isinstance(dim, list):
        dim = tuple(dim)

    if len(dim) == 0:
        ret = ti.field(dtype, shape, **kwargs)
    elif len(dim) == 1:
        ret = ti.Vector.field(dim[0], dtype, shape, **kwargs)
    elif len(dim) == 2:
        ret = ti.Matrix.field(dim[0], dim[1], dtype, shape, **kwargs)
    else:
        raise TypeError(f'Expect int or tuple for dim, got: {dim}')

    if initial is not None:
        if callable(initial):
            ti.materialize_callback(initial)
        else:
            initial = np.array(initial, dtype=ti.to_numpy_type(dtype))
            @ti.materialize_callback
            def init_field():
                ret.from_numpy(initial)

    return ret



@ti.data_oriented
class DataOriented(object):
    pass



class subscriptable(property):
    def __init__(self, func):
        self.func = func

        @functools.wraps(func)
        def accessor(this):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                return func(this, *args, **kwargs)

            @functools.wraps(func)
            def subscript(*indices):
                if len(indices) == 1 and indices[0] is None:
                    indices = []
                return func(this, *indices)

            wrapped.subscript = subscript
            wrapped.is_taichi_class = True

            return wrapped

        super().__init__(accessor)


class dummy_expression:
    is_taichi_class = True

    def __getattr__(self, key):
        def wrapped(*args, **kwargs):
            return self
        wrapped.__name__ = key
        return wrapped

_old_begin_frontend_if = ti.begin_frontend_if

def _begin_frontend_if(cond):
    if isinstance(cond, dummy_expression):
        cond = 0
    return _old_begin_frontend_if(cond)

ti.begin_frontend_if = _begin_frontend_if
