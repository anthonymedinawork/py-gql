# -*- coding: utf-8 -*-
""" Build an executable schema from an parsed SDL file. """

import collections

import six

from .. import schema as _schema
from ..exc import SDLError
from ..lang import ast as _ast, parse
from ..schema.directives import DeprecatedDirective
from ..schema.scalars import SPECIFIED_SCALAR_TYPES, DefaultCustomScalar
from ..utilities import typed_value_from_ast, directive_arguments


def schema_from_ast(ast, resolvers=None, known_types=None):  # noqa
    """ Build a valid schema from a parsed AST

    The schema is validate at the end to ensure not invalid schema gets created.

    :type ast: py_gql.lang.ast.Document|str
    :param ast: Parse AST

    :type resolvers: dict|callable
    :param resolvers: Used to infer field resolvers
        If a `dict` is provided, this looks for the resolver at key
        `{type_name}.{field_name}`. If a callable is provided, this calls
        it with the `{type_name}.{field_name}` argument and use the return value
        if it is callable.

    :type known_types: dict
    :param known_types: User supplied dictionnary of known types
        Use this to specify some custom implementation for scalar, enums, etc.
        WARN: In case of object types, interfaces, etc. the supplied type will
        override the extracted type without checking.

    WARN: Type extensions are ~~not supported yet~~ partially supported:
        - Supported: InterfaceType, ObjectType, UnionType, EnumType, InputTypeExtension
        - Not supported (silently ignored): ScalarTypeExtension

    WARN: Directives on type definitions and extensions are not suported yet

    WARN: Doesn't support comments-based description
    """

    if isinstance(ast, six.string_types):
        ast = parse(ast, allow_type_system=True)

    # First pass = parse and extract relevant informaton
    schema_definition, type_nodes, extension_nodes, directive_nodes = _extract_type(
        ast.definitions
    )

    # Second pass = translate types in schema object
    builder = _TypeMapBuilder(type_nodes, extension_nodes, known_types)
    types = builder()
    directives = builder.build_directives(directive_nodes)
    operation_types = _operation_types(schema_definition, types)

    for type in types.values():
        if isinstance(type, _schema.ObjectType):
            for field in type.fields:
                field.resolve = field.resolve or _infer_resolver(
                    resolvers, type.name, field.name
                )

    schema = _schema.Schema(
        query_type=operation_types.get("query"),
        mutation_type=operation_types.get("mutation"),
        subscription_type=operation_types.get("subscription"),
        types=types.values(),
        directives=directives.values(),
    )

    assert schema.validate()
    return schema


def _extract_type(definitions):
    schema_definition = None
    types = {}
    extensions = collections.defaultdict(list)
    directives = {}

    for definition in definitions:
        if isinstance(definition, _ast.SchemaDefinition):
            if schema_definition is not None:
                raise SDLError("Must provide only one schema definition", [definition])
            schema_definition = definition

        elif isinstance(definition, _ast.TypeDefinition):
            if definition.name.value in types:
                raise SDLError(
                    "Duplicate type %s" % definition.name.value, [definition]
                )
            types[definition.name.value] = definition

        elif isinstance(definition, _ast.TypeExtension):
            extensions[definition.name.value].append(definition)

        elif isinstance(definition, _ast.DirectiveDefinition):
            if definition.name.value in directives:
                raise SDLError(
                    "Duplicate directive @%s" % definition.name.value, [definition]
                )
            directives[definition.name.value] = definition

    return schema_definition, types, extensions, directives


def _operation_types(schema_definition, type_map):
    if schema_definition is None:
        return {
            k: type_map.get(k.capitalize(), None)
            for k in ("query", "mutation", "subscription")
        }
    else:
        operation_types = {}
        for opdef in schema_definition.operation_types:
            type_name = opdef.type.name.value
            op = opdef.operation
            if op in operation_types:
                raise SDLError(
                    "Can only define one %s in schema" % op, [schema_definition, opdef]
                )
            if type_name not in type_map:
                raise SDLError(
                    "%s type %s not found in document"
                    % (op, type_name),
                    [schema_definition, opdef],
                )
            operation_types[op] = type_map[type_name]
        return operation_types


