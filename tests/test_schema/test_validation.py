# -*- coding: utf-8 -*-
""" Test schema validation """

from typing import List

import pytest

from py_gql.exc import SchemaError
from py_gql.schema import (
    Argument,
    EnumType,
    EnumValue,
    Field,
    GraphQLType,
    InputField,
    InputObjectType,
    Int,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    Schema,
    String,
    UnionType,
)
from py_gql.schema.validation import validate_schema

SomeScalar = ScalarType(
    "SomeScalar",
    serialize=lambda a: None,
    parse=lambda a: None,
    parse_literal=lambda a, **k: None,
)  # type: ScalarType[None]

SomeObject = ObjectType("SomeObject", [Field("f", String)])

IncompleteObject = ObjectType("IncompleteObject", [])

SomeUnion = UnionType("SomeUnion", [SomeObject])

SomeInterface = InterfaceType("SomeInterface", [Field("f", String)])

SomeEnum = EnumType("SomeEnum", [EnumValue("ONLY")])

SomeInputObject = InputObjectType(
    "SomeInputObject", [InputField("val", String, default_value="hello")]
)


def _type_modifiers(t):
    return [t, ListType(t), NonNullType(t), NonNullType(ListType(t))]


def _with_modifiers(types):
    out = []  # type: List[GraphQLType]
    for t in types:
        out.extend(_type_modifiers(t))
    return out


output_types = _with_modifiers(
    [String, SomeScalar, SomeEnum, SomeObject, SomeUnion, SomeInterface]
)

not_output_types = _with_modifiers([SomeInputObject])

input_types = _with_modifiers([String, SomeScalar, SomeEnum, SomeInputObject])

not_input_types = _with_modifiers([SomeObject, SomeUnion, SomeInterface])


def _single_type_schema(type_, fieldname="f"):
    return Schema(ObjectType("Query", [Field(fieldname, type_)]), types=[type_])


def test_query_type_is_an_object_type():
    schema = _single_type_schema(String, "test")
    assert schema.is_valid


def test_query_and_mutation_types_are_object_types():
    schema = Schema(
        ObjectType("Query", [Field("test", String)]),
        mutation_type=ObjectType("Mutation", [Field("test", String)]),
    )
    assert schema.is_valid


def test_query_and_subscription_types_are_object_types():
    schema = Schema(
        ObjectType("Query", [Field("test", String)]),
        subscription_type=ObjectType("Subscription", [Field("test", String)]),
    )
    assert schema.is_valid


def test_reject_non_object_query_type():
    schema = Schema(String)  # type: ignore

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert str(exc_info.value) == 'Query must be ObjectType but got "String"'


def test_reject_non_object_mutation_type():
    schema = Schema(  # type: ignore
        ObjectType("Query", [Field("test", String)]), mutation_type=String
    )

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert str(exc_info.value) == 'Mutation must be ObjectType but got "String"'


def test_reject_non_object_subscription_type():
    schema = Schema(  # type: ignore
        ObjectType("Query", [Field("test", String)]), subscription_type=String
    )

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Subscription must be ObjectType but got "String"'
    )


def test_reject_incorrectly_typed_directives():
    with pytest.raises(SchemaError) as exc_info:
        Schema(SomeObject, directives=["somedirective"])  # type: ignore

    assert "somedirective" in str(exc_info.value)
    assert "str" in str(exc_info.value)


def test_accept_object_type_with_fields_object():
    schema = _single_type_schema(SomeObject)
    assert schema.is_valid


def test_reject_object_without_fields():
    schema = _single_type_schema(IncompleteObject)
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Type "IncompleteObject" must define at least one field'
    )


def test_reject_object_with_incorrectly_named_fields():
    schema = Schema(
        ObjectType("Query", [Field("bad-name-with-dashes", String)])
    )

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value) == 'Invalid name "bad-name-with-dashes", '
        "must match /^[_a-zA-Z][_a-zA-Z0-9]*$/"
    )


def test_reject_incorrectly_named_type():
    schema = _single_type_schema(
        ObjectType("bad-name-with-dashes", [Field("field", String)])
    )

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value) == 'Invalid type name "bad-name-with-dashes", '
        "must match /^[_a-zA-Z][_a-zA-Z0-9]*$/"
    )


