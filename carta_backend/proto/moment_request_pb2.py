"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'moment_request.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
from . import open_file_pb2 as open__file__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x14moment_request.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0benums.proto\x1a\x0fopen_file.proto"\x89\x02\n\rMomentRequest\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x1e\n\x07moments\x18\x02 \x03(\x0e2\r.CARTA.Moment\x12\x1f\n\x04axis\x18\x03 \x01(\x0e2\x11.CARTA.MomentAxis\x12\x11\n\tregion_id\x18\x04 \x01(\x0f\x12(\n\x0espectral_range\x18\x05 \x01(\x0b2\x10.CARTA.IntBounds\x12\x1f\n\x04mask\x18\x06 \x01(\x0e2\x11.CARTA.MomentMask\x12\'\n\x0bpixel_range\x18\x07 \x01(\x0b2\x12.CARTA.FloatBounds\x12\x0c\n\x04keep\x18\x08 \x01(\x08\x12\x11\n\trest_freq\x18\t \x01(\x01"n\n\x0eMomentResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12*\n\x0eopen_file_acks\x18\x03 \x03(\x0b2\x12.CARTA.OpenFileAck\x12\x0e\n\x06cancel\x18\x04 \x01(\x08"3\n\x0eMomentProgress\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x10\n\x08progress\x18\x02 \x01(\x02b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'moment_request_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_MOMENTREQUEST']._serialized_start = 74
    _globals['_MOMENTREQUEST']._serialized_end = 339
    _globals['_MOMENTRESPONSE']._serialized_start = 341
    _globals['_MOMENTRESPONSE']._serialized_end = 451
    _globals['_MOMENTPROGRESS']._serialized_start = 453
    _globals['_MOMENTPROGRESS']._serialized_end = 504