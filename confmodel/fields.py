from copy import deepcopy

try:
    from urllib2 import urlparse
except ImportError:
    import urllib.parse as urlparse

import re

from confmodel.config import ConfigField


class ConfigText(ConfigField):
    field_type = 'str'

    def clean(self, value):
        # XXX: We should really differentiate between "unicode" and "bytes".
        #      However, yaml.load() gives us bytestrings or unicode depending
        #      on the content.
        if not isinstance(value, basestring):
            self.raise_config_error("is not unicode.")
        return value


class ConfigInt(ConfigField):
    field_type = 'int'

    def clean(self, value):
        try:
            # We go via "str" to avoid silently truncating floats.
            # XXX: Is there a better way to do this?
            return int(str(value))
        except (ValueError, TypeError):
            self.raise_config_error("could not be converted to int.")


class ConfigFloat(ConfigField):
    field_type = 'float'

    def clean(self, value):
        try:
            return float(value)
        except (ValueError, TypeError):
            self.raise_config_error("could not be converted to float.")


class ConfigBool(ConfigField):
    field_type = 'bool'

    def clean(self, value):
        if isinstance(value, basestring):
            return value.strip().lower() not in ('false', '0', '')
        return bool(value)


class ConfigList(ConfigField):
    field_type = 'list'

    def clean(self, value):
        if isinstance(value, tuple):
            value = list(value)
        if not isinstance(value, list):
            self.raise_config_error("is not a list.")
        return deepcopy(value)


class ConfigDict(ConfigField):
    field_type = 'dict'

    def clean(self, value):
        if not isinstance(value, dict):
            self.raise_config_error("is not a dict.")
        return deepcopy(value)


class ConfigUrl(ConfigField):
    field_type = 'URL'

    def clean(self, value):
        if not isinstance(value, basestring):
            self.raise_config_error("is not a URL string.")
        # URLs must be bytes, not unicode.
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return urlparse.urlparse(value)


class ConfigRegex(ConfigText):
    field_type = 'regex'

    def clean(self, value):
        value = super(ConfigRegex, self).clean(value)
        return re.compile(value)
