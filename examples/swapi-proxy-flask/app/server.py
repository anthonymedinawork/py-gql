# -*- coding: utf-8 -*-

import os

import flask

from py_gql import process_graphql_query
from py_gql.execution.runtime import ThreadPoolRuntime
from py_gql.tracers import ApolloTracer

from .schema import SCHEMA

SCHEMA_SDL = SCHEMA.to_string()
RUNTIME = ThreadPoolRuntime(max_workers=20)

with open(os.path.join(os.path.dirname(__file__), "graphiql.html")) as f:
    GRAPHIQL_HTML = f.read()


app = flask.Flask(__name__)


@app.route("/sdl")
def sdl_route():
    return flask.Response(SCHEMA_SDL, mimetype="text")


@app.route("/graphql", methods=("POST",))
def graphql_route():

    data = flask.request.json

    tracer = ApolloTracer()

    result = process_graphql_query(
        SCHEMA,
        data["query"],
        variables=data.get("variables", {}),
        operation_name=data.get("operation_name"),
        instrumentation=tracer,
        runtime=RUNTIME,
    ).result()

    result.add_extension(tracer)

    return flask.jsonify(result.response())


@app.route("/graphiql")
def grahiql_route():
    return GRAPHIQL_HTML
