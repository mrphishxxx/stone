from __future__ import absolute_import, division, print_function, unicode_literals

import pprint

from stone.data_type import (
    Boolean,
    Bytes,
    Float32,
    Float64,
    Int32,
    Int64,
    List,
    String,
    Timestamp,
    UInt32,
    UInt64,
    Void,
    is_alias,
    is_boolean_type,
    is_float_type,
    is_list_type,
    is_numeric_type,
    is_string_type,
    is_struct_type,
    is_timestamp_type,
    is_tag_ref,
    is_union_type,
    is_user_defined_type,
    is_void_type,
    unwrap_nullable,
)
from .helpers import split_words

# This file defines *stylistic* choices for Swift
# (ie, that class names are UpperCamelCase and that variables are lowerCamelCase)


_primitive_table = {
    Boolean: 'NSNumber *',
    Bytes: 'NSData',
    Float32: 'NSNumber *',
    Float64: 'NSNumber *',
    Int32: 'NSNumber *',
    Int64: 'NSNumber *',
    List: 'NSArray',
    String: 'NSString *',
    Timestamp: 'NSDate *',
    UInt32: 'NSNumber *',
    UInt64: 'NSNumber *',
    Void: 'void',
}


_serial_table = {
    Boolean: 'DbxBoolSerializer',
    Bytes: 'DbxNSDataSerializer',
    Float32: 'DbxNSNumberSerializer',
    Float64: 'DbxNSNumberSerializer',
    Int32: 'DbxNSNumberSerializer',
    Int64: 'DbxNSNumberSerializer',
    List: 'DbxArraySerializer',
    String: 'DbxStringSerializer',
    Timestamp: 'DbxNSDateSerializer',
    UInt32: 'DbxNSNumberSerializer',
    UInt64: 'DbxNSNumberSerializer',
}


_validator_table = {
    Float32: 'numericValidator',
    Float64: 'numericValidator',
    Int32: 'numericValidator',
    Int64: 'numericValidator',
    List: 'arrayValidator',
    String: 'stringValidator',
    UInt32: 'numericValidator',
    UInt64: 'numericValidator',
}


_wrapper_primitives = {
    Boolean,
    Float32,
    Float64,
    UInt32,
    UInt64,
    Int32,
    Int64,
    String,
}


_reserved_words = {
    'auto',
    'else',
    'long',
    'switch',
    'break',
    'enum',
    'register',
    'typedef',
    'case',
    'extern',
    'return',
    'union',
    'char',
    'float',
    'short',
    'unsigned',
    'const',
    'for',
    'signed',
    'void',
    'continue',
    'goto',
    'sizeof',
    'volatile',
    'default',
    'if',
    'static',
    'while',
    'do',
    'int',
    'struct',
    '_Packed',
    'double',
    'protocol',
    'interface',
    'implementation',
    'NSObject',
    'NSInteger',
    'NSNumber',
    'CGFloat',
    'property',
    'nonatomic',
    'retain',
    'strong',
    'weak',
    'unsafe_unretained',
    'readwrite',
    'description',
    'id',
}


_reserved_prefixes = {
    'copy',
    'new',
}


def fmt_obj(o):
    assert not isinstance(o, dict), "Only use for base type literals"
    if o is True:
        return 'true'
    if o is False:
        return 'false'
    if o is None:
        return 'nil'
    return pprint.pformat(o, width=1)


def fmt_camel(name, upper_first=False, reserved=True, prefixes=False):
    name = str(name)
    words = [word.capitalize() for word in split_words(name)]
    if not upper_first:
        words[0] = words[0].lower()
    ret = ''.join(words)

    if reserved:
        if ret.lower() in _reserved_words:
            ret += '_'
        # properties can't begin with certain keywords
        for reserved_prefix in _reserved_prefixes:
            if ret.lower().startswith(reserved_prefix):
                new_prefix = 'the' if not upper_first else 'The'
                ret = new_prefix + ret[0].upper() + ret[1:]
                continue
    return ret

def fmt_enum_name(field_name, union):
    return '{}{}{}'.format(fmt_camel_upper(union.namespace.name),
                           fmt_camel_upper(union.name),
                           fmt_camel_upper(field_name))

def fmt_camel_upper(name, reserved=True):
    return fmt_camel(name, upper_first=True, reserved=reserved)


def fmt_public_name(name):
    return fmt_camel_upper(name)


def fmt_class(name):
    return fmt_camel_upper(name)


def fmt_class_type(data_type):
    data_type, nullable = unwrap_nullable(data_type)

    if is_user_defined_type(data_type):
        result = '{}'.format(fmt_class_prefix(data_type))
    else:
        result = _primitive_table.get(data_type.__class__, fmt_class(data_type.name))
        
        if is_list_type(data_type):
            data_type, _ = unwrap_nullable(data_type.data_type)
            result = result + '<{}>'.format(fmt_type(data_type))

    return result 


def fmt_func(name):
    return fmt_camel(name)


