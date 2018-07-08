# -*- coding: utf-8 -*-
""" """

from itertools import chain

from . import rules as _rules
from ..lang.visitor import ParrallelVisitor, visit
from ..utilities import TypeInfoVisitor
from .visitors import ValidationVisitor  # noqa: F401

SPECIFIED_RULES = (
    _rules.ExecutableDefinitionsChecker,
    _rules.UniqueOperationNameChecker,
    _rules.LoneAnonymousOperationChecker,
    _rules.SingleFieldSubscriptionsChecker,
    _rules.KnownTypeNamesChecker,
    _rules.FragmentsOnCompositeTypesChecker,
    _rules.VariablesAreInputTypesChecker,
    _rules.ScalarLeafsChecker,
    _rules.FieldsOnCorrectTypeChecker,
    _rules.UniqueFragmentNamesChecker,
    _rules.KnownFragmentNamesChecker,
    _rules.NoUnusedFragmentsChecker,
    _rules.PossibleFragmentSpreadsChecker,
    _rules.NoFragmentCyclesChecker,
    _rules.UniqueVariableNamesChecker,
    _rules.NoUndefinedVariablesChecker,
    _rules.NoUnusedVariablesChecker,
    _rules.KnownDirectivesChecker,
    _rules.UniqueDirectivesPerLocationChecker,
    _rules.KnownArgumentNamesChecker,
    _rules.UniqueArgumentNamesChecker,
    _rules.ValuesOfCorrectTypeChecker,
    _rules.ProvidedRequiredArgumentsChecker,
    _rules.VariablesInAllowedPositionChecker,
    _rules.OverlappingFieldsCanBeMergedChecker,
    _rules.UniqueInputFieldNamesChecker,
)


class ValidationResult(object):
    def __init__(self, errors):
        self.errors = errors or []

    def __bool__(self):
        return not self.errors

    __nonzero__ = __bool__

    def __iter__(self):
        return self.errors

    def __str__(self):
        return "<%s (%s)>" % (type(self).__name__, bool(self))


def validate_ast(schema, ast_root, validators=None):
    """ Check that an ast is a valid GraphQL query docuemnt.

    Runs a parse tree through a list of validation visitors given a schema.

    .. warning::

        This assumes the ast is a valid document generated by
        :func:`py_gql.lang.parse` and will most likely break
        unexpectedly if that's not the case.

    :type schema: py_gql.schema.Schema
    :param schema:
        Schema to validate against (for known types, directives, etc.).

    :type ast_root: py_gql.lang.ast.Document
    :param ast_root:
        The parse tree root, should be a Document.

    :type validators: Iterable[type|Tuple[type, dict]]
    :param validators:
        List of validators to use. Defaults to ``SPECIFIED_RULES``.

    :rtype: List[ValidationError]
    :returns:
        List of ValidationErrors.
    """
    type_info = TypeInfoVisitor(schema)
    if validators is None:
        validators = SPECIFIED_RULES

    def instantiate_validator(cls_or_tuple, schema, type_info):
        if isinstance(cls_or_tuple, tuple):
            cls, kw = cls_or_tuple
        else:
            cls, kw = cls_or_tuple, {}
        assert issubclass(cls, ValidationVisitor)
        return cls(schema, type_info, **kw)

    # Type info NEEDS to be first to be accurately used inside other validators
    # so when a validator enters node the type stack has already been updated.
    validator = ParrallelVisitor(
        type_info,
        *[
            instantiate_validator(validator_, schema, type_info)
            for validator_ in validators
        ]
    )

    visit(validator, ast_root)
    return ValidationResult(
        list(chain(*[v.errors for v in validator.visitors[1:]]))
    )
