"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'catalog_file_info.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x17catalog_file_info.proto\x12\x05CARTA\x1a\ndefs.proto"9\n\x16CatalogFileInfoRequest\x12\x11\n\tdirectory\x18\x01 \x01(\t\x12\x0c\n\x04name\x18\x02 \x01(\t"\x8d\x01\n\x17CatalogFileInfoResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12)\n\tfile_info\x18\x03 \x01(\x0b2\x16.CARTA.CatalogFileInfo\x12%\n\x07headers\x18\x04 \x03(\x0b2\x14.CARTA.CatalogHeaderb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'catalog_file_info_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_CATALOGFILEINFOREQUEST']._serialized_start = 46
    _globals['_CATALOGFILEINFOREQUEST']._serialized_end = 103
    _globals['_CATALOGFILEINFORESPONSE']._serialized_start = 106
    _globals['_CATALOGFILEINFORESPONSE']._serialized_end = 247