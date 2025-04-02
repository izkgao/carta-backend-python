"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'file_info.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0ffile_info.proto\x12\x05CARTA\x1a\ndefs.proto"Z\n\x0fFileInfoRequest\x12\x11\n\tdirectory\x18\x01 \x01(\t\x12\x0c\n\x04file\x18\x02 \x01(\t\x12\x0b\n\x03hdu\x18\x03 \x01(\t\x12\x19\n\x11support_aips_beam\x18\x04 \x01(\x08"\xf5\x01\n\x10FileInfoResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12"\n\tfile_info\x18\x03 \x01(\x0b2\x0f.CARTA.FileInfo\x12I\n\x12file_info_extended\x18\x04 \x03(\x0b2-.CARTA.FileInfoResponse.FileInfoExtendedEntry\x1aP\n\x15FileInfoExtendedEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12&\n\x05value\x18\x02 \x01(\x0b2\x17.CARTA.FileInfoExtended:\x028\x01b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'file_info_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_FILEINFORESPONSE_FILEINFOEXTENDEDENTRY']._loaded_options = None
    _globals['_FILEINFORESPONSE_FILEINFOEXTENDEDENTRY']._serialized_options = b'8\x01'
    _globals['_FILEINFOREQUEST']._serialized_start = 38
    _globals['_FILEINFOREQUEST']._serialized_end = 128
    _globals['_FILEINFORESPONSE']._serialized_start = 131
    _globals['_FILEINFORESPONSE']._serialized_end = 376
    _globals['_FILEINFORESPONSE_FILEINFOEXTENDEDENTRY']._serialized_start = 296
    _globals['_FILEINFORESPONSE_FILEINFOEXTENDEDENTRY']._serialized_end = 376