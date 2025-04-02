"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'open_catalog_file.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x17open_catalog_file.proto\x12\x05CARTA\x1a\ndefs.proto"^\n\x0fOpenCatalogFile\x12\x11\n\tdirectory\x18\x01 \x01(\t\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x0f\n\x07file_id\x18\x03 \x01(\x0f\x12\x19\n\x11preview_data_size\x18\x04 \x01(\x0f"\xb5\x02\n\x12OpenCatalogFileAck\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x0f\n\x07file_id\x18\x03 \x01(\x0f\x12)\n\tfile_info\x18\x04 \x01(\x0b2\x16.CARTA.CatalogFileInfo\x12\x11\n\tdata_size\x18\x05 \x01(\x0f\x12%\n\x07headers\x18\x06 \x03(\x0b2\x14.CARTA.CatalogHeader\x12@\n\x0cpreview_data\x18\x07 \x03(\x0b2*.CARTA.OpenCatalogFileAck.PreviewDataEntry\x1aE\n\x10PreviewDataEntry\x12\x0b\n\x03key\x18\x01 \x01(\x07\x12 \n\x05value\x18\x02 \x01(\x0b2\x11.CARTA.ColumnData:\x028\x01"#\n\x10CloseCatalogFile\x12\x0f\n\x07file_id\x18\x01 \x01(\x0fb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'open_catalog_file_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_OPENCATALOGFILEACK_PREVIEWDATAENTRY']._loaded_options = None
    _globals['_OPENCATALOGFILEACK_PREVIEWDATAENTRY']._serialized_options = b'8\x01'
    _globals['_OPENCATALOGFILE']._serialized_start = 46
    _globals['_OPENCATALOGFILE']._serialized_end = 140
    _globals['_OPENCATALOGFILEACK']._serialized_start = 143
    _globals['_OPENCATALOGFILEACK']._serialized_end = 452
    _globals['_OPENCATALOGFILEACK_PREVIEWDATAENTRY']._serialized_start = 383
    _globals['_OPENCATALOGFILEACK_PREVIEWDATAENTRY']._serialized_end = 452
    _globals['_CLOSECATALOGFILE']._serialized_start = 454
    _globals['_CLOSECATALOGFILE']._serialized_end = 489