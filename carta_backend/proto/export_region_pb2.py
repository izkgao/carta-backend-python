"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'export_region.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13export_region.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0benums.proto"\xa4\x02\n\x0cExportRegion\x12\x1d\n\x04type\x18\x01 \x01(\x0e2\x0f.CARTA.FileType\x12)\n\ncoord_type\x18\x02 \x01(\x0e2\x15.CARTA.CoordinateType\x12\x0f\n\x07file_id\x18\x03 \x01(\x0f\x12<\n\rregion_styles\x18\x04 \x03(\x0b2%.CARTA.ExportRegion.RegionStylesEntry\x12\x11\n\tdirectory\x18\x05 \x01(\t\x12\x0c\n\x04file\x18\x06 \x01(\t\x12\x11\n\toverwrite\x18\x07 \x01(\x08\x1aG\n\x11RegionStylesEntry\x12\x0b\n\x03key\x18\x01 \x01(\x0f\x12!\n\x05value\x18\x02 \x01(\x0b2\x12.CARTA.RegionStyle:\x028\x01"n\n\x0fExportRegionAck\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x10\n\x08contents\x18\x03 \x03(\t\x12\'\n\x1foverwrite_confirmation_required\x18\x04 \x01(\x08b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'export_region_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_EXPORTREGION_REGIONSTYLESENTRY']._loaded_options = None
    _globals['_EXPORTREGION_REGIONSTYLESENTRY']._serialized_options = b'8\x01'
    _globals['_EXPORTREGION']._serialized_start = 56
    _globals['_EXPORTREGION']._serialized_end = 348
    _globals['_EXPORTREGION_REGIONSTYLESENTRY']._serialized_start = 277
    _globals['_EXPORTREGION_REGIONSTYLESENTRY']._serialized_end = 348
    _globals['_EXPORTREGIONACK']._serialized_start = 350
    _globals['_EXPORTREGIONACK']._serialized_end = 460