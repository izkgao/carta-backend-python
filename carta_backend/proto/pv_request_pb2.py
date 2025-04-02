"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'pv_request.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import open_file_pb2 as open__file__pb2
from . import pv_preview_pb2 as pv__preview__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10pv_request.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0fopen_file.proto\x1a\x10pv_preview.proto"\xbb\x01\n\tPvRequest\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12\r\n\x05width\x18\x03 \x01(\x0f\x12(\n\x0espectral_range\x18\x04 \x01(\x0b2\x10.CARTA.IntBounds\x12\x0f\n\x07reverse\x18\x05 \x01(\x08\x12\x0c\n\x04keep\x18\x06 \x01(\x08\x122\n\x10preview_settings\x18\x07 \x01(\x0b2\x18.CARTA.PvPreviewSettings"\x95\x01\n\nPvResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12)\n\ropen_file_ack\x18\x03 \x01(\x0b2\x12.CARTA.OpenFileAck\x12*\n\x0cpreview_data\x18\x04 \x01(\x0b2\x14.CARTA.PvPreviewData\x12\x0e\n\x06cancel\x18\x05 \x01(\x08"C\n\nPvProgress\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x12\n\npreview_id\x18\x02 \x01(\x0f\x12\x10\n\x08progress\x18\x03 \x01(\x02b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pv_request_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_PVREQUEST']._serialized_start = 75
    _globals['_PVREQUEST']._serialized_end = 262
    _globals['_PVRESPONSE']._serialized_start = 265
    _globals['_PVRESPONSE']._serialized_end = 414
    _globals['_PVPROGRESS']._serialized_start = 416
    _globals['_PVPROGRESS']._serialized_end = 483