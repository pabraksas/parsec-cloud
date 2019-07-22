# Parsec Cloud (https://parsec.cloud) Copyright (c) AGPLv3 2019 Scille SAS

import attr
import pendulum
from typing import Tuple, Dict, List, Union

from parsec.types import DeviceID, FrozenDict
from parsec.serde import UnknownCheckedSchema, OneOfSchema, fields, validate, post_load
from parsec.core.types import remote_manifests
from parsec.core.types.base import (
    EntryID,
    EntryIDField,
    EntryName,
    EntryNameField,
    serializer_factory,
)
from parsec.core.types.access import (
    BlockAccess,
    BlockAccessSchema,
    DirtyBlockAccess,
    DirtyBlockAccessSchema,
    WorkspaceEntry,
    WorkspaceEntrySchema,
)


__all__ = (
    "LocalFileManifest",
    "LocalFolderManifest",
    "LocalWorkspaceManifest",
    "LocalUserManifest",
    "local_manifest_dumps",
    "local_manifest_loads",
)


# File manifest


@attr.s(slots=True, frozen=True, auto_attribs=True)
class LocalFileManifest:
    author: DeviceID
    base_manifest: remote_manifests.FileManifest
    need_sync: bool = False
    updated: pendulum.Pendulum = None
    size: int = 0
    blocks: Tuple[BlockAccess] = attr.ib(converter=tuple, default=())
    dirty_blocks: Tuple[DirtyBlockAccess] = attr.ib(converter=tuple, default=())

    def __attrs_post_init__(self):
        if self.updated is None:
            object.__setattr__(self, "updated", self.base_manifest.updated)

    @classmethod
    def make_placeholder(cls, author, parent_id, created=None):
        if created is None:
            created = pendulum.now()
        base_manifest = remote_manifests.FileManifest(
            author=author,
            parent_id=parent_id,
            version=0,
            created=created,
            updated=created,
            size=0,
            blocks=(),
        )
        return cls(author, base_manifest, need_sync=True)

    # Properties

    @property
    def parent_id(self):
        return self.base_manifest.parent_id

    @property
    def created(self):
        return self.base_manifest.created

    @property
    def base_version(self):
        return self.base_manifest.version

    @property
    def is_placeholder(self):
        return self.base_manifest.version == 0

    # Evolve methods

    def evolve_and_mark_updated(self, **data) -> "LocalFileManifest":
        if "updated" not in data:
            data["updated"] = pendulum.now()
        data.setdefault("need_sync", True)
        return attr.evolve(self, **data)

    def evolve(self, **data) -> "LocalFileManifest":
        return attr.evolve(self, **data)

    # Export methods

    def to_remote(self, **data) -> "remote_manifests.FileManifest":
        return remote_manifests.FileManifest(
            author=self.author,
            parent_id=self.parent_id,
            version=self.base_version,
            created=self.created,
            updated=self.updated,
            size=self.size,
            blocks=self.blocks,
            **data,
        )

    def asdict(self):
        dct = attr.asdict(self)
        dct.pop("base_manifest")
        props = "base_version", "is_placeholder", "parent_id", "created"
        for name in props:
            dct[name] = getattr(self, name)
        return dct


class LocalFileManifestSchema(UnknownCheckedSchema):
    format = fields.CheckedConstant(1, required=True)
    type = fields.CheckedConstant("local_file_manifest", required=True)
    author = fields.DeviceID(required=True)
    base_manifest = fields.Nested(remote_manifests.FileManifestSchema, required=True)
    need_sync = fields.Boolean(required=True)
    updated = fields.DateTime(required=True)
    size = fields.Integer(required=True, validate=validate.Range(min=0))
    blocks = fields.List(fields.Nested(BlockAccessSchema), required=True)
    dirty_blocks = fields.List(fields.Nested(DirtyBlockAccessSchema), required=True)

    @post_load
    def make_obj(self, data):
        data.pop("type")
        data.pop("format")
        return LocalFileManifest(**data)


local_file_manifest_serializer = serializer_factory(LocalFileManifestSchema)


# Folder manifest


