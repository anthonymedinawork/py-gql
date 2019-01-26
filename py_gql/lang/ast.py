# -*- coding: utf-8 -*-
""" GraphQL AST representations corresponding to the `GraphQL language elements`_.

 .. _GraphQL language elements:
   http://facebook.github.io/graphql/June2018/#sec-Language/#sec-Language
"""
# pylint: disable=redefined-builtin

import copy
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union, cast


class Node(object):
    """ Base AST node.

    - All subclasses should implement ``__slots__`` so ``__eq__`` and
      ``__repr__``, ``__copy__``, ``__deepcopy__`` and :meth:`to_dict` can work.
    - The ``source`` attribute is ignored for comparisons and serialization.
    """

    __slots__ = ("source", "loc")

    source: Optional[str]
    loc: Optional[Tuple[int, int]]

    def _props(self) -> Iterator[str]:
        attr: str
        for attr in self.__slots__:
            if attr != "source":
                yield attr

    def __eq__(self, rhs: Any) -> bool:
        return type(rhs) == type(self) and all(
            getattr(self, attr) == getattr(rhs, attr) for attr in self._props()
        )

    def __hash__(self) -> int:
        return id(self)

    def __repr__(self) -> str:
        return "<%s %s>" % (
            self.__class__.__name__,
            ", ".join(
                "%s=%s" % (attr, getattr(self, attr)) for attr in self._props()
            ),
        )

    def __getitem__(self, key, default=None):
        if key not in self.__slots__:
            raise KeyError(key)
        return getattr(self, key, default)

    def __copy__(self):
        return self.__class__(**{k: getattr(self, k) for k in self.__slots__})

    def __deepcopy__(self, memo):
        return self.__class__(
            **{k: copy.deepcopy(getattr(self, k), memo) for k in self.__slots__}
        )

    def to_dict(self):
        """ Convert the current node to a JSON serializable ``dict`` using
        :func:`node_to_dict`.

        Returns:
            dict: Converted value
        """
        return node_to_dict(self)


