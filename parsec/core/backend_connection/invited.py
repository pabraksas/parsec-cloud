# Parsec Cloud (https://parsec.cloud) Copyright (c) AGPL-3.0 2016-present Scille SAS
from __future__ import annotations

import trio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, AsyncGenerator, TypeVar

from parsec.api.protocol import INVITED_CMDS
from parsec.core.backend_connection.authenticated import AcquireTransport
from parsec.core.types import BackendAddrType, BackendInvitationAddr
from parsec.core.backend_connection import cmds
from parsec.core.backend_connection.transport import connect_as_invited
from parsec.core.backend_connection.exceptions import BackendNotAvailable
from parsec.core.backend_connection.expose_cmds import Transport, expose_cmds_with_retrier

T = TypeVar("T")


class BackendInvitedCmds:
    def __init__(
        self,
        addr: BackendAddrType,
        acquire_transport: AcquireTransport,
    ) -> None:
        self.addr = addr
        self.acquire_transport = acquire_transport

    ping = expose_cmds_with_retrier(cmds.invited_ping)
    invite_info = expose_cmds_with_retrier(cmds.invite_info)
    invite_1_claimer_wait_peer = expose_cmds_with_retrier(cmds.invite_1_claimer_wait_peer)
    invite_2a_claimer_send_hashed_nonce = expose_cmds_with_retrier(
        cmds.invite_2a_claimer_send_hashed_nonce
    )
    invite_2b_claimer_send_nonce = expose_cmds_with_retrier(cmds.invite_2b_claimer_send_nonce)
    invite_3a_claimer_signify_trust = expose_cmds_with_retrier(cmds.invite_3a_claimer_signify_trust)
    invite_3b_claimer_wait_peer_trust = expose_cmds_with_retrier(
        cmds.invite_3b_claimer_wait_peer_trust
    )
    invite_4_claimer_communicate = expose_cmds_with_retrier(cmds.invite_4_claimer_communicate)


for cmd in INVITED_CMDS:
    assert hasattr(BackendInvitedCmds, cmd)


@asynccontextmanager
async def backend_invited_cmds_factory(
    addr: BackendInvitationAddr, keepalive: Optional[int] = None
) -> AsyncGenerator[BackendInvitedCmds, None]:
    """
    Raises:
        BackendConnectionError
    """
    transport_lock = trio.Lock()
    transport: Optional[Transport] = None
    closed = False

    async def _init_transport() -> None:
        nonlocal transport
        if not transport:
            if closed:
                raise trio.ClosedResourceError
            transport = await connect_as_invited(addr, keepalive=keepalive)
            transport.logger = transport.logger.bind(auth="<invited>")

    async def _destroy_transport() -> None:
        nonlocal transport
        if transport:
            await transport.aclose()
            transport = None

    @asynccontextmanager
    async def _acquire_transport(
        force_fresh: bool = False, ignore_status: bool = False, allow_not_available: bool = False
    ) -> AsyncIterator[Transport]:
        nonlocal transport

        async with transport_lock:
            await _init_transport()
            try:
                assert transport is not None, "Transport is None after call `_init_transport`"
                yield transport
            except BackendNotAvailable:
                await _destroy_transport()
                raise

    try:
        yield BackendInvitedCmds(addr, _acquire_transport)

    finally:
        async with transport_lock:
            closed = True
            await _destroy_transport()
