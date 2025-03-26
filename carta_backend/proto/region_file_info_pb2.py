"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'region_file_info.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x16region_file_info.proto\x12\x05CARTA\x1a\ndefs.proto"8\n\x15RegionFileInfoRequest\x12\x11\n\tdirectory\x18\x01 \x01(\t\x12\x0c\n\x04file\x18\x02 \x01(\t"p\n\x16RegionFileInfoResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12"\n\tfile_info\x18\x03 \x01(\x0b2\x0f.CARTA.FileInfo\x12\x10\n\x08contents\x18\x04 \x03(\tb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'region_file_info_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_REGIONFILEINFOREQUEST']._serialized_start = 45
    _globals['_REGIONFILEINFOREQUEST']._serialized_end = 101
    _globals['_REGIONFILEINFORESPONSE']._serialized_start = 103
    _globals['_REGIONFILEINFORESPONSE']._serialized_end = 215