class _TypeMapBuilder(object):
    def __init__(self, type_nodes, extension_nodes, known_types=None):
        self._type_nodes = type_nodes
        self._extension_nodes = extension_nodes
        self._cache = {}
        self._stack = []

        for type in known_types or []:
            self._cache[type.name] = type

        for type in SPECIFIED_SCALAR_TYPES:
            self._cache[type.name] = type

    def __call__(self):
        return {type.name: type for type in self.build_types(self._type_nodes.values())}

    def build_directives(self, directive_defs):
        return {
            directive_def.name.value: self.build_directive(directive_def)
            for directive_def in directive_defs.values()
        }

    def ref(self, type_name):
        return lambda: self._cache[type_name]

    def build_directive(self, node):
        return _schema.Directive(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            locations=[loc.value for loc in node.locations],
            args=(
                [self.argument(arg) for arg in node.arguments]
                if node.arguments
                else None
            ),
        )

    def build_types(self, type_nodes):
        return [self.build_type(type_node) for type_node in type_nodes]

    def build_type(self, type_node):
        if isinstance(type_node, _ast.ListType):
            return _schema.ListType(self.build_type(type_node.type))

        if isinstance(type_node, _ast.NonNullType):
            return _schema.NonNullType(self.build_type(type_node.type))

        type_name = type_node.name.value

        if type_name in self._cache:
            return self._cache[type_name]

        self._stack.append(type_name)

        if isinstance(type_node, _ast.NamedType):
            type_def = self._type_nodes.get(type_name)
            if type_def is None:
                raise SDLError("Type %s not found in document" % type_name, type_node)
            if type_name in self._stack:
                # Leverage the ususal lazy evaluation of fields and types
                # to prevent recursion issues
                return self.ref(type_name)
            self._cache[type_name] = self.build_type(type_def)
        elif isinstance(type_node, _ast.TypeDefinition):
            self._cache[type_name] = self.type_from_definition(type_node)
        else:
            raise TypeError(type(type_node))

        self._stack.pop()
        return self._cache[type_name]

    def type_from_definition(self, type_def):
        if isinstance(type_def, _ast.ObjectTypeDefinition):
            return self.object_type(type_def)
        if isinstance(type_def, _ast.InterfaceTypeDefinition):
            return self.interface_type(type_def)
        if isinstance(type_def, _ast.EnumTypeDefinition):
            return self.enum_type(type_def)
        if isinstance(type_def, _ast.UnionTypeDefinition):
            return self.union_type(type_def)
        if isinstance(type_def, _ast.ScalarTypeDefinition):
            return self.scalar_type(type_def)
        if isinstance(type_def, _ast.InputObjectTypeDefinition):
            return self.input_object_type(type_def)

    def object_type(self, node):
        t = _schema.ObjectType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            fields=[self.object_field(field_node) for field_node in node.fields],
            interfaces=(
                [self.build_type(iface) for iface in node.interfaces]
                if node.interfaces
                else None
            ),
        )
        for ext in self._extension_nodes[t.name]:
            if not isinstance(ext, _ast.ObjectTypeExtension):
                raise SDLError(
                    "Expected an ObjectTypeExtension node for ObjectType %s" % t.name,
                    [node],
                )
            t.fields.extend(
                [self.object_field(field_node) for field_node in ext.fields]
            )
            t.interfaces.extend(
                [self.build_type(iface) for iface in ext.interfaces]
                if ext.interfaces
                else None
            )
        return t

    def interface_type(self, node):
        t = _schema.InterfaceType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            fields=[self.object_field(field_node) for field_node in node.fields],
        )
        for ext in self._extension_nodes[t.name]:
            if not isinstance(ext, _ast.InterfaceTypeExtension):
                raise SDLError(
                    "Expected an InterfaceTypeExtension node for InterfaceType %s"
                    % t.name,
                    [node],
                )
            t.fields.extend(
                [self.object_field(field_node) for field_node in ext.fields]
            )
        return t

    def object_field(self, node):
        return _schema.Field(
            node.name.value,
            self.build_type(node.type),
            description=(node.description.value if node.description else None),
            args=(
                [self.argument(arg) for arg in node.arguments]
                if node.arguments
                else None
            ),
            deprecation_reason=_deprecation_reason(node),
        )

    def argument(self, node):
        type = self.build_type(node.type)
        kwargs = dict(
            description=(node.description.value if node.description else None)
        )
        if node.default_value is not None:
            kwargs["default_value"] = typed_value_from_ast(node.default_value, type)

        return _schema.Argument(node.name.value, type, **kwargs)

    def enum_type(self, node):
        values = [self.enum_value(v) for v in node.values]
        name = node.name.value
        for ext in self._extension_nodes[name]:
            if not isinstance(ext, _ast.UnionTypeExtension):
                raise SDLError(
                    "Expected an UnionTypeExtension node for UnionType %s" % name,
                    [node],
                )
            values.extend([self.enum_value(v) for v in ext.values])
        return _schema.EnumType(
            name=name,
            description=(node.description.value if node.description else None),
            values=values,
        )

    def enum_value(self, node):
        return _schema.EnumValue(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            value=node.name.value,
            deprecation_reason=_deprecation_reason(node),
        )

    def union_type(self, node):
        t = _schema.UnionType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            types=[self.build_type(type) for type in node.types],
        )
        for ext in self._extension_nodes[t.name]:
            if not isinstance(ext, _ast.UnionTypeExtension):
                raise SDLError(
                    "Expected an UnionTypeExtension node for UnionType %s" % t.name,
                    [node],
                )
            t.types.extend([self.build_type(type) for type in ext.types])
        return t

    def scalar_type(self, node):
        return DefaultCustomScalar(
            name=node.name.value,
            description=(node.description.value if node.description else None),
        )

    def input_object_type(self, node):
        return _schema.InputObjectType(
            name=node.name.value,
            description=(node.description.value if node.description else None),
            fields=[self.input_field(field_node) for field_node in node.fields],
        )

    def input_field(self, node):
        type = self.build_type(node.type)
        kwargs = dict(
            description=(node.description.value if node.description else None)
        )
        if node.default_value is not None:
            kwargs["default_value"] = typed_value_from_ast(node.default_value, type)

        return _schema.InputField(node.name.value, type, **kwargs)


def _deprecation_reason(node):
    args = directive_arguments(DeprecatedDirective, node, {})
    return args.get("reason") if args else None


def _infer_resolver(resolvers, type_name, field_name):
    if callable(resolvers):
        return resolvers(type_name, field_name)
    elif isinstance(resolvers, dict):
        return resolvers.get("%s.%s" % (type_name, field_name))
    return None
