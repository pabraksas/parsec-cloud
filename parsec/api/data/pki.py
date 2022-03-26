# Parsec Cloud (https://parsec.cloud) Copyright (c) AGPLv3 2016-2021 Scille SAS

import attr
from typing import Dict, Any

from parsec.api.data.base import BaseAPIData
from parsec.api.protocol import HumanHandle, HumanHandleField
from parsec.api.protocol.types import DeviceLabel, DeviceLabelField
from parsec.crypto import PublicKey, VerifyKey
from parsec.serde import BaseSchema, fields, post_load


@attr.s(slots=True, frozen=True, auto_attribs=True, kw_only=True, eq=False)
class PkiEnrollmentRequestInfo(BaseAPIData):
    class SCHEMA_CLS(BaseSchema):
        verify_key = fields.VerifyKey(required=True)
        public_key = fields.PublicKey(required=True)
        requested_human_handle = HumanHandleField(required=True)
        requested_device_label = DeviceLabelField(required=True)

        @post_load
        def make_obj(self, data: Dict[str, Any]) -> "PkiEnrollmentRequestInfo":
            return PkiEnrollmentRequestInfo(**data)

    verify_key: VerifyKey
    public_key: PublicKey
    requested_human_handle: HumanHandle
    requested_device_label: DeviceLabel


@attr.s(slots=True, frozen=True, auto_attribs=True, kw_only=True, eq=False)
class PkiEnrollmentRequest(BaseAPIData):
    class SCHEMA_CLS(BaseSchema):
        der_x509_certificate = fields.Bytes(require=True)
        signature = fields.Bytes(required=True)
        pki_request_info = fields.Bytes(required=True)  # Signature should be checked before loading
        requested_human_handle = HumanHandleField(required=True)

        @post_load
        def make_obj(self, data: Dict[str, Any]) -> "PkiEnrollmentRequest":
            return PkiEnrollmentRequest(**data)

    der_x509_certificate: bytes
    signature: bytes
    pki_request_info: bytes
    requested_human_handle: HumanHandle


@attr.s(slots=True, frozen=True, auto_attribs=True, kw_only=True, eq=False)
class PkiEnrollmentReply(BaseAPIData):
    class SCHEMA_CLS(BaseSchema):
        der_x509_admin_certificate = fields.Bytes(required=True)
        signature = fields.Bytes(required=True)
        pki_reply_info = fields.Bytes(required=True)  # Signature should be checked before loading

        @post_load
        def make_obj(self, data: Dict[str, Any]) -> "PkiEnrollmentReply":
            return PkiEnrollmentReply(**data)

    der_x509_admin_certificate: bytes
    signature: bytes
    pki_reply_info: bytes
