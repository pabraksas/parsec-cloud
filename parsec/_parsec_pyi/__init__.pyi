# Parsec Cloud (https://parsec.cloud) Copyright (c) AGPL-3.0 2016-present Scille SAS

from __future__ import annotations

# Data Error
class DataError(Exception): ...
class EntryNameError(ValueError): ...
class PkiEnrollmentError(Exception): ...
class PkiEnrollmentLocalPendingError(PkiEnrollmentError): ...
class PkiEnrollmentLocalPendingCannotReadError(PkiEnrollmentLocalPendingError): ...
class PkiEnrollmentLocalPendingCannotRemoveError(PkiEnrollmentLocalPendingError): ...
class PkiEnrollmentLocalPendingCannotSaveError(PkiEnrollmentLocalPendingError): ...
class PkiEnrollmentLocalPendingValidationError(PkiEnrollmentLocalPendingError): ...
