"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'vector_overlay.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x14vector_overlay.proto\x12\x05CARTA\x1a\x0benums.proto\x1a\ndefs.proto"\xcc\x02\n\x1aSetVectorOverlayParameters\x12\x0f\n\x07file_id\x18\x01 \x01(\x07\x12(\n\x0cimage_bounds\x18\x03 \x01(\x0b2\x12.CARTA.ImageBounds\x12\x18\n\x10smoothing_factor\x18\x04 \x01(\x07\x12\x12\n\nfractional\x18\x05 \x01(\x08\x12\x11\n\tthreshold\x18\x06 \x01(\x01\x12\x11\n\tdebiasing\x18\x07 \x01(\x08\x12\x0f\n\x07q_error\x18\x08 \x01(\x01\x12\x0f\n\x07u_error\x18\t \x01(\x01\x12\x18\n\x10stokes_intensity\x18\n \x01(\x0f\x12\x14\n\x0cstokes_angle\x18\x0b \x01(\x0f\x120\n\x10compression_type\x18\x0c \x01(\x0e2\x16.CARTA.CompressionType\x12\x1b\n\x13compression_quality\x18\r \x01(\x02b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'vector_overlay_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SETVECTOROVERLAYPARAMETERS']._serialized_start = 57
    _globals['_SETVECTOROVERLAYPARAMETERS']._serialized_end = 389