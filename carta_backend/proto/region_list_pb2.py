"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'region_list.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x11region_list.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0benums.proto"V\n\x11RegionListRequest\x12\x11\n\tdirectory\x18\x01 \x01(\t\x12.\n\x0bfilter_mode\x18\x02 \x01(\x0e2\x19.CARTA.FileListFilterMode"\xb7\x01\n\x12RegionListResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x11\n\tdirectory\x18\x03 \x01(\t\x12\x0e\n\x06parent\x18\x04 \x01(\t\x12\x1e\n\x05files\x18\x05 \x03(\x0b2\x0f.CARTA.FileInfo\x12,\n\x0esubdirectories\x18\x06 \x03(\x0b2\x14.CARTA.DirectoryInfo\x12\x0e\n\x06cancel\x18\x07 \x01(\x08b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'region_list_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_REGIONLISTREQUEST']._serialized_start = 53
    _globals['_REGIONLISTREQUEST']._serialized_end = 139
    _globals['_REGIONLISTRESPONSE']._serialized_start = 142
    _globals['_REGIONLISTRESPONSE']._serialized_end = 325