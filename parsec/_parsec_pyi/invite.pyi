# Parsec Cloud (https://parsec.cloud) Copyright (c) AGPL-3.0 2016-present Scille SAS

from __future__ import annotations

from typing import List, Tuple

from parsec._parsec_pyi.crypto import PrivateKey, PublicKey, SecretKey, VerifyKey
from parsec._parsec_pyi.enumerate import UserProfile
from parsec._parsec_pyi.ids import DeviceID, DeviceLabel, EntryID, HumanHandle

class SASCode:
    def __init__(self, code: str) -> None: ...
    def __str__(self) -> str: ...
    def __lt__(self, other: SASCode) -> bool: ...
    def __gt__(self, other: SASCode) -> bool: ...
    def __le__(self, other: SASCode) -> bool: ...
    def __ge__(self, other: SASCode) -> bool: ...
    def __hash__(self) -> int: ...
    @classmethod
    def from_int(cls, num: int) -> SASCode: ...
    @property
    def str(self) -> str: ...

def generate_sas_codes(
    claimer_nonce: bytes, greeter_nonce: bytes, shared_secret_key: SecretKey
) -> Tuple[SASCode, SASCode]: ...
def generate_sas_code_candidates(valid_sas: SASCode, size: int) -> List[SASCode]: ...

class InviteUserData:
    def __init__(
        self,
        requested_device_label: DeviceLabel | None,
        requested_human_handle: HumanHandle | None,
        public_key: PublicKey,
        verify_key: VerifyKey,
    ) -> None: ...
    @property
    def requested_human_handle(self) -> HumanHandle | None: ...
    @property
    def requested_device_label(self) -> DeviceLabel | None: ...
    @property
    def public_key(self) -> PublicKey: ...
    @property
    def verify_key(self) -> VerifyKey: ...
    @classmethod
    def dump_and_encrypt(cls, key: SecretKey) -> bytes: ...
    @classmethod
    def decrypt_and_load(cls, encrypted: bytes, key: SecretKey) -> InviteUserData: ...

class InviteUserConfirmation:
    def __init__(
        self,
        device_id: DeviceID,
        device_label: DeviceLabel | None,
        human_handle: HumanHandle | None,
        profile: UserProfile,
        root_verify_key: VerifyKey,
    ) -> None: ...
    @property
    def human_handle(self) -> HumanHandle | None: ...
    @property
    def device_label(self) -> DeviceLabel | None: ...
    @property
    def device_id(self) -> DeviceID: ...
    @property
    def profile(self) -> UserProfile: ...
    @property
    def root_verify_key(self) -> VerifyKey: ...
    def dump_and_encrypt(self, key: SecretKey) -> bytes: ...
    @classmethod
    def decrypt_and_load(cls, encrypted: bytes, key: SecretKey) -> InviteUserConfirmation: ...

class InviteDeviceData:
    def __init__(
        self, requested_device_label: DeviceLabel | None, verify_key: VerifyKey
    ) -> None: ...
    @property
    def requested_device_label(self) -> DeviceLabel | None: ...
    @property
    def verify_key(self) -> VerifyKey: ...
    def dump_and_encrypt(self, key: SecretKey) -> bytes: ...
    @classmethod
    def decrypt_and_load(cls, encrypted: bytes, key: SecretKey) -> InviteDeviceData: ...

class InviteDeviceConfirmation:
    def __init__(
        self,
        device_id: DeviceID,
        device_label: DeviceLabel | None,
        human_handle: HumanHandle | None,
        profile: UserProfile,
        private_key: PrivateKey,
        root_verify_key: VerifyKey,
        user_manifest_id: EntryID,
        user_manifest_key: SecretKey,
    ) -> None: ...
    @property
    def device_id(self) -> DeviceID: ...
    @property
    def device_label(self) -> DeviceLabel | None: ...
    @property
    def human_handle(self) -> HumanHandle | None: ...
    @property
    def profile(self) -> UserProfile: ...
    @property
    def private_key(self) -> PrivateKey: ...
    @property
    def root_verify_key(self) -> VerifyKey: ...
    @property
    def user_manifest_id(self) -> EntryID: ...
    @property
    def user_manifest_key(self) -> SecretKey: ...
    def dump_and_encrypt(self, key: SecretKey) -> bytes: ...
    @classmethod
    def decrypt_and_load(cls, encrypted: bytes, key: SecretKey) -> InviteDeviceConfirmation: ...
