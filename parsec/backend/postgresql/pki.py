# Parsec Cloud (https://parsec.cloud) Copyright (c) BSLv1.1 (eventually AGPLv3) 2016-2021 Scille SAS

import hashlib
from typing import List
from uuid import UUID
from pendulum import DateTime

from parsec.api.protocol import OrganizationID
from parsec.api.protocol.pki import PkiEnrollmentStatus
from parsec.api.protocol.types import UserID, UserProfile
from parsec.backend.backend_events import BackendEvent
from parsec.backend.postgresql.handler import send_signal
from parsec.backend.user import UserActiveUsersLimitReached, UserAlreadyExistsError
from parsec.backend.user_type import User, Device
from parsec.backend.pki import (
    PkiEnrollmentActiveUsersLimitReached,
    PkiEnrollmentAlreadyEnrolledError,
    PkiEnrollmentAlreadyExistError,
    PkiEnrollmentCertificateAlreadySubmittedError,
    PkiEnrollmentIdAlreadyUsedError,
    PkiEnrollmentInfo,
    PkiEnrollmentInfoAccepted,
    PkiEnrollmentInfoCancelled,
    PkiEnrollmentInfoRejected,
    PkiEnrollmentInfoSubmitted,
    PkiEnrollmentListItem,
    BasePkiEnrollmentComponent,
    PkiEnrollmentNoLongerAvailableError,
    PkiEnrollmentNotFoundError,
)
from parsec.backend.postgresql import PGHandler
from parsec.backend.postgresql.utils import Q, q_organization_internal_id, q_device_internal_id
from parsec.backend.postgresql.user_queries.create import (
    q_create_user,
    q_take_user_device_write_lock,
)

_q_get_pki_enrollment_from_certificate_sha1 = Q(
    f"""
    SELECT * FROM pki_enrollment
    WHERE (
        organization = { q_organization_internal_id("$organization_id") }
        AND submitter_der_x509_certificate_sha1=$submitter_der_x509_certificate_sha1
    )
    ORDER BY enrollment_state ASC
    """
)

_q_get_pki_enrollment_from_enrollment_id = Q(
    f"""
    SELECT * FROM pki_enrollment
    WHERE (
        organization = { q_organization_internal_id("$organization_id") }
        AND enrollment_id=$enrollment_id
    )
    """
)

_q_get_pki_enrollment_for_update = Q(
    f"""
    SELECT * FROM pki_enrollment
    WHERE (
        organization = { q_organization_internal_id("$organization_id") }
        AND enrollment_id=$enrollment_id
    )
    FOR UPDATE
    """
)

_q_get_pki_enrollment_from_state = Q(
    f"""
    SELECT * FROM pki_enrollment
    WHERE (
        organization = { q_organization_internal_id("$organization_id") }
        AND enrollment_state=$state
    )
    ORDER BY _id ASC
    """
)


_q_submit_pki_enrollment = Q(
    f"""
    INSERT INTO pki_enrollment(
        organization,
        enrollment_id,
        submitter_der_x509_certificate,
        submitter_der_x509_certificate_sha1,
        submit_payload_signature,
        submit_payload,
        enrollment_state,
        submitted_on
    )
    VALUES(
        { q_organization_internal_id("$organization_id") },
        $enrollment_id,
        $submitter_der_x509_certificate,
        $submitter_der_x509_certificate_sha1,
        $submit_payload_signature,
        $submit_payload,
        $enrollment_state,
        $submitted_on
    )

    """
)

_q_cancel_pki_enrollment = Q(
    f"""
    UPDATE pki_enrollment
    SET
        enrollment_state=$enrollment_state,
        info_cancelled.cancelled_on=$cancelled_on
    WHERE (
        organization = { q_organization_internal_id("$organization_id") }
        AND enrollment_id=$enrollment_id
    )
    """
)


_q_reject_pki_enrollment = Q(
    f"""
    UPDATE pki_enrollment
    SET
        enrollment_state=$enrollment_state,
        info_rejected.rejected_on=$rejected_on
    WHERE (
        organization = { q_organization_internal_id("$organization_id") }
        AND enrollment_id=$enrollment_id
    )
    """
)