@attr.s(slots=True, frozen=True, auto_attribs=True)
class LocalFolderManifest:

    author: DeviceID
    base_manifest: remote_manifests.FolderManifest
    need_sync: bool = False
    updated: pendulum.Pendulum = None
    children: Dict[EntryName, EntryID] = attr.ib(converter=FrozenDict, factory=FrozenDict)

    def __attrs_post_init__(self):
        if self.updated is None:
            object.__setattr__(self, "updated", self.base_manifest.updated)

    @classmethod
    def make_placeholder(cls, author, parent_id, created=None):
        if created is None:
            created = pendulum.now()
        base_manifest = remote_manifests.FolderManifest(
            author=author,
            parent_id=parent_id,
            version=0,
            created=created,
            updated=created,
            children={},
        )
        return cls(author, base_manifest, need_sync=True)

    # Properties

    @property
    def parent_id(self):
        return self.base_manifest.parent_id

    @property
    def created(self):
        return self.base_manifest.created

    @property
    def base_version(self):
        return self.base_manifest.version

    @property
    def is_placeholder(self):
        return self.base_manifest.version == 0

    # Evolve methods

    def evolve_and_mark_updated(self, **data) -> "LocalFolderManifest":
        if "updated" not in data:
            data["updated"] = pendulum.now()
        data.setdefault("need_sync", True)
        return attr.evolve(self, **data)

    def evolve(self, **data) -> "LocalFolderManifest":
        return attr.evolve(self, **data)

    def evolve_children_and_mark_updated(self, data) -> "LocalFolderManifest":
        return self.evolve_and_mark_updated(
            children={k: v for k, v in {**self.children, **data}.items() if v is not None}
        )

    def evolve_children(self, data) -> "LocalFolderManifest":
        return self.evolve(
            children={k: v for k, v in {**self.children, **data}.items() if v is not None}
        )

    # Export methods

    def to_remote(self, **data) -> "remote_manifests.FolderManifest":
        return remote_manifests.FolderManifest(
            author=self.author,
            parent_id=self.parent_id,
            version=self.base_version,
            created=self.created,
            updated=self.updated,
            children=self.children,
            **data,
        )

    def asdict(self):
        dct = attr.asdict(self)
        dct.pop("base_manifest")
        props = "base_version", "is_placeholder", "parent_id", "created"
        for name in props:
            dct[name] = getattr(self, name)
        return dct


class LocalFolderManifestSchema(UnknownCheckedSchema):
    format = fields.CheckedConstant(1, required=True)
    type = fields.CheckedConstant("local_folder_manifest", required=True)
    author = fields.DeviceID(required=True)
    base_manifest = fields.Nested(remote_manifests.FolderManifestSchema, required=True)
    need_sync = fields.Boolean(required=True)
    updated = fields.DateTime(required=True)
    children = fields.Map(
        EntryNameField(validate=validate.Length(min=1, max=256)),
        EntryIDField(required=True),
        required=True,
    )

    @post_load
    def make_obj(self, data):
        data.pop("type")
        data.pop("format")
        return LocalFolderManifest(**data)


local_folder_manifest_serializer = serializer_factory(LocalFolderManifestSchema)


# Workspace manifest


@attr.s(slots=True, frozen=True, auto_attribs=True)
class LocalWorkspaceManifest:

    author: DeviceID
    base_manifest: remote_manifests.WorkspaceManifest
    need_sync: bool = False
    updated: pendulum.Pendulum = None
    children: Dict[EntryName, EntryID] = attr.ib(converter=FrozenDict, factory=FrozenDict)

    def __attrs_post_init__(self):
        if self.updated is None:
            object.__setattr__(self, "updated", self.base_manifest.updated)

    @classmethod
    def make_placeholder(cls, author, parent_id, created=None):
        if created is None:
            created = pendulum.now()
        base_manifest = remote_manifests.WorkspaceManifest(
            author=author,
            parent_id=parent_id,
            version=0,
            created=created,
            updated=created,
            children={},
        )
        return cls(author, base_manifest, need_sync=True)

    # Properties

    @property
    def parent_id(self):
        return self.base_manifest.parent_id

    @property
    def created(self):
        return self.base_manifest.created

    @property
    def base_version(self):
        return self.base_manifest.version

    @property
    def is_placeholder(self):
        return self.base_manifest.version == 0

    # Evolve methods

    def evolve_and_mark_updated(self, **data) -> "LocalWorkspaceManifest":
        if "updated" not in data:
            data["updated"] = pendulum.now()
        data.setdefault("need_sync", True)
        return attr.evolve(self, **data)

    def evolve(self, **data) -> "LocalWorkspaceManifest":
        return attr.evolve(self, **data)

    def evolve_children_and_mark_updated(self, data) -> "LocalWorkspaceManifest":
        return self.evolve_and_mark_updated(
            children={k: v for k, v in {**self.children, **data}.items() if v is not None}
        )

    def evolve_children(self, data) -> "LocalWorkspaceManifest":
        return self.evolve(
            children={k: v for k, v in {**self.children, **data}.items() if v is not None}
        )

    # Export methods

    def to_remote(self, **data) -> "remote_manifests.WorkspaceManifest":
        return remote_manifests.WorkspaceManifest(
            author=self.author,
            parent_id=self.parent_id,
            version=self.base_version,
            created=self.created,
            updated=self.updated,
            children=self.children,
            **data,
        )

    def asdict(self):
        dct = attr.asdict(self)
        dct.pop("base_manifest")
        props = "base_version", "is_placeholder", "parent_id", "created"
        for name in props:
            dct[name] = getattr(self, name)
        return dct