class Name(Node):
    __slots__ = ("source", "loc", "value")

    def __init__(
        self,
        value: str,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.value = value
        self.source = source
        self.loc = loc


class Definition(Node):
    pass


class ExecutableDefinition(Definition):
    pass


class Value(Node):
    pass


class Type(Node):
    pass


class SupportDirectives(object):
    directives: List["Directive"]


class NamedType(Type):
    __slots__ = ("source", "loc", "name")

    def __init__(
        self,
        name: Name,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.source = source
        self.loc = loc


class ListType(Type):
    __slots__ = ("source", "loc", "type")

    def __init__(
        self,
        type: Type,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.type = type
        self.source = source
        self.loc = loc


class NonNullType(Type):
    __slots__ = ("source", "loc", "type")

    def __init__(
        self,
        type: Type,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.type = type
        self.source = source
        self.loc = loc


class Document(Node):
    __slots__ = ("source", "loc", "definitions")

    def __init__(
        self,
        definitions: Optional[List[Definition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.definitions: List[Definition] = definitions or []
        self.source = source
        self.loc = loc


class OperationDefinition(SupportDirectives, ExecutableDefinition):
    __slots__ = (
        "source",
        "loc",
        "operation",
        "name",
        "variable_definitions",
        "directives",
        "selection_set",
    )

    def __init__(
        self,
        operation: str,
        selection_set,  # type: SelectionSet
        name: Optional[Name] = None,
        variable_definitions=None,  # type: Optional[List[VariableDefinition]]
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.operation = operation
        self.name = name
        self.selection_set = selection_set
        self.variable_definitions: List[
            VariableDefinition
        ] = variable_definitions or []
        self.directives: List[Directive] = directives or []
        self.source = source
        self.loc = loc


class Variable(Node):
    __slots__ = ("source", "loc", "name")

    def __init__(
        self,
        name: Name,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.source = source
        self.loc = loc


class VariableDefinition(Node):
    __slots__ = ("source", "loc", "variable", "type", "default_value")

    def __init__(
        self,
        variable: Variable,
        type: Type,
        default_value=None,  # type: Optional[Value]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.variable = variable
        self.type = type
        self.default_value = default_value
        self.source = source
        self.loc = loc


class Selection(Node):
    pass


class SelectionSet(Node):
    __slots__ = ("source", "loc", "selections")

    def __init__(
        self,
        selections: Optional[List[Selection]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.selections: List[Selection] = selections or []
        self.source = source
        self.loc = loc


class Field(SupportDirectives, Selection):
    __slots__ = (
        "source",
        "loc",
        "name",
        "alias",
        "arguments",
        "directives",
        "selection_set",
        "response_name",
    )

    def __init__(
        self,
        name: Name,
        alias: Optional[Name] = None,
        arguments=None,  # type: Optional[List[Argument]]
        directives=None,  # type: Optional[List[Directive]]
        selection_set: Optional[SelectionSet] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.alias = alias
        self.name = name
        self.arguments: List[Argument] = arguments or []
        self.directives: List[Directive] = directives or []
        self.selection_set = selection_set
        self.source = source
        self.loc = loc
        self.response_name = alias.value if alias else name.value


class Argument(Node):
    __slots__ = ("source", "loc", "name", "value")

    def __init__(
        self,
        name: Name,
        value: Union[Value, Variable],
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.value = value
        self.source = source
        self.loc = loc


class FragmentSpread(SupportDirectives, Selection):
    __slots__ = ("source", "loc", "name", "directives")

    def __init__(
        self,
        name: Name,
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.source = source
        self.loc = loc


class InlineFragment(SupportDirectives, Selection):
    __slots__ = (
        "source",
        "loc",
        "type_condition",
        "directives",
        "selection_set",
    )

    def __init__(
        self,
        selection_set: SelectionSet,
        type_condition: Optional[Type] = None,
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.type_condition = type_condition
        self.directives: List[Directive] = directives or []
        self.selection_set = selection_set
        self.source = source
        self.loc = loc


class FragmentDefinition(SupportDirectives, ExecutableDefinition):
    __slots__ = (
        "loc",
        "name",
        "variable_definitions",
        "type_condition",
        "directives",
        "selection_set",
    )

    def __init__(
        self,
        name: Name,
        type_condition: NamedType,
        selection_set: SelectionSet,
        variable_definitions: Optional[List[VariableDefinition]] = None,
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.variable_definitions: List[
            VariableDefinition
        ] = variable_definitions or []
        self.type_condition = type_condition
        self.directives: List[Directive] = directives or []
        self.selection_set = selection_set
        self.source = source
        self.loc = loc


class _StringValue(Value):
    __slots__ = ("source", "loc", "value")

    def __init__(
        self,
        value: str,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.value = value
        self.source = source
        self.loc = loc

    def __str__(self):
        return str(self.value)


class IntValue(_StringValue):
    pass


class FloatValue(_StringValue):
    pass


class StringValue(Value):
    __slots__ = ("source", "loc", "value", "block")

    def __init__(
        self,
        value: str,
        block: bool = False,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.value = value
        self.block = block
        self.source = source
        self.loc = loc

    def __str__(self):
        if self.block:
            return '"""%s"""' % self.value
        else:
            return '"%s"' % self.value


class BooleanValue(Value):
    __slots__ = ("source", "loc", "value")

    def __init__(
        self,
        value: bool,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.value = value
        self.source = source
        self.loc = loc

    def __str__(self):
        return str(self.value).lower()


class NullValue(Value):
    __slots__ = ("source", "loc")

    def __init__(
        self,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.source = source
        self.loc = loc

    def __str__(self):
        return "null"


class EnumValue(_StringValue):
    pass


class ListValue(Value):
    __slots__ = ("source", "loc", "values")

    def __init__(
        self,
        values: List[Union[Value, Variable]],
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.values = values
        self.source = source
        self.loc = loc


class ObjectValue(Value):
    __slots__ = ("source", "loc", "fields")

    def __init__(
        self,
        fields,  # type: List[ObjectField]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.fields = fields or []
        self.source = source
        self.loc = loc


class ObjectField(Node):
    __slots__ = ("source", "loc", "name", "value")

    def __init__(
        self,
        name: Name,
        value: Value,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.value = value
        self.source = source
        self.loc = loc


class Directive(Node):
    __slots__ = ("source", "loc", "name", "arguments")

    def __init__(
        self,
        name: Name,
        arguments: Optional[List[Argument]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.arguments: List[Argument] = arguments or []
        self.source = source
        self.loc = loc


class SupportDescription(object):
    description: Optional[StringValue]


class TypeSystemDefinition(SupportDirectives, Definition):
    pass


class SchemaDefinition(TypeSystemDefinition):
    __slots__ = ("source", "loc", "directives", "operation_types")

    def __init__(
        self,
        directives: Optional[List[Directive]] = None,
        operation_types=None,  # type: Optional[List[OperationTypeDefinition]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.directives: List[Directive] = directives or []
        self.operation_types: List[
            OperationTypeDefinition
        ] = operation_types or []
        self.source = source
        self.loc = loc


class OperationTypeDefinition(Node):
    __slots__ = ("source", "loc", "operation", "type")

    def __init__(
        self,
        operation: str,
        type: NamedType,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.operation = operation
        self.type = type
        self.source = source
        self.loc = loc


class TypeDefinition(SupportDescription, TypeSystemDefinition):
    name: Name


class ScalarTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.source = source
        self.loc = loc
        self.description = description


class ObjectTypeDefinition(TypeDefinition):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "interfaces",
        "directives",
        "fields",
    )

    def __init__(
        self,
        name: Name,
        interfaces: Optional[List[NamedType]] = None,
        directives: Optional[List[Directive]] = None,
        fields=None,  # type: Optional[List[FieldDefinition]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.interfaces: List[NamedType] = interfaces or []
        self.directives: List[Directive] = directives or []
        self.fields: List[FieldDefinition] = fields or []
        self.source = source
        self.loc = loc
        self.description = description


class FieldDefinition(SupportDirectives, SupportDescription, Node):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "arguments",
        "type",
        "directives",
    )

    def __init__(
        self,
        name: Name,
        type: Type,
        arguments: Optional[List["InputValueDefinition"]] = None,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.arguments: List[InputValueDefinition] = arguments or []
        self.type = type
        self.directives: List[Directive] = directives or []
        self.source = source
        self.loc = loc
        self.description = description


class InputValueDefinition(SupportDirectives, SupportDescription, Node):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "type",
        "default_value",
        "directives",
    )

    def __init__(
        self,
        name: Name,
        type: Type,
        default_value: Optional[Value] = None,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.type = type
        self.default_value = default_value
        self.directives: List[Directive] = directives or []
        self.source = source
        self.loc = loc
        self.description = description


class InterfaceTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "fields")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        fields: Optional[List[FieldDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.fields: List[FieldDefinition] = fields or []
        self.source = source
        self.loc = loc
        self.description = description


class UnionTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "types")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        types: Optional[List[NamedType]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.types: List[NamedType] = types or []
        self.source = source
        self.loc = loc
        self.description = description


class EnumTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "values")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        values=None,  # type: Optional[List[EnumValueDefinition]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.values: List[EnumValueDefinition] = values or []
        self.source = source
        self.loc = loc
        self.description = description


class EnumValueDefinition(SupportDirectives, SupportDescription, Node):
    __slots__ = ("source", "loc", "description", "name", "directives")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.source = source
        self.loc = loc
        self.description = description


class InputObjectTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "fields")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        fields: Optional[List[InputValueDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.fields: List[InputValueDefinition] = fields or []
        self.source = source
        self.loc = loc
        self.description = description


class TypeSystemExtension(TypeSystemDefinition):
    pass


class SchemaExtension(TypeSystemExtension):
    __slots__ = ("source", "loc", "directives", "operation_types")

    def __init__(
        self,
        directives: Optional[List[Directive]] = None,
        operation_types: Optional[List[OperationTypeDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.directives: List[Directive] = directives or []
        self.operation_types: List[
            OperationTypeDefinition
        ] = operation_types or []
        self.source = source
        self.loc = loc


class TypeExtension(TypeSystemExtension):
    name: Name


class ScalarTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.source = source
        self.loc = loc


class ObjectTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "interfaces", "directives", "fields")

    def __init__(
        self,
        name: Name,
        interfaces: Optional[List[NamedType]] = None,
        directives: Optional[List[Directive]] = None,
        fields=None,  # type: Optional[List[FieldDefinition]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.interfaces: List[NamedType] = interfaces or []
        self.directives: List[Directive] = directives or []
        self.fields: List[FieldDefinition] = fields or []
        self.source = source
        self.loc = loc


class InterfaceTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "fields")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        fields: Optional[List[FieldDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.fields: List[FieldDefinition] = fields or []
        self.source = source
        self.loc = loc


class UnionTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "types")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        types: Optional[List[NamedType]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.types: List[NamedType] = types or []
        self.source = source
        self.loc = loc


class EnumTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "values")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        values: Optional[List[EnumValueDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.values: List[EnumValueDefinition] = values or []
        self.values = values or []
        self.source = source
        self.loc = loc


class InputObjectTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "fields")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        fields: Optional[List[InputValueDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives: List[Directive] = directives or []
        self.fields: List[InputValueDefinition] = fields or []
        self.source = source
        self.loc = loc


class DirectiveDefinition(SupportDescription, TypeSystemDefinition):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "arguments",
        "locations",
    )

    def __init__(
        self,
        name: Name,
        arguments: Optional[List[InputValueDefinition]] = None,
        locations: Optional[List[Name]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.arguments: List[InputValueDefinition] = arguments or []
        self.locations: List[Name] = locations or []
        self.source = source
        self.loc = loc
        self.description = description


def _node_to_dict(node):
    if isinstance(node, Node):
        return dict(
            {
                attr: _node_to_dict(getattr(node, attr))
                for attr in node._props()
            },
            __kind__=node.__class__.__name__,
        )
    elif isinstance(node, list):
        return [_node_to_dict(v) for v in node]
    else:
        return node


def node_to_dict(node: Node) -> Dict[str, Any]:
    """ Recrusively convert a ``py_gql.lang.ast.Node`` instance to a dict.

    This is mostly useful for testing and when you need to convert nodes to JSON
    such as interop with other languages, printing and serialisation.

    Nodes are converted based on their `__slots__` adding a `__kind__` key
    corresponding to the node class while primitive values are left as is.
    Lists are converted per-element.

    Argss:
        node (any): A :class:`Node` instance or any node attribute

    Returns:
        Converted value
    """
    return cast(Dict[str, Any], _node_to_dict(node))
