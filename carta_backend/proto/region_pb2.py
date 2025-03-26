"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'region.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0cregion.proto\x12\x05CARTA\x1a\ndefs.proto"o\n\tSetRegion\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12&\n\x0bregion_info\x18\x03 \x01(\x0b2\x11.CARTA.RegionInfo\x12\x16\n\x0epreview_region\x18\x04 \x01(\x08"C\n\x0cSetRegionAck\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x11\n\tregion_id\x18\x03 \x01(\x0f"!\n\x0cRemoveRegion\x12\x11\n\tregion_id\x18\x01 \x01(\x0fb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'region_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SETREGION']._serialized_start = 35
    _globals['_SETREGION']._serialized_end = 146
    _globals['_SETREGIONACK']._serialized_start = 148
    _globals['_SETREGIONACK']._serialized_end = 215
    _globals['_REMOVEREGION']._serialized_start = 217
    _globals['_REMOVEREGION']._serialized_end = 250