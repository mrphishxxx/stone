from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import json
import os
import re

from contextlib import contextmanager

from stone.data_type import (
    is_list_type,
    is_struct_type,
    is_timestamp_type,
    is_user_defined_type,
    is_union_type,
    is_void_type,
    unwrap_nullable,
)
from stone.target.obj_c_helpers import (
    fmt_alloc_call,
    fmt_camel,
    fmt_camel_upper,
    fmt_class,
    fmt_class_prefix,
    fmt_default,
    fmt_func,
    fmt_func_args,
    fmt_func_args_declaration,
    fmt_func_call,
    fmt_import,
    fmt_literal,
    fmt_property_str,
    fmt_public_name,
    fmt_serial_obj,
    fmt_signature,
    fmt_type,
    fmt_var,
    is_primitive_type,
    is_ptr_type,
)
from stone.target.obj_c import (
    base,
    comment_prefix,
    ObjCBaseGenerator,
    stone_warning,
    undocumented,
)

_cmdline_parser = argparse.ArgumentParser(
    prog='ObjC-test-generator',
    description=(
        'Generates unit tests for the Obj C SDK.'),
)


class ObjCTestGenerator(ObjCBaseGenerator):
    """Generates Xcode tests for Objective C SDK."""
    cmdline_parser = _cmdline_parser

    def generate(self, api):
        with self.output_to_relative_path('DbxSerializationTests.m'):
            self.emit_raw(base)
            self.emit('#import <XCTest/XCTest.h>')
            self.emit()
            self._generate_testing_imports(api)

            with self.block_h('DbxSerializationTests', extensions=['XCTestCase']):
                pass

            self.emit()
            self.emit()

            with self.block_m('DbxSerializationTests'):

                with self.block_func('checkError', fmt_func_args_declaration([('originalObj', 'id'), ('outputObj', 'id')])):
                    self.emit('NSAssert(([[originalObj description] isEqual:[outputObj description]]), @"\\nSerialization and deserialization failed to preserve object data:\\n\\nBefore:\\n %@ \\n\\nAfter:\\n %@.\\n\\n", originalObj, outputObj);')
                for namespace in api.namespaces.values():
                    self._generate_namespace_tests(namespace)

    def _generate_namespace_tests(self, namespace):
        ns_name = fmt_public_name(namespace.name)

        self.emit()
        self.emit('/// Serialization tests for the {} namespace.'.format(ns_name))
        self.emit()
        self.emit()
        for data_type in namespace.linearize_data_types():
            class_name = fmt_public_name(data_type.name)

            if is_struct_type(data_type):
                examples = data_type.get_examples()

                for example_type in examples:
                    test_name = 'testSerialize{}{}{}'.format(ns_name, class_name, fmt_camel_upper(example_type, reserved=False))
                    with self.block_func(test_name):
                        self.emit('/// Data from the "{}" example'.format(example_type))
                        example_data = examples[example_type].value

                        result = []



                        for field in data_type.all_fields:
                            field_data_type, nullable = unwrap_nullable(field.data_type)

                            # if ns_name+class_name == 'FilesUploadSessionFinishBatchResult' and example_type == 'default':
                            #     print(example_data)
                            #     print()
                            #     print()

                            field_name = fmt_var(field.name)

                            if field.name in example_data:
                                example_value = fmt_literal(example_data[field.name], field_data_type)
                                example_value = example_value.replace('\n', '')

                                if is_user_defined_type(field_data_type) or is_list_type(field_data_type) or is_timestamp_type(field_data_type):
                                    result.append((field_name, field_name))
                                else:
                                    result.append((field_name, example_value))

                                if is_user_defined_type(field_data_type):
                                    if is_struct_type(field_data_type) and field_data_type.has_enumerated_subtypes():
                                        for tags, subtype in field_data_type.get_all_subtypes_with_tags():
                                            assert len(tags) == 1, tags
                                            tag = tags[0]
                                            if tag == example_data[field.name]['.tag']:
                                                self.emit('{} *{} = {};'.format(fmt_class_prefix(subtype),
                                                    field_name, fmt_literal(example_data[field.name], subtype)))
                                    else:   
                                        self.emit('{} *{} = {};'.format(fmt_class_prefix(field_data_type),
                                            field_name, example_value))
                                elif is_list_type(field_data_type):
                                    self.emit('NSArray *{} = {};'.format(field_name, example_value))
                                elif is_timestamp_type(field_data_type):
                                    self.emit('NSDate *{} = {};'.format(field_name, example_value))
                            else:
                                if not is_void_type(field.data_type):
                                    result.append((field_name, fmt_default(field.data_type)))

                        args_str = fmt_func_args(result)



                        if '\n' not in args_str:
                            if fmt_class_prefix(data_type) == 'DbxFilesMetadata':
                                print(data_type)
                            if is_struct_type(data_type) and data_type.has_enumerated_subtypes():
                                for tags, subtype in data_type.get_all_subtypes_with_tags():
                                    assert len(tags) == 1, tags
                                    tag = tags[0]
                                    if tag == example_data['.tag']:
                                        self.emit('{} *obj = {};'.format(fmt_class_prefix(subtype), fmt_literal(example_data, subtype)))
                                        self.emit('NSData *serializedData = [DropboxTransportClient jsonDataWithDictionary:[{} serialize:obj]];'.format(fmt_class_prefix(subtype)))
                                        self.emit('id jsonObj = [NSJSONSerialization JSONObjectWithData:serializedData options:NSJSONReadingMutableContainers error:nil];')
                                        self.emit('{} *outputObj = [{} deserialize:jsonObj];'.format(fmt_class_prefix(subtype), fmt_class_prefix(subtype)))
                                        self.emit('[self checkError:obj outputObj:outputObj];')

                            else:   
                                self.emit('{} *obj = {};'.format(fmt_class_prefix(data_type), fmt_func_call(fmt_alloc_call(fmt_class_prefix(data_type)), self._cstor_name_from_fields_names(result), args_str)))
                                self.emit('NSData *serializedData = [DropboxTransportClient jsonDataWithDictionary:[{} serialize:obj]];'.format(fmt_class_prefix(data_type)))
                                self.emit('id jsonObj = [NSJSONSerialization JSONObjectWithData:serializedData options:NSJSONReadingMutableContainers error:nil];')
                                self.emit('{} *outputObj = [{} deserialize:jsonObj];'.format(fmt_class_prefix(data_type), fmt_class_prefix(data_type)))
                                self.emit('[self checkError:obj outputObj:outputObj];')
                    self.emit()
    
    def _field_type_from_field_name(self, field_name, data_type):
        

        return None

    def _generate_testing_imports(self, api):
        import_classes = ['DbxStoneSerializers', 'DropboxTransportClient']
        for namespace in api.namespaces.values():
            for data_type in namespace.linearize_data_types():
                import_classes.append(fmt_class_prefix(data_type))
        
        self._generate_imports_m(import_classes)
