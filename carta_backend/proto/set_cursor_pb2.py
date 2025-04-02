"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'set_cursor.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import region_requirements_pb2 as region__requirements__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10set_cursor.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x19region_requirements.proto"v\n\tSetCursor\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x1b\n\x05point\x18\x02 \x01(\x0b2\x0c.CARTA.Point\x12;\n\x14spatial_requirements\x18\x03 \x01(\x0b2\x1d.CARTA.SetSpatialRequirementsb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'set_cursor_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SETCURSOR']._serialized_start = 66
    _globals['_SETCURSOR']._serialized_end = 184