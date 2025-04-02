"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'contour.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\rcontour.proto\x12\x05CARTA\x1a\x0benums.proto\x1a\ndefs.proto"\xbf\x02\n\x14SetContourParameters\x12\x0f\n\x07file_id\x18\x01 \x01(\x07\x12\x19\n\x11reference_file_id\x18\x02 \x01(\x07\x12(\n\x0cimage_bounds\x18\x03 \x01(\x0b2\x12.CARTA.ImageBounds\x12\x0e\n\x06levels\x18\x04 \x03(\x01\x12,\n\x0esmoothing_mode\x18\x05 \x01(\x0e2\x14.CARTA.SmoothingMode\x12\x18\n\x10smoothing_factor\x18\x06 \x01(\x05\x12\x19\n\x11decimation_factor\x18\x07 \x01(\x05\x12\x19\n\x11compression_level\x18\x08 \x01(\x05\x12\x1a\n\x12contour_chunk_size\x18\t \x01(\x05\x12\'\n\rchannel_range\x18\n \x01(\x0b2\x10.CARTA.IntBoundsb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'contour_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SETCONTOURPARAMETERS']._serialized_start = 50
    _globals['_SETCONTOURPARAMETERS']._serialized_end = 369