_q_accept_pki_enrollment = Q(
    f"""
    UPDATE pki_enrollment
    SET
        enrollment_state=$enrollment_state,
        info_accepted.accepted_on=$accepted_on,
        info_accepted.accepter_der_x509_certificate=$accepter_der_x509_certificate,
        info_accepted.accept_payload_signature=$accept_payload_signature,
        info_accepted.accept_payload=$accept_payload,
        accepter={q_device_internal_id(organization_id="$organization_id", device_id="$accepter")},
        accepted={q_device_internal_id(organization_id="$organization_id", device_id="$accepted")}
    WHERE (
        organization = { q_organization_internal_id("$organization_id") }
        AND enrollment_id=$enrollment_id
    )
    """
)


_q_get_user_from_device_id = Q(
    f"""
    SELECT *
    FROM user_
    WHERE
        user_.organization = { q_organization_internal_id("$organization_id") }
        AND user_._id=(
            SELECT user_
            FROM device
            WHERE device._id=$device_id
            AND device.organization = { q_organization_internal_id("$organization_id") }
        )
    LIMIT 1
    """
)


def _build_enrollment_info(entry) -> PkiEnrollmentInfo:
    if entry["enrollment_state"] == PkiEnrollmentStatus.SUBMITTED.value:
        return PkiEnrollmentInfoSubmitted(
            enrollment_id=entry["enrollment_id"], submitted_on=entry["submitted_on"]
        )
    elif entry["enrollment_state"] == PkiEnrollmentStatus.CANCELLED.value:
        return PkiEnrollmentInfoCancelled(
            enrollment_id=entry["enrollment_id"],
            submitted_on=entry["submitted_on"],
            cancelled_on=entry["info_cancelled"]["cancelled_on"],
        )
    elif entry["enrollment_state"] == PkiEnrollmentStatus.REJECTED.value:
        return PkiEnrollmentInfoRejected(
            enrollment_id=entry["enrollment_id"],
            submitted_on=entry["submitted_on"],
            rejected_on=entry["info_rejected"]["rejected_on"],
        )
    elif entry["enrollment_state"] == PkiEnrollmentStatus.ACCEPTED.value:
        return PkiEnrollmentInfoAccepted(
            enrollment_id=entry["enrollment_id"],
            submitted_on=entry["submitted_on"],
            accepted_on=entry["info_accepted"]["accepted_on"],
            accepter_der_x509_certificate=entry["info_accepted"]["accepter_der_x509_certificate"],
            accept_payload_signature=entry["info_accepted"]["accept_payload_signature"],
            accept_payload=entry["info_accepted"]["accept_payload"],
        )
    else:
        assert False


