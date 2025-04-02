"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'region_stats.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x12region_stats.proto\x12\x05CARTA\x1a\ndefs.proto"\x82\x01\n\x0fRegionStatsData\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12\x0f\n\x07channel\x18\x03 \x01(\x0f\x12\x0e\n\x06stokes\x18\x04 \x01(\x0f\x12*\n\nstatistics\x18\x05 \x03(\x0b2\x16.CARTA.StatisticsValueb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'region_stats_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_REGIONSTATSDATA']._serialized_start = 42
    _globals['_REGIONSTATSDATA']._serialized_end = 172