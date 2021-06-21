# Parsec Cloud (https://parsec.cloud) Copyright (c) AGPLv3 2016-2021 Scille SAS

import enum


# Cross-plateform windows error enumeration


class ntstatus(enum.IntEnum):
    STATUS_INVALID_HANDLE = 0xC0000008
    STATUS_INVALID_PARAMETER = 0xC000000D
    STATUS_END_OF_FILE = 0xC0000011
    STATUS_ACCESS_DENIED = 0xC0000022
    STATUS_OBJECT_NAME_NOT_FOUND = 0xC0000034
    STATUS_OBJECT_NAME_COLLISION = 0xC0000035
    STATUS_MEDIA_WRITE_PROTECTED = 0xC00000A2
    STATUS_FILE_IS_A_DIRECTORY = 0xC00000BA
    STATUS_NOT_SAME_DEVICE = 0xC00000D4
    STATUS_DIRECTORY_NOT_EMPTY = 0xC0000101
    STATUS_NOT_A_DIRECTORY = 0xC0000103
    STATUS_HOST_UNREACHABLE = 0xC000023D
