import inspect
import textwrap

from confmodel.errors import ConfigError
from confmodel.interfaces import IConfigData

from six import with_metaclass


class ConfigField(object):
    """
    The base class for all config fields.

    A config field is a descriptor that reads a value from the source data,
    validates it, and transforms it into an appropriate Python object.

    :param str doc:
        Description of this field to be included in generated documentation.

    :param bool required:
        Set to ``True`` if this field is required, ``False`` if it is optional.
        Unless otherwise specified, fields are not required.

    :param default:
        The default value for this field if no value is provided. This is
        unused if the field is required.

    :param bool static:
        Set to ``True`` if this is a static field. See :ref:`static-field-docs`
        for further information.

    :param fallbacks:
        A list of :class:`FieldFallback` objects to try if the value isn't
        present in the source data. See :ref:`field-fallback-docs` for further
        information.

    Subclasses of :class:`ConfigField` are expected to override :meth:`clean`
    to convert values from the source data to the required form. :meth:`clean`
    is called during validation and also on every attribute access, so it
    should not perform expensive computation. (If expensive computation is
    necessary for some reason, the result should be cached.)

    There are two special attributes on this descriptor:

    .. attribute:: field_type = None

        A class attribute that specifies the field type in generated
        documentation. It should be a string, or ``None`` to indicate that the
        field type should remain unspecified.

    .. attribute:: name

        An instance attribute containing the name bound to this descriptor
        instance. It is set by metaclass magic when a :class:`.Config` subclass
        is defined.
    """
    _creation_order = 0

    field_type = None

    def __init__(self, doc, required=False, default=None, static=False,
                 fallbacks=()):
        # This hack is to allow us to track the order in which fields were
        # added to a config class. We want to do this so we can document fields
        # in the same order they're defined.
        self.creation_order = ConfigField._creation_order
        ConfigField._creation_order += 1
        self.name = None
        self.doc = doc
        self.required = required
        self.default = default
        self.static = static
        self.fallbacks = fallbacks

    def get_doc(self):
        """
        Build documentation for this field.

        A reST ``:param:`` field is generated based on the :attr:`name`,
        :attr:`doc`, and :attr:`field_type` attributes.

        :returns:
            A string containing a documentation section for this field.
        """
        if self.field_type is None:
            header = ":param %s:" % (self.name,)
        else:
            header = ":param %s %s:" % (self.field_type, self.name)
        return header, self.doc

    def setup(self, name):
        self.name = name

    def present(self, config, check_fallbacks=True):
        """
        Check if a value for this field is present in the config data.

        :param config:
            :class:`.Config` object containing config data.
        :param bool check_fallbacks:
            If ``False``, fallbacks will not be checked. (This is used
            internally to determine whether to use fallbacks when looking up
            data.)

        :returns:
            ``True`` if the value is present in the provided data, ``False``
            otherwise.
        """
        if self.name in config._config_data:
            return True
        if check_fallbacks:
            for fallback in self.fallbacks:
                if fallback.present(config):
                    return True
        return False

    def validate(self, config):
        """
        Check that the value is present if required and valid if present.

        If the field is required but no value is found, a :exc:`.ConfigError`
        is raised. Further validation is performed by calling :meth:`clean` and
        the value is assumed to be valid if no exceptions are raised.

        :param config:
            :class:`.Config` object containing config data.

        :returns:
            ``None``, but exceptions are raised for validation failures.
        """
        if self.required and not self.present(config):
            raise ConfigError(
                "Missing required config field '%s'" % (self.name,))
        # This will raise an exception if the value exists, but is invalid.
        self.get_value(config)

    def raise_config_error(self, message_suffix):
        """
        Raise a :exc:`.ConfigError` referencing this field.

        The text "Field '<field name>' <message suffix>" is used as the
        exception message.

        :param str message_suffix:
            A string to append to the exception message.

        :returns:
            Doesn't return, but raises a :exc:`.ConfigError`.
        """
        raise ConfigError("Field '%s' %s" % (self.name, message_suffix))

    def clean(self, value):
        """
        Clean and process a value from the source data.

        This should be overridden in subclasses to handle different kinds of
        fields.

        :param value:
            A value from the source data.

        :returns:
            A value suitable for Python code to use. This implementation merely
            returns the value it was given.
        """
        return value

    def find_value(self, config):
        """
        Find a value in the source data, fallbacks, or field default.

        :param config:
            :class:`.Config` object containing config data.

        :returns:
            The first value it finds.
        """
        if self.present(config, check_fallbacks=False):
            return config._config_data.get(self.name, self.default)
        for fallback in self.fallbacks:
            if fallback.present(config):
                return fallback.build_value(config)
        return self.default

    def get_value(self, config):
        """
        Get the cleaned value for this config field.

        This calls :meth:`find_value` to get the raw value and then calls
        :meth:`clean` to process it, unless the value is ``None``.

        This method may be overridden in subclasses if ``None`` needs to be
        handled differently.

        :param config:
            :class:`.Config` object containing config data.

        :returns:
            A cleaned value suitable for Python code to use.
        """
        value = self.find_value(config)
        return self.clean(value) if value is not None else None

    def __get__(self, config, cls):
        if config is None:
            return self
        if config.static and not self.static:
            self.raise_config_error("is not marked as static.")
        return self.get_value(config)

    def __set__(self, config, value):
        raise AttributeError("Config fields are read-only.")


