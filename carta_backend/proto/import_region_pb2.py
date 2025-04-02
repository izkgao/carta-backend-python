"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'import_region.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13import_region.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0benums.proto"r\n\x0cImportRegion\x12\x10\n\x08group_id\x18\x01 \x01(\x0f\x12\x1d\n\x04type\x18\x02 \x01(\x0e2\x0f.CARTA.FileType\x12\x11\n\tdirectory\x18\x03 \x01(\t\x12\x0c\n\x04file\x18\x04 \x01(\t\x12\x10\n\x08contents\x18\x05 \x03(\t"\xb6\x02\n\x0fImportRegionAck\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x124\n\x07regions\x18\x03 \x03(\x0b2#.CARTA.ImportRegionAck.RegionsEntry\x12?\n\rregion_styles\x18\x04 \x03(\x0b2(.CARTA.ImportRegionAck.RegionStylesEntry\x1aA\n\x0cRegionsEntry\x12\x0b\n\x03key\x18\x01 \x01(\x0f\x12 \n\x05value\x18\x02 \x01(\x0b2\x11.CARTA.RegionInfo:\x028\x01\x1aG\n\x11RegionStylesEntry\x12\x0b\n\x03key\x18\x01 \x01(\x0f\x12!\n\x05value\x18\x02 \x01(\x0b2\x12.CARTA.RegionStyle:\x028\x01b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'import_region_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_IMPORTREGIONACK_REGIONSENTRY']._loaded_options = None
    _globals['_IMPORTREGIONACK_REGIONSENTRY']._serialized_options = b'8\x01'
    _globals['_IMPORTREGIONACK_REGIONSTYLESENTRY']._loaded_options = None
    _globals['_IMPORTREGIONACK_REGIONSTYLESENTRY']._serialized_options = b'8\x01'
    _globals['_IMPORTREGION']._serialized_start = 55
    _globals['_IMPORTREGION']._serialized_end = 169
    _globals['_IMPORTREGIONACK']._serialized_start = 172
    _globals['_IMPORTREGIONACK']._serialized_end = 482
    _globals['_IMPORTREGIONACK_REGIONSENTRY']._serialized_start = 344
    _globals['_IMPORTREGIONACK_REGIONSENTRY']._serialized_end = 409
    _globals['_IMPORTREGIONACK_REGIONSTYLESENTRY']._serialized_start = 411
    _globals['_IMPORTREGIONACK_REGIONSTYLESENTRY']._serialized_end = 482