class LocalWorkspaceManifestSchema(UnknownCheckedSchema):
    format = fields.CheckedConstant(1, required=True)
    type = fields.CheckedConstant("local_folder_manifest", required=True)
    author = fields.DeviceID(required=True)
    base_manifest = fields.Nested(remote_manifests.WorkspaceManifestSchema, required=True)
    need_sync = fields.Boolean(required=True)
    updated = fields.DateTime(required=True)
    children = fields.Map(
        EntryNameField(validate=validate.Length(min=1, max=256)),
        EntryIDField(required=True),
        required=True,
    )

    @post_load
    def make_obj(self, data):
        data.pop("type")
        data.pop("format")
        return LocalWorkspaceManifest(**data)


local_workspace_manifest_serializer = serializer_factory(LocalWorkspaceManifestSchema)


# User manifest


@attr.s(slots=True, frozen=True, auto_attribs=True)
class LocalUserManifest:
    author: DeviceID
    base_version: int = 0
    need_sync: bool = True
    is_placeholder: bool = True
    created: pendulum.Pendulum = None
    updated: pendulum.Pendulum = None
    last_processed_message: int = 0
    workspaces: List[WorkspaceEntry] = attr.ib(converter=tuple, default=())

    def __attrs_post_init__(self):
        if not self.created:
            object.__setattr__(self, "created", pendulum.now())
        if not self.updated:
            object.__setattr__(self, "updated", self.created)

    def to_remote(self, **data) -> "remote_manifests.WorkspaceManifest":
        return remote_manifests.UserManifest(
            author=self.author,
            version=self.base_version,
            created=self.created,
            updated=self.updated,
            last_processed_message=self.last_processed_message,
            workspaces=tuple(self.workspaces),
            **data,
        )

    def get_workspace_entry(self, workspace_id: EntryID) -> WorkspaceEntry:
        return next((w for w in self.workspaces if w.id == workspace_id), None)

    def evolve_and_mark_updated(self, **data) -> "LocalUserManifest":
        if "updated" not in data:
            data["updated"] = pendulum.now()
        data.setdefault("need_sync", True)
        return attr.evolve(self, **data)

    def evolve(self, **data) -> "LocalUserManifest":
        return attr.evolve(self, **data)

    def evolve_workspaces_and_mark_updated(self, *data) -> "LocalUserManifest":
        workspaces = {**{w.id: w for w in self.workspaces}, **{w.id: w for w in data}}
        return self.evolve_and_mark_updated(workspaces=tuple(workspaces.values()))

    def evolve_workspaces(self, *data) -> "LocalUserManifest":
        workspaces = {**{w.id: w for w in self.workspaces}, **{w.id: w for w in data}}
        return self.evolve(workspaces=tuple(workspaces.values()))


# TODO: rename base_version ==> version since we don't have base_author and base_updated ?
class LocalUserManifestSchema(UnknownCheckedSchema):
    format = fields.CheckedConstant(1, required=True)
    type = fields.CheckedConstant("local_user_manifest", required=True)
    author = fields.DeviceID(required=True)
    base_version = fields.Integer(required=True, validate=validate.Range(min=0))
    need_sync = fields.Boolean(required=True)
    is_placeholder = fields.Boolean(required=True)
    created = fields.DateTime(required=True)
    updated = fields.DateTime(required=True)
    last_processed_message = fields.Integer(required=True, validate=validate.Range(min=0))
    workspaces = fields.List(fields.Nested(WorkspaceEntrySchema), required=True)

    @post_load
    def make_obj(self, data):
        data.pop("type")
        data.pop("format")
        return LocalUserManifest(**data)


local_user_manifest_serializer = serializer_factory(LocalUserManifestSchema)


class TypedLocalManifestSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "local_workspace_manifest": LocalWorkspaceManifestSchema,
        "local_user_manifest": LocalUserManifestSchema,
        "local_folder_manifest": LocalFolderManifestSchema,
        "local_file_manifest": LocalFileManifestSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, LocalWorkspaceManifest):
            return "local_workspace_manifest"
        elif isinstance(obj, LocalUserManifest):
            return "local_user_manifest"
        elif isinstance(obj, LocalFolderManifest):
            return "local_folder_manifest"
        elif isinstance(obj, LocalFileManifest):
            return "local_file_manifest"
        else:
            raise RuntimeError(f"Unknown object {obj}")


local_manifest_serializer = serializer_factory(TypedLocalManifestSchema)


LocalManifest = Union[
    LocalFileManifest, LocalFolderManifest, LocalWorkspaceManifest, LocalUserManifest
]


def local_manifest_dumps(manifest: LocalManifest) -> bytes:
    """
    Raises:
        SerdeError
    """
    return local_manifest_serializer.dumps(manifest)


def local_manifest_loads(raw: bytes) -> LocalManifest:
    """
    Raises:
        SerdeError
    """
    return local_manifest_serializer.loads(raw)