class FieldFallback(object):
    required_fields = None

    def get_field_descriptor(self, config, field_name):
        field = config._fields.get(field_name, None)
        if field is None:
            raise ConfigError(
                "Undefined fallback field: '%s'" % (field_name,))
        return field

    def field_present(self, config, field_name):
        """
        Check if a value for the named field is present in the config data.

        :param config: :class:`.Config` instance containing config data.
        :param str field_name: Name of the field to look up.

        :returns:
            ``True`` if the value is present in the provided data, ``False``
            otherwise.
        """
        field = self.get_field_descriptor(config, field_name)
        return field.present(config)

    def present(self, config):
        if self.required_fields is None:
            raise NotImplementedError(
                "Please set .required_fields or override .present()")

        for field_name in self.required_fields:
            if not self.field_present(config, field_name):
                return False
        return True

    def build_value(self, config):
        raise NotImplementedError("Please implement .build_value()")


def split_and_trim_docstring(docstring):
    lines = docstring.expandtabs().splitlines()
    if not lines:
        return []
    line_indents = set()
    # Examine the indentation of each line, skipping the first line because
    # it's special.
    for line in lines[1:]:
        stripped_line = line.lstrip()
        if stripped_line:
            # Skip empty lines.
            line_indents.add(len(line) - len(stripped_line))
    # Trim the indentation off each line. The first line is still special.
    trimmed_lines = [lines[0].strip()]
    if line_indents:
        indent_trim = min(line_indents)
        for line in lines[1:]:
            trimmed_lines.append(line[indent_trim:].rstrip())
    # Remove initial and final empty lines.
    while trimmed_lines and not trimmed_lines[0]:
        trimmed_lines.pop(0)
    while trimmed_lines and not trimmed_lines[-1]:
        trimmed_lines.pop()
    return trimmed_lines


def generate_doc(cls, fields, header_indent='', indent=' ' * 4):
    """
    Generate a docstring for a cls and its fields.
    """
    doc = split_and_trim_docstring(cls.__doc__ or '')
    doc.append("")
    doc.append("Configuration options:")
    for field in fields:
        header, field_doc = field.get_doc()
        doc.append("")
        doc.append(header_indent + header)
        doc.append("")
        doc.extend(textwrap.wrap(field_doc, initial_indent=indent,
                                 subsequent_indent=indent))
    return "\n".join(doc)


class ConfigMetaClass(type):
    def __new__(mcs, name, bases, class_dict):
        # locate Field instances
        fields = []
        unified_class_dict = {}
        for base in bases:
            unified_class_dict.update(inspect.getmembers(base))
        unified_class_dict.update(class_dict)

        for key, possible_field in unified_class_dict.items():
            if isinstance(possible_field, ConfigField):
                fields.append(possible_field)
                possible_field.setup(key)

        fields.sort(key=lambda f: f.creation_order)
        class_dict['_fields'] = dict((f.name, f) for f in fields)
        class_dict['_field_names'] = tuple(f.name for f in fields)
        cls = type.__new__(mcs, name, bases, class_dict)
        cls.__doc__ = generate_doc(cls, fields)
        return cls


class Config(with_metaclass(ConfigMetaClass, object)):
    """
    Config object.
    """

    __metaclass__ = ConfigMetaClass

    def __init__(self, config_data, static=False):
        self._config_data = IConfigData(config_data)
        self.static = static
        for field in self._get_fields():
            if self.static and not field.static:
                # Skip non-static fields on static configs.
                continue
            field.validate(self)
        self.post_validate()

    @classmethod
    def _get_fields(cls):
        return [cls._fields[field_name] for field_name in cls._field_names]

    def raise_config_error(self, message):
        """
        Raise a :exc:`.ConfigError` with the given message.
        """
        raise ConfigError(message)

    def post_validate(self):
        """
        Subclasses may override this to provide cross-field validation.

        Implementations should raise :exc:`.ConfigError` if the configuration
        is invalid (by calling :meth:`raise_config_error`, for example).
        """
        pass