def test_accept_field_args_with_correct_names():
    schema = _single_type_schema(
        ObjectType(
            "SomeObject",
            [Field("field", String, [Argument("goodArg", String)])],
        )
    )
    assert schema.is_valid


def test_reject_field_args_with_incorrect_names():
    schema = _single_type_schema(
        ObjectType(
            "SomeObject",
            [Field("field", String, [Argument("bad-arg", String)])],
        )
    )

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Invalid name "bad-arg", must match /^[_a-zA-Z][_a-zA-Z0-9]*$/'
    )


def test_accept_union_type_with_valid_members():
    TypeA = ObjectType("TypeA", [Field("f", String)])
    TypeB = ObjectType("TypeB", [Field("f", String)])
    GoodUnion = UnionType("GoodUnion", [TypeA, TypeB])
    schema = _single_type_schema(GoodUnion)
    assert schema.is_valid


def test_reject_union_type_with_no_member():
    EmptyUnion = UnionType("EmptyUnion", [])
    schema = _single_type_schema(EmptyUnion)

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'UnionType "EmptyUnion" must at least define one member'
    )


def test_reject_union_type_with_duplicate_members():
    TypeA = ObjectType("TypeA", [Field("f", String)])
    BadUnion = UnionType("BadUnion", [TypeA, TypeA])
    schema = _single_type_schema(BadUnion)
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'UnionType "BadUnion" can only include type "TypeA" once'
    )


def test_reject_union_type_with_non_object_members():
    TypeA = ObjectType("TypeA", [Field("f", String)])
    BadUnion = UnionType("BadUnion", [TypeA, SomeScalar])  # type: ignore
    schema = _single_type_schema(BadUnion)
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'UnionType "BadUnion" expects object types but got "SomeScalar"'
    )


def test_accept_input_type():
    schema = _single_type_schema(
        ObjectType(
            "Object",
            [Field("field", String, [Argument("arg", SomeInputObject)])],
        )
    )
    assert schema.is_valid


def test_reject_input_type_with_no_fields():
    EmptyInput = InputObjectType("EmptyInput", [])
    schema = _single_type_schema(
        ObjectType(
            "Object", [Field("field", String, [Argument("arg", EmptyInput)])]
        )
    )

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Type "EmptyInput" must define at least one field'
    )


def test_reject_input_type_with_incorectly_typed_fields():
    BadInput = InputObjectType("BadInput", [InputField("f", SomeObject)])
    schema = _single_type_schema(
        ObjectType(
            "Object", [Field("field", String, [Argument("arg", BadInput)])]
        )
    )

    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Expected input type for field "f" on "BadInput" '
        'but got "SomeObject"'
    )


def test_reject_enum_type_with_no_values():
    schema = _single_type_schema(EnumType("EmptyEnum", []))
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'EnumType "EmptyEnum" must at least define one value'
    )


def test_reject_enum_value_with_incorrect_name():
    schema = _single_type_schema(EnumType("BadEnum", ["#value"]))
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Invalid name "#value", must match /^[_a-zA-Z][_a-zA-Z0-9]*$/'
    )


@pytest.mark.parametrize("type_", output_types, ids=lambda t: "type = %s" % t)
def test_accept_output_type_as_object_fields(type_):
    schema = _single_type_schema(type_)
    assert schema.is_valid


@pytest.mark.parametrize(
    "type_", not_output_types + [None], ids=lambda t: "type = %s" % t
)
def test_reject_non_output_type_as_object_fields(type_):
    schema = _single_type_schema(type_)
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Expected output type for field "f" on "Query" but got "%s"' % type_
    )


def test_reject_object_implementing_same_interface_twice():
    schema = _single_type_schema(
        ObjectType(
            "SomeObject",
            [Field("f", String)],
            interfaces=[SomeInterface, SomeInterface],
        )
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value) == 'Type "SomeObject" mut only implement interface '
        '"SomeInterface" once'
    )


