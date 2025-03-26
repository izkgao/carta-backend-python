"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'tiles.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0btiles.proto\x12\x05CARTA\x1a\x0benums.proto"\x98\x01\n\x10AddRequiredTiles\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\r\n\x05tiles\x18\x02 \x03(\x0f\x120\n\x10compression_type\x18\x03 \x01(\x0e2\x16.CARTA.CompressionType\x12\x1b\n\x13compression_quality\x18\x04 \x01(\x02\x12\x15\n\rcurrent_tiles\x18\x05 \x03(\x0f"5\n\x13RemoveRequiredTiles\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\r\n\x05tiles\x18\x02 \x03(\x0fb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'tiles_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_ADDREQUIREDTILES']._serialized_start = 36
    _globals['_ADDREQUIREDTILES']._serialized_end = 188
    _globals['_REMOVEREQUIREDTILES']._serialized_start = 190
    _globals['_REMOVEREQUIREDTILES']._serialized_end = 243