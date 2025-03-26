"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'set_image_channels.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import tiles_pb2 as tiles__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x18set_image_channels.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0btiles.proto"\xe4\x01\n\x10SetImageChannels\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x0f\n\x07channel\x18\x02 \x01(\x0f\x12\x0e\n\x06stokes\x18\x03 \x01(\x0f\x12/\n\x0erequired_tiles\x18\x04 \x01(\x0b2\x17.CARTA.AddRequiredTiles\x12\'\n\rchannel_range\x18\x05 \x01(\x0b2\x10.CARTA.IntBounds\x12\'\n\rcurrent_range\x18\x06 \x01(\x0b2\x10.CARTA.IntBounds\x12\x1b\n\x13channel_map_enabled\x18\x07 \x01(\x08b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'set_image_channels_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SETIMAGECHANNELS']._serialized_start = 61
    _globals['_SETIMAGECHANNELS']._serialized_end = 289