@pytest.mark.parametrize("type_", output_types, ids=lambda t: "type = %s" % t)
def test_accept_interface_fields_with_output_type(type_):
    iface = InterfaceType("GoodInterface", [Field("f", type_)])
    schema = _single_type_schema(iface)
    assert schema.is_valid


@pytest.mark.parametrize(
    "type_", not_output_types + [None], ids=lambda t: "type = %s" % t
)
def test_reject_interface_fields_with_non_output_type(type_):
    iface = InterfaceType("BadInterface", [Field("f", type_)])
    schema = _single_type_schema(iface)
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Expected output type for field "f" on "BadInterface" '
        'but got "%s"' % type_
    )


def test_reject_interface_with_no_field():
    iface = InterfaceType("BadInterface", [])
    schema = _single_type_schema(iface)
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Type "BadInterface" must define at least one field'
    )


@pytest.mark.parametrize("type_", input_types, ids=lambda t: "type = %s" % t)
def test_accept_argument_with_input_type(type_):
    schema = _single_type_schema(
        ObjectType(
            "GoodObject", [Field("f", String, [Argument("goodArg", type_)])]
        )
    )
    assert schema.is_valid


@pytest.mark.parametrize(
    "type_", not_input_types + [None], ids=lambda t: "type = %s" % t
)
def test_reject_argument_with_non_input_type(type_):
    schema = _single_type_schema(
        ObjectType(
            "BadObject", [Field("f", String, [Argument("badArg", type_)])]
        )
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Expected input type for argument "badArg" on "BadObject.f" '
        'but got "%s"' % type_
    )


@pytest.mark.parametrize("type_", input_types, ids=lambda t: "type = %s" % t)
def test_accept_input_object_with_input_type(type_):
    schema = _single_type_schema(
        ObjectType(
            "GoodObject",
            [
                Field(
                    "f",
                    String,
                    [
                        Argument(
                            "goodArg",
                            InputObjectType(
                                "GoodInput", [InputField("f", type_)]
                            ),
                        )
                    ],
                )
            ],
        )
    )
    assert schema.is_valid


@pytest.mark.parametrize(
    "type_", not_input_types + [None], ids=lambda t: "type = %s" % t
)
def test_reject_input_object_with_non_input_type(type_):
    schema = _single_type_schema(
        ObjectType(
            "BadObject",
            [
                Field(
                    "f",
                    String,
                    [
                        Argument(
                            "badArg",
                            InputObjectType(
                                "BadInput", [InputField("f", type_)]
                            ),
                        )
                    ],
                )
            ],
        )
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Expected input type for field "f" on "BadInput" '
        'but got "%s"' % type_
    )


def test_reject_input_object_with_no_field():
    arg = Argument("badArg", InputObjectType("BadInput", []))
    schema = _single_type_schema(
        ObjectType("BadObject", [Field("f", String, [arg])])
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value) == 'Type "BadInput" must define at least one field'
    )


def test_accept_object_which_implements_interface():
    schema = _single_type_schema(
        ObjectType(
            "SomeObject", [Field("f", String)], interfaces=[SomeInterface]
        )
    )
    assert schema.is_valid


def test_accept_object_which_implements_interface_along_with_more_fields():
    schema = _single_type_schema(
        ObjectType(
            "SomeObject",
            [Field("f", String), Field("f2", String)],
            interfaces=[SomeInterface],
        )
    )
    assert schema.is_valid


def test_accept_object_which_implements_interface_along_with_nullable_args():
    schema = _single_type_schema(
        ObjectType(
            "SomeObject",
            [Field("f", String, [Argument("arg", String)])],
            interfaces=[SomeInterface],
        )
    )
    assert schema.is_valid


def test_reject_object_missing_interface_field():
    schema = _single_type_schema(
        ObjectType(
            "SomeObject", [Field("_f", String)], interfaces=[SomeInterface]
        )
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Interface field "SomeInterface.f" is not implemented '
        'by type "SomeObject"'
    )


def test_reject_object_with_incorrectly_typed_interface_field():
    schema = _single_type_schema(
        ObjectType("SomeObject", [Field("f", Int)], interfaces=[SomeInterface])
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Interface field "SomeInterface.f" expects type "String" '
        'but "SomeObject.f" is type "Int"'
    )


