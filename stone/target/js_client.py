from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import json
import six
import sys

from stone.data_type import (
    is_user_defined_type,
    unwrap,
)
from stone.generator import CodeGenerator
from stone.target.js_helpers import (
    fmt_func,
    fmt_obj,
    fmt_type,
)


_cmdline_parser = argparse.ArgumentParser(prog='js-client-generator')
_cmdline_parser.add_argument(
    'filename',
    help=('The name to give the single Javascript file that is created and '
          'contains all of the routes.'),
)
_cmdline_parser.add_argument(
    '-c',
    '--class-name',
    type=str,
    help=('The name of the class the generated functions will be attached to. '
          'The name will be added to each function documentation, which makes '
          'it available for tools like JSDoc.'),
)
_cmdline_parser.add_argument(
    '-e',
    '--extra-arg',
    action='append',
    type=str,
    default=[],
    help=("Additional argument to add to a route function's docstring based "
          "on if the route has a certain attribute set. Format (JSON): "
          '{"match": ["ROUTE_ATTR", ROUTE_VALUE_TO_MATCH], '
          '"arg_name": "ARG_NAME", "arg_type": "ARG_TYPE", '
          '"arg_docstring": "ARG_DOCSTRING"}'),
)

_header = """\
// Auto-generated by Stone, do not modify.
var routes = {};
"""


class JavascriptGenerator(CodeGenerator):
    """Generates a single Javascript file with all of the routes defined."""

    cmdline_parser = _cmdline_parser

    # Instance var of the current namespace being generated
    cur_namespace = None

    preserve_aliases = True

    def generate(self, api):
        with self.output_to_relative_path(self.args.filename):

            self.emit_raw(_header)

            extra_args = self._parse_extra_args(self.args.extra_arg)

            for namespace in api.namespaces.values():
                for route in namespace.routes:
                    self._generate_route(
                        api.route_schema, namespace, route, extra_args)

            self.emit()
            self.emit('module.exports = routes;')

    def _parse_extra_args(self, extra_args_raw):
        extra_args = {}

        for extra_arg_raw in extra_args_raw:
            def exit(m):
                print('Invalid --extra-arg:%s: %s' % (m, extra_arg_raw),
                      file=sys.stderr)
                sys.exit(1)

            try:
                extra_arg = json.loads(extra_arg_raw)
            except ValueError as e:
                exit(str(e))

            # Validate extra_arg JSON blob
            if 'match' not in extra_arg:
                exit('No match key')
            elif (not isinstance(extra_arg['match'], list) or
                      len(extra_arg['match']) != 2):
                exit('match key is not a list of two strings')
            elif (not isinstance(extra_arg['match'][0], six.text_type) or
                      not isinstance(extra_arg['match'][1], six.text_type)):
                print(type(extra_arg['match'][0]))
                exit('match values are not strings')
            elif 'arg_name' not in extra_arg:
                exit('No arg_name key')
            elif not isinstance(extra_arg['arg_name'], six.text_type):
                exit('arg_name is not a string')
            elif 'arg_type' not in extra_arg:
                exit('No arg_type key')
            elif not isinstance(extra_arg['arg_type'], six.text_type):
                exit('arg_type is not a string')
            elif ('arg_docstring' in extra_arg and
                      not isinstance(extra_arg['arg_docstring'], six.text_type)):
                exit('arg_docstring is not a string')

            attr_key, attr_val = extra_arg['match'][0], extra_arg['match'][1]
            extra_args.setdefault(attr_key, {})[attr_val] = \
                (extra_arg['arg_name'], extra_arg['arg_type'],
                 extra_arg.get('arg_docstring'))

        return extra_args

    def _generate_route(self, route_schema, namespace, route, extra_args):
        function_name = fmt_func(namespace.name + '_' + route.name)
        self.emit()
        self.emit('/**')
        if route.doc:
            self.emit_wrapped_text(self.process_doc(route.doc, self._docf), prefix=' * ')
        if self.args.class_name:
            self.emit(' * @function {}#{}'.format(self.args.class_name,
                                                  function_name))
        if route.deprecated:
            self.emit(' * @deprecated')

        self.emit(' * @arg {%s} arg - The request parameters.' %
                  fmt_type(route.arg_data_type))
        if is_user_defined_type(route.arg_data_type):
            for attr_key in route.attrs:
                if attr_key not in extra_args:
                    continue
                attr_val = route.attrs[attr_key]
                if attr_val in extra_args[attr_key]:
                    arg_name, arg_type, arg_docstring = extra_args[attr_key][attr_val]
                    field_docstring = '@arg {%s} arg.%s' % (arg_type, arg_name)
                    if arg_docstring:
                        field_docstring += ' - %s' % arg_docstring
                    self.emit_wrapped_text(field_docstring, prefix=' * ')

            for field in route.arg_data_type.all_fields:
                field_doc = ' - ' + field.doc if field.doc else ''
                field_type, nullable, _ = unwrap(field.data_type)
                field_js_type = fmt_type(field_type)
                if nullable:
                    field_js_type += '|null'
                self.emit_wrapped_text(
                    '@arg {%s} arg.%s%s' %
                        (field_js_type, field.name,
                         self.process_doc(field_doc, self._docf)),
                    prefix=' * ')
        self.emit(' * @returns {%s}' % fmt_type(route.result_data_type))
        self.emit(' */')
        self.emit('routes.%s = function (arg) {' % function_name)
        with self.indent(dent=2):
            url = '{}/{}'.format(namespace.name, route.name)
            if route_schema.fields:
                additional_args = []
                for field in route_schema.fields:
                    additional_args.append(fmt_obj(route.attrs[field.name]))
                self.emit(
                    "return this.request('{}', arg, {});".format(
                        url, ', '.join(additional_args)))
            else:
                self.emit(
                    'return this.request("%s", arg);' % url)
        self.emit('};')

    def _docf(self, tag, val):
        """
        Callback used as the handler argument to process_docs(). This converts
        Stone doc references to JSDoc-friendly annotations.
        """
        # TODO(kelkabany): We're currently just dropping all doc ref tags.
        return val