def fmt_type(data_type, tag=False, has_default=False):
    data_type, nullable = unwrap_nullable(data_type)

    if is_user_defined_type(data_type):
        result = '{} *'.format(fmt_class_prefix(data_type))
    else:
        result = _primitive_table.get(data_type.__class__, fmt_class(data_type.name))
        
        if is_list_type(data_type):
            data_type, _ = unwrap_nullable(data_type.data_type)
            result = result + '<{}> *'.format(fmt_type(data_type)) 
    
    if tag:
        if nullable or has_default:
            result += ' _Nullable'
        elif not is_void_type(data_type):
            result += ' _Nonnull'

    return result


def fmt_class_prefix(data_type):
    return 'Dbx{}{}'.format(fmt_class(data_type.namespace.name),
                            fmt_class(data_type.name))


def fmt_validator(data_type):
    return _validator_table.get(data_type.__class__, fmt_class(data_type.name))


def fmt_serial_obj(data_type):
    data_type, nullable = unwrap_nullable(data_type)

    if is_user_defined_type(data_type):
        result = fmt_serial_class(fmt_class_prefix(data_type))
    else:
        result = _serial_table.get(data_type.__class__, fmt_class(data_type.name))

    return result


def fmt_serial_class(class_name):
    return '{}Serializer'.format(class_name)


def fmt_route_obj_class(namespace_name):
    return 'Dbx{}RouteObjects'.format(fmt_camel_upper(namespace_name))


def fmt_routes_class(namespace_name):
    return 'Dbx{}Routes'.format(fmt_class(namespace_name))


def fmt_route_var(namespace_name, route_name):
    return 'dbx{}{}'.format(fmt_camel_upper(namespace_name), fmt_camel_upper(route_name))


def fmt_func_args(arg_str_pairs):
    result = []
    first_arg = True
    for arg_name, arg_value in arg_str_pairs:
        if first_arg:
            result.append('{}'.format(arg_value))
            first_arg = False
        else:
            result.append('{}:{}'.format(arg_name, arg_value))
    return ' '.join(result)


def fmt_func_args_declaration(arg_str_pairs):
    result = []
    first_arg = True
    for arg_name, arg_type in arg_str_pairs:
        if first_arg:
            result.append('({}){}'.format(arg_type, arg_name))
            first_arg = False
        else:
            result.append('{}:({}){}'.format(arg_name, arg_type, arg_name))
    return ' '.join(result)


def fmt_func_args_from_fields(args):
    result = []
    first_arg = True
    for arg in args:
        if first_arg:
            result.append('({}){}'.format(fmt_type(arg.data_type), fmt_var(arg.name)))
            first_arg = False
        else:
            result.append('{}:({}){}'.format(fmt_var(arg.name), fmt_type(arg.data_type), fmt_var(arg.name)))
    return ' '.join(result)


def fmt_func_call(caller, callee, args=None):
    if args:
        result = '[{} {}:{}]'.format(caller, callee, args)
    else:
        result = '[{} {}]'.format(caller, callee)

    return result

def fmt_alloc_call(caller):
    return '[{} alloc]'.format(caller)


def fmt_default_value(field):
    if is_tag_ref(field.default):
        return '[[{} alloc] initWith{}]'.format(
            fmt_class_prefix(field.default.union_data_type),
            fmt_class(field.default.tag_name))
    elif is_numeric_type(field.data_type):
        return '[NSNumber numberWithInt:{}]'.format(field.default)
    elif is_boolean_type(field.data_type):
        if field.default:
            bool_str = 'YES'
        else:
            bool_str = 'NO'
        return '@{}'.format(bool_str)
    else:
        raise TypeError('Can\'t handle default value type %r' % type(field.data_type))


def fmt_signature(func, args, return_type='void', class_func=False):
    modifier = '-' if not class_func else '+'
    if args:
        result = '{} ({}){}:{}'.format(modifier, return_type, func, args)
    else:
        result = '{} ({}){}'.format(modifier, return_type, func)

    return result


def is_primitive_type(data_type):
    data_type, _ = unwrap_nullable(data_type)
    return data_type.__class__ in _wrapper_primitives


def fmt_var(name):
    return fmt_camel(name)


def fmt_property(field):
    attrs = ['nonatomic']
    if is_primitive_type(field.data_type):
        attrs.append('copy')
    base_string = '@property ({}) {} {};'

    return base_string.format(', '.join(attrs), fmt_type(field.data_type, tag=True), fmt_var(field.name))


def fmt_import(header_file):
    return '#import "{}.h"'.format(header_file)


def fmt_property_str(prop, typ, attrs=None):
    if not attrs:
        attrs = ['nonatomic']
    base_string = '@property ({}) {} {};'
    return base_string.format(', '.join(attrs), typ, prop)


def is_ptr_type(data_type):
    data_type, _ = unwrap_nullable(data_type)
    if data_type.__class__ in _true_primitives:
        type_name = 'NSInteger'
    type_name = _primitive_table.get(data_type.__class__, fmt_class(data_type.name))
    return type_name[-1] == '*' or is_struct_type(data_type) or is_list_type(data_type)