"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'open_file.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0fopen_file.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0benums.proto"\x9e\x01\n\x08OpenFile\x12\x11\n\tdirectory\x18\x01 \x01(\t\x12\x0c\n\x04file\x18\x02 \x01(\t\x12\x0b\n\x03hdu\x18\x03 \x01(\t\x12\x0f\n\x07file_id\x18\x04 \x01(\x0f\x12&\n\x0brender_mode\x18\x05 \x01(\x0e2\x11.CARTA.RenderMode\x12\x10\n\x08lel_expr\x18\x06 \x01(\x08\x12\x19\n\x11support_aips_beam\x18\x07 \x01(\x08"\xd6\x01\n\x0bOpenFileAck\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07file_id\x18\x02 \x01(\x0f\x12\x0f\n\x07message\x18\x03 \x01(\t\x12"\n\tfile_info\x18\x04 \x01(\x0b2\x0f.CARTA.FileInfo\x123\n\x12file_info_extended\x18\x05 \x01(\x0b2\x17.CARTA.FileInfoExtended\x12\x1a\n\x12file_feature_flags\x18\x06 \x01(\x07\x12\x1f\n\nbeam_table\x18\x07 \x03(\x0b2\x0b.CARTA.Beamb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'open_file_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_OPENFILE']._serialized_start = 52
    _globals['_OPENFILE']._serialized_end = 210
    _globals['_OPENFILEACK']._serialized_start = 213
    _globals['_OPENFILEACK']._serialized_end = 427