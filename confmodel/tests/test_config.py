from unittest import TestCase

from confmodel.config import (
    Config, ConfigField, ConfigText, ConfigInt, ConfigFloat, ConfigBool,
    ConfigList, ConfigDict, ConfigUrl, ConfigRegex, FieldFallback,
    fallback_build_value_passthrough)
from confmodel.errors import ConfigError


class TestConfig(TestCase):
    def test_simple_config(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("foo")
            bar = ConfigField("bar")

        conf = FooConfig({'foo': 'blah'})
        self.assertEqual(conf.foo, 'blah')
        self.assertEqual(conf.bar, None)

        conf = FooConfig({'bar': 'blah'})
        self.assertEqual(conf.foo, None)
        self.assertEqual(conf.bar, 'blah')

    def test_required_field(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("foo", required=True)
            bar = ConfigField("bar")

        conf = FooConfig({'foo': 'blah'})
        self.assertEqual(conf.foo, 'blah')
        self.assertEqual(conf.bar, None)

        self.assertRaises(ConfigError, FooConfig, {'bar': 'blah'})

    def test_static_field(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("foo", required=True, static=True)
            bar = ConfigField("bar")

        conf = FooConfig({'foo': 'blah', 'bar': 'baz'}, static=True)
        self.assertEqual(conf.foo, 'blah')
        self.assertRaises(ConfigError, lambda: conf.bar)

    def test_default_field(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("what 'twas", default="brillig")
            bar = ConfigField("tove status", default="slithy")

        conf = FooConfig({'foo': 'blah'})
        self.assertEqual(conf.foo, 'blah')
        self.assertEqual(conf.bar, 'slithy')

        conf = FooConfig({'bar': 'blah'})
        self.assertEqual(conf.foo, 'brillig')
        self.assertEqual(conf.bar, 'blah')

    def test_doc(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("A foo field.")
            bar = ConfigText("A bar field.")

        self.assertEqual(FooConfig.__doc__, '\n'.join([
            "Test config.",
            "",
            "Configuration options:",
            "",
            ":param foo:",
            "",
            "    A foo field.",
            "",
            ":param str bar:",
            "",
            "    A bar field.",
            ]))

        # And again with the fields defined in a different order to check that
        # we document fields in definition order.
        class BarConfig(Config):
            "Test config."
            bar = ConfigField("A bar field.")
            foo = ConfigField("A foo field.")

        self.assertEqual(BarConfig.__doc__, '\n'.join([
            "Test config.",
            "",
            "Configuration options:",
            "",
            ":param bar:",
            "",
            "    A bar field.",
            "",
            ":param foo:",
            "",
            "    A foo field.",
            ]))

    def test_inheritance(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("From base class.")

        class BarConfig(FooConfig):
            "Another test config."
            bar = ConfigField("New field.")

        conf = BarConfig({'foo': 'blah', 'bar': 'bleh'})
        self.assertEqual(conf.fields,
                         [FooConfig.foo, BarConfig.bar])
        self.assertEqual(conf.foo, 'blah')
        self.assertEqual(conf.bar, 'bleh')

        # Inherited fields should come before local fields.
        self.assertEqual(BarConfig.__doc__, '\n'.join([
            "Another test config.",
            "",
            "Configuration options:",
            "",
            ":param foo:",
            "",
            "    From base class.",
            "",
            ":param bar:",
            "",
            "    New field.",
            ]))

    def test_double_inheritance(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("From base class.")

        class BarConfig(FooConfig):
            "Another test config."
            bar = ConfigField("From middle class.")

        class BazConfig(BarConfig):
            "Second-level inheritance test config."
            baz = ConfigField("From top class.")

        conf = BazConfig({'foo': 'blah', 'bar': 'bleh', 'baz': 'blerg'})
        self.assertEqual(conf.fields,
                         [FooConfig.foo, BarConfig.bar, BazConfig.baz])
        self.assertEqual(conf.foo, 'blah')
        self.assertEqual(conf.bar, 'bleh')
        self.assertEqual(conf.baz, 'blerg')

    def test_validation(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("foo", required=True, static=True)
            bar = ConfigInt("bar", required=True)

        conf = FooConfig({'foo': 'blah', 'bar': 1})
        self.assertEqual(conf.foo, 'blah')
        self.assertEqual(conf.bar, 1)

        self.assertRaises(ConfigError, FooConfig, {})
        self.assertRaises(ConfigError, FooConfig, {'foo': 'blah', 'baz': 'hi'})

    def test_static_validation(self):
        class FooConfig(Config):
            "Test config."
            foo = ConfigField("foo", required=True, static=True)
            bar = ConfigInt("bar", required=True)

        conf = FooConfig({'foo': 'blah'}, static=True)
        self.assertEqual(conf.foo, 'blah')

        conf = FooConfig({'foo': 'blah', 'bar': 'hi'}, static=True)
        self.assertEqual(conf.foo, 'blah')

        self.assertRaises(ConfigError, FooConfig, {}, static=True)

    def test_post_validate(self):
        class FooConfig(Config):
            foo = ConfigInt("foo", required=True)

            def post_validate(self):
                if self.foo < 0:
                    self.raise_config_error("'foo' must be non-negative")

        conf = FooConfig({'foo': 1})
        self.assertEqual(conf.foo, 1)

        self.assertRaises(ConfigError, FooConfig, {'foo': -1})

    def test_fields_read_only(self):
        class FooConfig(Config):
            foo = ConfigInt("foo")

        conf = FooConfig({'foo': 1})
        self.assertRaises(AttributeError, setattr, conf, 'foo', 2)


class FakeModel(object):
    def __init__(self, config):
        self._config_data = config


class TestConfigField(TestCase):
    def fake_model(self, *value, **kw):
        config = kw.pop('config', {})
        if value:
            assert len(value) == 1
            config['foo'] = value[0]
        return FakeModel(config)

    def field_value(self, field, *value, **kw):
        self.assert_field_valid(field, *value, **kw)
        return field.get_value(self.fake_model(*value, **kw))

    def assert_field_valid(self, field, *value, **kw):
        field.validate(self.fake_model(*value, **kw))

    def assert_field_invalid(self, field, *value, **kw):
        self.assertRaises(ConfigError, field.validate,
                          self.fake_model(*value, **kw))

    def make_field(self, field_cls, **kw):
        field = field_cls("desc", **kw)
        field.setup('foo')
        return field

    def test_text_field(self):
        field = self.make_field(ConfigText)
        self.assertEqual('foo', self.field_value(field, 'foo'))
        self.assertEqual(u'foo', self.field_value(field, u'foo'))
        self.assertEqual(u'foo\u1234', self.field_value(field, u'foo\u1234'))
        self.assertEqual(None, self.field_value(field, None))
        self.assertEqual(None, self.field_value(field))
        self.assert_field_invalid(field, object())
        self.assert_field_invalid(field, 1)

    def test_regex_field(self):
        field = self.make_field(ConfigRegex)
        value = self.field_value(field, '^v[a-z]m[a-z]$')
        self.assertTrue(value.match('vumi'))
        self.assertFalse(value.match('notvumi'))
        self.assertEqual(None, self.field_value(field, None))

    def test_int_field(self):
        field = self.make_field(ConfigInt)
        self.assertEqual(0, self.field_value(field, 0))
        self.assertEqual(1, self.field_value(field, 1))
        self.assertEqual(100, self.field_value(field, "100"))
        self.assertEqual(100, self.field_value(field, u"100"))
        self.assertEqual(None, self.field_value(field, None))
        self.assertEqual(None, self.field_value(field))
        self.assert_field_invalid(field, object())
        self.assert_field_invalid(field, 2.3)
        self.assert_field_invalid(field, "foo")
        self.assert_field_invalid(field, u"foo\u1234")

    def test_float_field(self):
        field = self.make_field(ConfigFloat)
        self.assertEqual(0, self.field_value(field, 0))
        self.assertEqual(1, self.field_value(field, 1))
        self.assertEqual(0.5, self.field_value(field, 0.5))
        self.assertEqual(0.5, self.field_value(field, "0.5"))
        self.assertEqual(100, self.field_value(field, "100"))
        self.assertEqual(100, self.field_value(field, u"100"))
        self.assertEqual(None, self.field_value(field, None))
        self.assertEqual(None, self.field_value(field))
        self.assert_field_invalid(field, object())
        self.assert_field_invalid(field, "foo")
        self.assert_field_invalid(field, u"foo\u1234")

    def test_bool_field(self):
        field = self.make_field(ConfigBool)
        self.assertEqual(False, self.field_value(field, 0))
        self.assertEqual(True, self.field_value(field, 1))
        self.assertEqual(False, self.field_value(field, "0"))
        self.assertEqual(True, self.field_value(field, "true"))
        self.assertEqual(True, self.field_value(field, "TrUe"))
        self.assertEqual(False, self.field_value(field, u"false"))
        self.assertEqual(False, self.field_value(field, ""))
        self.assertEqual(True, self.field_value(field, True))
        self.assertEqual(False, self.field_value(field, False))
        self.assertEqual(None, self.field_value(field, None))
        self.assertEqual(None, self.field_value(field))

    def test_list_field(self):
        field = self.make_field(ConfigList)
        self.assertEqual([], self.field_value(field, []))
        self.assertEqual([], self.field_value(field, ()))
        self.assertEqual([0], self.field_value(field, [0]))
        self.assertEqual(["foo"], self.field_value(field, ["foo"]))
        self.assertEqual(None, self.field_value(field, None))
        self.assertEqual(None, self.field_value(field))
        self.assert_field_invalid(field, object())
        self.assert_field_invalid(field, "foo")
        self.assert_field_invalid(field, 123)

    def test_list_field_immutable(self):
        field = self.make_field(ConfigList)
        model = self.fake_model(['fault', 'mine'])
        value = field.get_value(model)
        self.assertEqual(value, ['fault', 'mine'])
        value[1] = 'yours'
        self.assertEqual(field.get_value(model), ['fault', 'mine'])

    def test_dict_field(self):
        field = self.make_field(ConfigDict)
        self.assertEqual({}, self.field_value(field, {}))
        self.assertEqual({'foo': 1}, self.field_value(field, {'foo': 1}))
        self.assertEqual({1: 'foo'}, self.field_value(field, {1: 'foo'}))
        self.assertEqual(None, self.field_value(field, None))
        self.assertEqual(None, self.field_value(field))
        self.assert_field_invalid(field, object())
        self.assert_field_invalid(field, "foo")
        self.assert_field_invalid(field, 123)

    def test_dict_field_immutable(self):
        field = self.make_field(ConfigDict)
        model = self.fake_model({'fault': 'mine'})
        value = field.get_value(model)
        self.assertEqual(value, {'fault': 'mine'})
        value['fault'] = 'yours'
        self.assertEqual(field.get_value(model), {'fault': 'mine'})

    def test_url_field(self):
        def assert_url(value,
                       scheme='', netloc='', path='', query='', fragment=''):
            self.assertEqual(value.scheme, scheme)
            self.assertEqual(value.netloc, netloc)
            self.assertEqual(value.path, path)
            self.assertEqual(value.query, query)
            self.assertEqual(value.fragment, fragment)

        field = self.make_field(ConfigUrl)
        assert_url(self.field_value(field, 'foo'), path='foo')
        assert_url(self.field_value(field, u'foo'), path='foo')
        assert_url(self.field_value(field, u'foo\u1234'),
                   path='foo\xe1\x88\xb4')
        self.assertEqual(None, self.field_value(field, None))
        self.assertEqual(None, self.field_value(field))
        self.assert_field_invalid(field, object())
        self.assert_field_invalid(field, 1)


class TestFieldFallback(TestCase):
    def test_get_fields(self):
        class ConfigWithFallback(Config):
            field1 = ConfigText("field1", required=True)
            field2 = ConfigInt("field2")
            field3 = ConfigBool("field3")

        fallback = FieldFallback(['field1', 'field3'])
        config = ConfigWithFallback({'field1': 'foo'})
        self.assertEqual(fallback.get_fields(config), {
            # We need to get the descriptors off the class.
            'field1': ConfigWithFallback.field1,
            'field3': ConfigWithFallback.field3,
        })

    def test_get_fields_undefined_field(self):
        class ConfigWithFallback(Config):
            field1 = ConfigText("field1", required=True)
            field2 = ConfigInt("field2")

        fallback = FieldFallback(['field1', 'field3'])
        config = ConfigWithFallback({'field1': 'foo'})
        self.assertRaises(ConfigError, fallback.get_fields, config)
        # Python 2.6 doesn't provide a mechanism to get the exception object,
        # so we do this by hand.
        try:
            fallback.get_fields(config)
        except ConfigError, err:
            self.assertEqual(err.args[0], "Undefined fallback field: 'field3'")

    def test_validation_simple(self):
        class ConfigWithFallback(Config):
            field = ConfigText("field", required=True)

        fallback = FieldFallback(['field'])
        config = ConfigWithFallback({'field': 'foo'})
        fallback.validate(config)

    def test_fallback_build_value_passthrough(self):
        self.assertEqual(
            fallback_build_value_passthrough({'foo': 'bar'}), "bar")
        self.assertEqual(
            fallback_build_value_passthrough({'bar': 'baz'}), "baz")
        self.assertRaises(ConfigError, fallback_build_value_passthrough, {})
        self.assertRaises(
            ConfigError, fallback_build_value_passthrough, {'a': 1, 'b': 2})

    def test_build_value_default_callback(self):
        class ConfigWithFallback(Config):
            field = ConfigText("field", required=True)

        fallback = FieldFallback(['field'])
        config = ConfigWithFallback({'field': 'foo'})
        self.assertEqual(fallback.build_value(config), "foo")

    def test_build_value_custom_callback(self):
        class ConfigWithFallback(Config):
            host = ConfigText("host", required=True)
            port = ConfigInt("port", required=True)

        def fallback_host_port(fields):
            return "%(host)s:%(port)s" % fields

        fallback = FieldFallback(['host', 'port'], fallback_host_port)
        config = ConfigWithFallback({'host': 'example.com', 'port': 8080})
        self.assertEqual(fallback.build_value(config), "example.com:8080")

    def test_field_uses_required_fallback(self):
        class ConfigWithFallback(Config):
            oldfield = ConfigText(
                "oldfield", required=False, required_fallback=True)
            newfield = ConfigText(
                "newfield", required=True,
                fallbacks=[FieldFallback(["oldfield"])])

        config = ConfigWithFallback({"oldfield": "foo"})
        self.assertEqual(config.newfield, "foo")

    def test_field_ignores_unnecessary_fallback(self):
        class ConfigWithFallback(Config):
            oldfield = ConfigText(
                "oldfield", required=False, required_fallback=True)
            newfield = ConfigText(
                "newfield", required=True,
                fallbacks=[FieldFallback(["oldfield"])])

        config = ConfigWithFallback({"oldfield": "foo", "newfield": "bar"})
        self.assertEqual(config.newfield, "bar")

    def test_field_present_if_fallback_present(self):
        class ConfigWithFallback(Config):
            oldfield = ConfigText(
                "oldfield", required=False, required_fallback=True)
            newfield = ConfigText(
                "newfield", required=True,
                fallbacks=[FieldFallback(["oldfield"])])

        config = ConfigWithFallback({"oldfield": "foo"})
        self.assertEqual(ConfigWithFallback.newfield.present(config), True)

    def test_field_not_present_if_fallback_missing(self):
        class ConfigWithFallback(Config):
            oldfield = ConfigText(
                "oldfield", required=False, required_fallback=True)
            newfield = ConfigText(
                "newfield", required=False,
                fallbacks=[FieldFallback(["oldfield"])])

        config = ConfigWithFallback({})
        self.assertEqual(ConfigWithFallback.newfield.present(config), False)
