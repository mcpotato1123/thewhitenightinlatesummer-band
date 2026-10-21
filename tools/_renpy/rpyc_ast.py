"""Load Ren'Py .rpyc (RENPY RPC2) AST pickles with stub classes.

The pickled AST references renpy.* classes that only exist inside the engine.
We register permissive stand-ins so the object graph can be rebuilt and walked.
"""
import io
import pickle
import struct
import sys
import zlib

HEADER = b"RENPY RPC2"


def read_slots(blob):
    """Return {slot: uncompressed bytes} for a .rpyc blob."""
    slots = {}
    if not blob.startswith(HEADER):
        # legacy: whole file is one zlib stream = slot 1
        return {1: zlib.decompress(blob)}
    pos = len(HEADER)
    while True:
        slot, start, length = struct.unpack('<III', blob[pos:pos + 12])
        pos += 12
        if slot == 0:
            break
        slots[slot] = zlib.decompress(blob[start:start + length])
    return slots


class Stub(object):
    """Permissive placeholder for any renpy class."""

    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        self._args = args

    def __setstate__(self, state):
        if isinstance(state, dict):
            self.__dict__.update(state)
        elif isinstance(state, tuple) and len(state) == 2 and isinstance(state[1], dict):
            self.__dict__.update(state[1])
        else:
            self._state = state

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, _short(self.__dict__))


def _short(d, n=3):
    items = []
    for k, v in list(d.items())[:n]:
        if isinstance(v, str):
            v = v if len(v) < 40 else v[:37] + '...'
        items.append('%s=%r' % (k, v))
    return ', '.join(items)


_classes = {}


def _stub_class(module, name):
    key = (module, name)
    cls = _classes.get(key)
    if cls is None:
        # Container subclasses are pickled with SETITEMS/APPENDS, so the
        # stand-in has to actually behave like the builtin it imitates.
        if name.endswith('Dict') or name == 'dict':
            base = dict
        elif name.endswith('List') or name.endswith('Set') or name in ('tuple', 'list', 'set'):
            base = list
        else:
            base = Stub
        bases = (base,) if base is Stub else (base, Stub)
        cls = type(name, bases, {'__module__': module})
        _classes[key] = cls
    return cls


class RpycUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except Exception:
            return _stub_class(module, name)


def load_stmts(blob, slot=2):
    """Return (header_dict, [top-level AST nodes])."""
    slots = read_slots(blob)
    data = slots.get(slot) or slots.get(1)
    return RpycUnpickler(io.BytesIO(data)).load()