class PGPkiEnrollmentComponent(BasePkiEnrollmentComponent):
    def __init__(self, dbh: PGHandler):
        self.dbh = dbh

    def register_components(self, **other_components):
        self._user_component = other_components["user"]

    async def submit(
        self,
        organization_id: OrganizationID,
        enrollment_id: UUID,
        force: bool,
        submitter_der_x509_certificate: bytes,
        submit_payload_signature: bytes,
        submit_payload: bytes,
        submitted_on: DateTime,
    ) -> None:
        """
        Raises:
            PkiEnrollmentCertificateAlreadySubmittedError
            PkiEnrollmentAlreadyEnrolledError
        """
        submitter_der_x509_certificate_sha1 = hashlib.sha1(submitter_der_x509_certificate).digest()
        async with self.dbh.pool.acquire() as conn, conn.transaction():
            # Hold the user/device write lock before any check in the enrollment
            # table to ensure it is going to be done without concurrency issues
            await q_take_user_device_write_lock(conn, organization_id)

            # Assert enrollment_id not used
            row = await conn.fetchrow(
                *_q_get_pki_enrollment_for_update(
                    organization_id=organization_id.str, enrollment_id=enrollment_id
                )
            )
            if row:
                raise PkiEnrollmentIdAlreadyUsedError()

            # Try to retrieve the last attempt with this x509 certificate
            rep = await conn.fetch(
                *_q_get_pki_enrollment_from_certificate_sha1(
                    organization_id=organization_id.str,
                    submitter_der_x509_certificate_sha1=submitter_der_x509_certificate_sha1,
                )
            )
            for row in rep:
                enrollment_state = row["enrollment_state"]
                if enrollment_state == PkiEnrollmentStatus.SUBMITTED.value:
                    if force:
                        await conn.execute(
                            *_q_cancel_pki_enrollment(
                                organization_id=organization_id.str,
                                enrollment_id=row["enrollment_id"],
                                enrollment_state=PkiEnrollmentStatus.CANCELLED.value,
                                cancelled_on=submitted_on,
                            )
                        )
                        await send_signal(
                            conn,
                            BackendEvent.PKI_ENROLLMENT_UPDATED,
                            organization_id=organization_id,
                        )

                    else:
                        raise PkiEnrollmentCertificateAlreadySubmittedError(
                            submitted_on=row["submitted_on"]
                        )
                elif enrollment_state in [
                    PkiEnrollmentStatus.REJECTED.value,
                    PkiEnrollmentStatus.CANCELLED.value,
                ]:
                    # Previous attempt was unsuccessful, so we are clear to submit a new attempt !
                    pass
                elif enrollment_state == PkiEnrollmentStatus.ACCEPTED.value:
                    # Previous attempt end successfully, we are not allowed to submit
                    # unless the created user has been revoked
                    assert row["accepted"] is not None and row["accepter"] is not None

                    row = await conn.fetchrow(
                        *_q_get_user_from_device_id(
                            organization_id=organization_id.str,
                            device_id=row["accepted"],
                            # now=submitted_on,
                        )
                    )
                    user = User(
                        user_id=UserID(row["user_id"]),
                        human_handle=None,
                        profile=UserProfile(row["profile"]),
                        user_certificate=row["user_certificate"],
                        redacted_user_certificate=row["redacted_user_certificate"],
                        user_certifier=None,
                        created_on=row["created_on"],
                        revoked_on=row["revoked_on"],
                        revoked_user_certificate=row["revoked_user_certificate"],
                        revoked_user_certifier=None,
                    )
                    # if row and row.get("revoked_on") and row.get("revoked_on") < submitted_on:
                    if not user.is_revoked():
                        raise PkiEnrollmentAlreadyEnrolledError(submitted_on)
                else:
                    assert False
            await conn.execute(
                *_q_submit_pki_enrollment(
                    organization_id=organization_id.str,
                    enrollment_id=enrollment_id,
                    submitter_der_x509_certificate=submitter_der_x509_certificate,
                    submitter_der_x509_certificate_sha1=submitter_der_x509_certificate_sha1,
                    submit_payload_signature=submit_payload_signature,
                    submit_payload=submit_payload,
                    enrollment_state=PkiEnrollmentStatus.SUBMITTED.value,
                    submitted_on=submitted_on,
                )
            )
            await send_signal(
                conn, BackendEvent.PKI_ENROLLMENT_UPDATED, organization_id=organization_id
            )

    async def info(self, organization_id: OrganizationID, enrollment_id: UUID) -> PkiEnrollmentInfo:
        """
        Raises:
            PkiEnrollmentNotFoundError
        """
        async with self.dbh.pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                *_q_get_pki_enrollment_from_enrollment_id(
                    organization_id=organization_id.str, enrollment_id=enrollment_id
                )
            )
            if not row:
                raise PkiEnrollmentNotFoundError()
            else:
                return _build_enrollment_info(row)

    async def list(self, organization_id: OrganizationID) -> List[PkiEnrollmentListItem]:
        """
        Raises: Nothing !
        """

        async with self.dbh.pool.acquire() as conn, conn.transaction():

            entries = await conn.fetch(
                *_q_get_pki_enrollment_from_state(
                    organization_id=organization_id.str, state=PkiEnrollmentStatus.SUBMITTED.value
                )
            )
            return [
                PkiEnrollmentListItem(
                    enrollment_id=entry["enrollment_id"],
                    submitted_on=entry["submitted_on"],
                    submitter_der_x509_certificate=entry["submitter_der_x509_certificate"],
                    submit_payload_signature=entry["submit_payload_signature"],
                    submit_payload=entry["submit_payload"],
                )
                for entry in entries
            ]

    async def reject(
        self, organization_id: OrganizationID, enrollment_id: UUID, rejected_on: DateTime
    ) -> None:
        """
        Raises:
            PkiEnrollmentNotFoundError
            PkiEnrollmentNoLongerAvailableError
        """

        async with self.dbh.pool.acquire() as conn, conn.transaction():
            # Enrollment submit depend on the data we are going to modify,
            # hence by transitivity we also should hold the user/device write lock
            await q_take_user_device_write_lock(conn, organization_id)

            row = await conn.fetchrow(
                *_q_get_pki_enrollment_for_update(
                    organization_id=organization_id.str, enrollment_id=enrollment_id
                )
            )
            if not row:
                raise PkiEnrollmentNotFoundError()
            if row["enrollment_state"] != PkiEnrollmentStatus.SUBMITTED.value:
                raise PkiEnrollmentNoLongerAvailableError()

            await conn.execute(
                *_q_reject_pki_enrollment(
                    organization_id=organization_id.str,
                    enrollment_id=enrollment_id,
                    enrollment_state=PkiEnrollmentStatus.REJECTED.value,
                    rejected_on=rejected_on,
                )
            )
            await send_signal(
                conn, BackendEvent.PKI_ENROLLMENT_UPDATED, organization_id=organization_id
            )

    async def accept(
        self,
        organization_id: OrganizationID,
        enrollment_id: UUID,
        accepter_der_x509_certificate: bytes,
        accept_payload_signature: bytes,
        accept_payload: bytes,
        accepted_on: DateTime,
        user: User,
        first_device: Device,
    ) -> None:
        """
        Raises:
            PkiEnrollmentNotFoundError
            PkiEnrollmentNoLongerAvailableError
            PkiEnrollmentAlreadyExistError
            PkiEnrollmentActiveUsersLimitReached
        """
        async with self.dbh.pool.acquire() as conn, conn.transaction():
            # Enrollment submit depend on the data we are going to modify,
            # hence by transitivity we also should hold the user/device write lock
            await q_take_user_device_write_lock(conn, organization_id)

            row = await conn.fetchrow(
                *_q_get_pki_enrollment_for_update(
                    organization_id=organization_id.str, enrollment_id=enrollment_id
                )
            )
            if not row:
                raise PkiEnrollmentNotFoundError()
            if row["enrollment_state"] != PkiEnrollmentStatus.SUBMITTED.value:
                raise PkiEnrollmentNoLongerAvailableError()

            try:
                await q_create_user(
                    conn=conn,
                    organization_id=organization_id,
                    user=user,
                    first_device=first_device,
                    lock_already_held=True,
                )

            except UserAlreadyExistsError as exc:
                raise PkiEnrollmentAlreadyExistError from exc

            except UserActiveUsersLimitReached as exc:
                raise PkiEnrollmentActiveUsersLimitReached from exc

            assert user.user_certifier is not None
            await conn.execute(
                *_q_accept_pki_enrollment(
                    enrollment_state=PkiEnrollmentStatus.ACCEPTED.value,
                    organization_id=organization_id.str,
                    enrollment_id=enrollment_id,
                    accepted_on=accepted_on,
                    accepter_der_x509_certificate=accepter_der_x509_certificate,
                    accept_payload_signature=accept_payload_signature,
                    accept_payload=accept_payload,
                    accepter=user.user_certifier.str,
                    accepted=first_device.device_id.str,
                )
            )
            await send_signal(
                conn, BackendEvent.PKI_ENROLLMENT_UPDATED, organization_id=organization_id
            )
