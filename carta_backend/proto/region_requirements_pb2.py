"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'region_requirements.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x19region_requirements.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0benums.proto"\xc4\x01\n\x14SetStatsRequirements\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12>\n\rstats_configs\x18\x03 \x03(\x0b2\'.CARTA.SetStatsRequirements.StatsConfig\x1aH\n\x0bStatsConfig\x12\x12\n\ncoordinate\x18\x01 \x01(\t\x12%\n\x0bstats_types\x18\x02 \x03(\x0e2\x10.CARTA.StatsType"j\n\x18SetHistogramRequirements\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12*\n\nhistograms\x18\x03 \x03(\x0b2\x16.CARTA.HistogramConfig"\xe0\x01\n\x16SetSpatialRequirements\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12E\n\x10spatial_profiles\x18\x03 \x03(\x0b2+.CARTA.SetSpatialRequirements.SpatialConfig\x1a[\n\rSpatialConfig\x12\x12\n\ncoordinate\x18\x01 \x01(\t\x12\r\n\x05start\x18\x02 \x01(\x0f\x12\x0b\n\x03end\x18\x03 \x01(\x0f\x12\x0b\n\x03mip\x18\x04 \x01(\x0f\x12\r\n\x05width\x18\x05 \x01(\x0f"\xd4\x01\n\x17SetSpectralRequirements\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12H\n\x11spectral_profiles\x18\x03 \x03(\x0b2-.CARTA.SetSpectralRequirements.SpectralConfig\x1aK\n\x0eSpectralConfig\x12\x12\n\ncoordinate\x18\x01 \x01(\t\x12%\n\x0bstats_types\x18\x02 \x03(\x0e2\x10.CARTA.StatsTypeb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'region_requirements_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SETSTATSREQUIREMENTS']._serialized_start = 62
    _globals['_SETSTATSREQUIREMENTS']._serialized_end = 258
    _globals['_SETSTATSREQUIREMENTS_STATSCONFIG']._serialized_start = 186
    _globals['_SETSTATSREQUIREMENTS_STATSCONFIG']._serialized_end = 258
    _globals['_SETHISTOGRAMREQUIREMENTS']._serialized_start = 260
    _globals['_SETHISTOGRAMREQUIREMENTS']._serialized_end = 366
    _globals['_SETSPATIALREQUIREMENTS']._serialized_start = 369
    _globals['_SETSPATIALREQUIREMENTS']._serialized_end = 593
    _globals['_SETSPATIALREQUIREMENTS_SPATIALCONFIG']._serialized_start = 502
    _globals['_SETSPATIALREQUIREMENTS_SPATIALCONFIG']._serialized_end = 593
    _globals['_SETSPECTRALREQUIREMENTS']._serialized_start = 596
    _globals['_SETSPECTRALREQUIREMENTS']._serialized_end = 808
    _globals['_SETSPECTRALREQUIREMENTS_SPECTRALCONFIG']._serialized_start = 733
    _globals['_SETSPECTRALREQUIREMENTS_SPECTRALCONFIG']._serialized_end = 808