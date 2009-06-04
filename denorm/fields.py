# -*- coding: utf-8 -*-
from django.db import models
from denorm import denorms

def denormalized(DBField,*args,**kwargs):
    """
    Turns a callable into model field, analogous to python's ``@property`` decorator.
    The callable will be used to compute the value of the field every time the model
    gets saved.
    If the callable has dependency information attached to it the fields value will
    also be recomputed if the dependencies require it.

    **Arguments:**

    DBField (required)
        The type of field you want to use to save the data.
        Note that you have to use the field class and not an instance
        of it.

    \*args, \*\*kwargs:
        Those will be passed unaltered into the constructor of ``DBField``
        once it gets actually created.
    """

    class DenormDBField(DBField):

        """
        Special subclass of the given DBField type, with a few extra additions.
        """

        def contribute_to_class(self,cls,name,*args,**kwargs):
            self.denorm.model = cls
            self.denorm.fieldname = name
            self.field_args = (args, kwargs)
            models.signals.class_prepared.connect(self.denorm.setup,sender=cls)
            DBField.contribute_to_class(self,cls,name,*args,**kwargs)

        def south_field_definition(self):
            """
            the old way of telling south how this field should be
            inserted into migrations, this will be removed soon
            """
            import warnings
            warnings.warn("south_field_definition will be deprecated, you should really update your south version.",DeprecationWarning)
            if DBField.__module__.startswith("django.db.models.fields"):
                arglist = [repr(x) for x in args]
                kwlist = ["%s=%r" % (x, y) for x, y in kwargs.items()]
                return "%s(%s)" % (
                    DBField.__name__,
                    ", ".join(arglist + kwlist)
                )

        def south_field_triple(self):
            """
            Because this field will be defined as a decorator, give
            South hints on how to recreate it for database use.
            """
            if DBField.__module__.startswith("django.db.models.fields"):
                return (
                    '.'.join(('models',DBField.__name__)),
                    [repr(x) for x in args],
                    kwargs,
                )

    def deco(func):
        denorm = denorms.CallbackDenorm()
        denorm.func = func
        dbfield = DenormDBField(*args,**kwargs)
        dbfield.denorm = denorm
        return dbfield
    return deco

class CountField(models.PositiveIntegerField):
    """
    A ``PositiveIntegerField`` that stores the number of rows
    related to this model instance through the specified manager.
    The value will be incrementally updated when related objects
    are added and removed.

    **Arguments:**

    manager_name:
        The name of the related manager to be counted.

    \*args, \*\*kwargs:
        Those will be passed into the constructor of ``PositiveIntegerField``.
        kwargs['default'] will be set to 0.
    """
    def __init__(self,manager_name,*args,**kwargs):
        self.denorm = denorms.CountDenorm()
        self.denorm.manager_name = manager_name
        kwargs["default"] = 0
        super(CountField,self).__init__(*args,**kwargs)

    def contribute_to_class(self,cls,name,*args,**kwargs):
        self.denorm.model = cls
        self.denorm.fieldname = name
        models.signals.class_prepared.connect(self.denorm.setup)
        super(CountField,self).contribute_to_class(cls,name,*args,**kwargs)
