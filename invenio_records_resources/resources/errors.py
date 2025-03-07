# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
# Copyright (C) 2020 Northwestern University
#
# Invenio-Records-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Common Errors handling for Resources."""

import marshmallow as ma
from flask import g, jsonify, make_response, request, url_for
from flask_resources import HTTPJSONException, Resource, create_error_handler
from invenio_pidstore.errors import PIDAlreadyExists, PIDDeletedError, \
    PIDDoesNotExistError, PIDRedirectedError, PIDUnregistered
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.routing import BuildError

from ..errors import validation_error_to_list_errors
from ..services.errors import PermissionDeniedError, \
    QuerystringValidationError, RevisionIdMismatchError


class HTTPJSONValidationException(HTTPJSONException):
    """HTTP exception serializing to JSON and reflecting Marshmallow errors."""

    description = "A validation error occurred."

    def __init__(self, exception):
        """Constructor."""
        super().__init__(
            code=400,
            errors=validation_error_to_list_errors(exception)
        )


def create_pid_redirected_error_handler():
    """Creates an error handler for `PIDRedirectedError` error."""

    def pid_redirected_error_handler(e):
        try:
            # Check that the source pid and the destination pid are of the same
            # pid_type
            assert e.pid.pid_type == e.destination_pid.pid_type
            # Redirection works only for the item route of the format
            # `/records/<pid_value>`
            location = url_for(
                request.url_rule.endpoint,
                pid_value=e.destination_pid.pid_value
            )
            data = dict(
                status=301,
                message='Moved Permanently.',
                location=location,
            )
            response = make_response(jsonify(data), data['status'])
            response.headers['Location'] = location
            return response
        except (AssertionError, BuildError, KeyError):
            raise e

    return pid_redirected_error_handler


class ErrorHandlersMixin:
    """Mixin to define common error handlers."""

    error_handlers = {
        ma.ValidationError: create_error_handler(
            lambda e: HTTPJSONValidationException(e)
        ),
        RevisionIdMismatchError: create_error_handler(
            lambda e: HTTPJSONException(
                code=412,
                description=e.description,
            )
        ),
        QuerystringValidationError: create_error_handler(
            HTTPJSONException(
                code=400,
                description="Invalid querystring parameters.",
            )
        ),
        PermissionDeniedError: create_error_handler(
            HTTPJSONException(
                code=403,
                description="Permission denied.",
            )
        ),
        PIDDeletedError: create_error_handler(
            HTTPJSONException(
                code=410,
                description="The record has been deleted.",
            )
        ),
        PIDAlreadyExists: create_error_handler(
            HTTPJSONException(
                code=400,
                description="The persistent identifier is already registered.",
            )
        ),
        PIDDoesNotExistError: create_error_handler(
            HTTPJSONException(
                code=404,
                description="The persistent identifier does not exist.",
            )
        ),
        PIDUnregistered: create_error_handler(
            HTTPJSONException(
                code=404,
                description="The persistent identifier is not registered.",
            )
        ),
        PIDRedirectedError: create_pid_redirected_error_handler(),
        NoResultFound: create_error_handler(
            HTTPJSONException(
                code=404,
                description="Not found.",
            )
        ),
    }
