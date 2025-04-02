"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'pv_preview.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10pv_preview.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0benums.proto"\xbc\x02\n\rPvPreviewData\x12\x12\n\npreview_id\x18\x01 \x01(\x0f\x12+\n\nimage_info\x18\x02 \x01(\x0b2\x17.CARTA.FileInfoExtended\x12\x12\n\nimage_data\x18\x03 \x01(\x0c\x12\x15\n\rnan_encodings\x18\x04 \x01(\x0c\x12\r\n\x05width\x18\x05 \x01(\x0f\x12\x0e\n\x06height\x18\x06 \x01(\x0f\x120\n\x10compression_type\x18\x07 \x01(\x0e2\x16.CARTA.CompressionType\x12\x1b\n\x13compression_quality\x18\x08 \x01(\x02\x12,\n\x10histogram_bounds\x18\t \x01(\x0b2\x12.CARTA.FloatBounds\x12#\n\thistogram\x18\n \x01(\x0b2\x10.CARTA.Histogramb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pv_preview_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_PVPREVIEWDATA']._serialized_start = 53
    _globals['_PVPREVIEWDATA']._serialized_end = 369