def test_accept_object_fields_with_interface_subtype_of_interface_field():
    iface = InterfaceType(
        "IFace", [Field("f", lambda: iface)]
    )  # type: InterfaceType
    obj = ObjectType(
        "Obj", [Field("f", lambda: obj)], interfaces=[iface]
    )  # type: ObjectType
    schema = _single_type_schema(obj)
    assert schema.is_valid


def test_accept_object_fields_with_union_subtype_of_interface_field():
    union = UnionType("union", [SomeObject])
    iface = InterfaceType("IFace", [Field("f", union)])
    obj = ObjectType("Obj", [Field("f", SomeObject)], interfaces=[iface])
    schema = _single_type_schema(obj)
    assert schema.is_valid


def test_reject_object_fields_with_missing_interface_argument():
    iface = InterfaceType(
        "IFace", [Field("f", String, [Argument("arg", String)])]
    )
    obj = ObjectType("Obj", [Field("f", String)], interfaces=[iface])
    schema = _single_type_schema(obj)
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value) == 'Interface field argument "IFace.f.arg" is not '
        'provided by "Obj.f"'
    )


def test_reject_object_fields_with_incorrectly_typed_interface_argument():
    iface = InterfaceType(
        "IFace", [Field("f", String, [Argument("arg", String)])]
    )
    obj = ObjectType(
        "Obj", [Field("f", String, [Argument("arg", Int)])], interfaces=[iface]
    )
    schema = _single_type_schema(obj)
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value) == 'Interface field argument "IFace.f.arg" expects '
        'type "String" but "Obj.f.arg" is type "Int"'
    )


def test_reject_object_which_implements_interface_along_with_required_args():
    iface = InterfaceType("IFace", [Field("f", String)])
    schema = _single_type_schema(
        ObjectType(
            "SomeObject",
            [Field("f", String, [Argument("arg", NonNullType(String))])],
            interfaces=[iface],
        )
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Object field argument "SomeObject.f.arg" is of required '
        'type "String!" but is not provided by interface field "IFace.f"'
    )


def test_accept_object_with_list_interface_list_field():
    iface = InterfaceType("IFace", [Field("f", ListType(String))])
    schema = _single_type_schema(
        ObjectType(
            "SomeObject", [Field("f", ListType(String))], interfaces=[iface]
        )
    )
    assert schema.is_valid


def test_accept_object_with_non_list_interface_list_field():
    iface = InterfaceType("IFace", [Field("f", ListType(String))])
    schema = _single_type_schema(
        ObjectType("SomeObject", [Field("f", String)], interfaces=[iface])
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Interface field "IFace.f" expects type "[String]" but '
        '"SomeObject.f" is type "String"'
    )


def test_accept_object_with_list_interface_non_list_field():
    iface = InterfaceType("IFace", [Field("f", String)])
    schema = _single_type_schema(
        ObjectType(
            "SomeObject", [Field("f", ListType(String))], interfaces=[iface]
        )
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Interface field "IFace.f" expects type "String" but '
        '"SomeObject.f" is type "[String]"'
    )


def test_accept_object_with_non_null_interface_null_field():
    iface = InterfaceType("IFace", [Field("f", String)])
    schema = _single_type_schema(
        ObjectType(
            "SomeObject", [Field("f", NonNullType(String))], interfaces=[iface]
        )
    )
    assert schema.is_valid


def test_reject_object_with_null_interface_non_null_field():
    iface = InterfaceType("IFace", [Field("f", NonNullType(String))])
    schema = _single_type_schema(
        ObjectType("SomeObject", [Field("f", String)], interfaces=[iface])
    )
    with pytest.raises(SchemaError) as exc_info:
        validate_schema(schema)

    assert not schema.is_valid

    assert (
        str(exc_info.value)
        == 'Interface field "IFace.f" expects type "String!" but '
        '"SomeObject.f" is type "String"'
    )


def test_starwars_schema_is_valid(starwars_schema):
    assert validate_schema(starwars_schema)
