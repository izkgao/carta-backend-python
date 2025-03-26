"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'raster_tile.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x11raster_tile.proto\x12\x05CARTA\x1a\x0benums.proto\x1a\ndefs.proto"\x8f\x01\n\x0eRasterTileSync\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x0f\n\x07channel\x18\x02 \x01(\x0f\x12\x0e\n\x06stokes\x18\x03 \x01(\x0f\x12\x0f\n\x07sync_id\x18\x04 \x01(\x0f\x12\x14\n\x0canimation_id\x18\x05 \x01(\x0f\x12\x12\n\ntile_count\x18\x06 \x01(\x0f\x12\x10\n\x08end_sync\x18\x07 \x01(\x08"\xd8\x01\n\x0eRasterTileData\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x0f\n\x07channel\x18\x02 \x01(\x0f\x12\x0e\n\x06stokes\x18\x03 \x01(\x0f\x120\n\x10compression_type\x18\x04 \x01(\x0e2\x16.CARTA.CompressionType\x12\x1b\n\x13compression_quality\x18\x05 \x01(\x02\x12\x0f\n\x07sync_id\x18\x06 \x01(\x0f\x12\x14\n\x0canimation_id\x18\x07 \x01(\x0f\x12\x1e\n\x05tiles\x18\x08 \x03(\x0b2\x0f.CARTA.TileDatab\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'raster_tile_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_RASTERTILESYNC']._serialized_start = 54
    _globals['_RASTERTILESYNC']._serialized_end = 197
    _globals['_RASTERTILEDATA']._serialized_start = 200
    _globals['_RASTERTILEDATA']._serialized_end = 416