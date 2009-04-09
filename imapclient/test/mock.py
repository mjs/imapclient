# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2008 Michael Foord
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 0.4.0
# http://www.voidspace.org.uk/python/mock.html

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.

__all__ = (
    'Mock',
    'patch',
    'patch_object',
    'sentinel',
    '__version__'
)

__version__ = '0.4.0'

DEFAULT = object()


class Mock(object):
    def __init__(self, methods=None, spec=None, side_effect=None, 
                 return_value=DEFAULT, name=None, parent=None):
        self._parent = parent
        self._name = name
        if spec is not None and methods is None:
            methods = [member for member in dir(spec) if not 
                       (member.startswith('__') and  member.endswith('__'))]
        self._methods = methods
        self._children = {}
        self._return_value = return_value
        self.side_effect = side_effect
        
        self.reset()
        
        
    def reset(self):
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.call_args_list = []
        self.method_calls = []
        for child in self._children.itervalues():
            child.reset()
        if isinstance(self._return_value, Mock):
            self._return_value.reset()
        
    
    def __get_return_value(self):
        if self._return_value is DEFAULT:
            self._return_value = Mock()
        return self._return_value
    
    def __set_return_value(self, value):
        self._return_value = value
        
    return_value = property(__get_return_value, __set_return_value)


    def __call__(self, *args, **kwargs):
        self.called = True
        self.call_count += 1
        self.call_args = (args, kwargs)
        self.call_args_list.append((args, kwargs))
        
        parent = self._parent
        name = self._name
        while parent is not None:
            parent.method_calls.append((name, args, kwargs))
            if parent._parent is None:
                break
            name = parent._name + '.' + name
            parent = parent._parent

        if self.side_effect is not None:
            self.side_effect()
            
        return self.return_value
    
    
    def __getattr__(self, name):
        if self._methods is not None and name not in self._methods:
            raise AttributeError("object has no attribute '%s'" % name)
        
        if name not in self._children:
            self._children[name] = Mock(parent=self, name=name)
            
        return self._children[name]
    
    
    def assert_called_with(self, *args, **kwargs):
        assert self.call_args == (args, kwargs), 'Expected: %s\nCalled with: %s' % ((args, kwargs), self.call_args)
        

        
def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


def _patch(target, attribute, new):
        
    def patcher(func):
        original = getattr(target, attribute)
        if hasattr(func, 'restore_list'):
            func.restore_list.append((target, attribute, original))
            func.patch_list.append((target, attribute, new))
            return func
        
        func.restore_list = [(target, attribute, original)]
        func.patch_list = [(target, attribute, new)]
        
        def patched(*args, **keywargs):
            for target, attribute, new in func.patch_list:
                if new is DEFAULT:
                    new = Mock()
                    args += (new,)
                setattr(target, attribute, new)
            try:
                return func(*args, **keywargs)
            finally:
                for target, attribute, original in func.restore_list:
                    setattr(target, attribute, original)
                    
        patched.__name__ = func.__name__ 
        patched.compat_co_firstlineno = getattr(func, "compat_co_firstlineno", 
                                                func.func_code.co_firstlineno)
        return patched
    
    return patcher


def patch_object(target, attribute, new=DEFAULT):
    return _patch(target, attribute, new)


def patch(target, new=DEFAULT):
    try:
        target, attribute = target.rsplit('.', 1)    
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: %s" % (target,))
    target = _importer(target)
    return _patch(target, attribute, new)


class SentinelObject(object):
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return '<SentinelObject "%s">' % self.name


class Sentinel(object):
    def __init__(self):
        self._sentinels = {}
        
    def __getattr__(self, name):
        return self._sentinels.setdefault(name, SentinelObject(name))
    
    
sentinel = Sentinel()
