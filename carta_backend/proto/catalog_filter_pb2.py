"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'catalog_filter.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x14catalog_filter.proto\x12\x05CARTA\x1a\x0benums.proto\x1a\ndefs.proto"\xbc\x02\n\x14CatalogFilterRequest\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x16\n\x0ecolumn_indices\x18\x02 \x03(\x05\x12+\n\x0efilter_configs\x18\x03 \x03(\x0b2\x13.CARTA.FilterConfig\x12\x18\n\x10subset_data_size\x18\x04 \x01(\x0f\x12\x1a\n\x12subset_start_index\x18\x05 \x01(\x0f\x12/\n\x0cimage_bounds\x18\x06 \x01(\x0b2\x19.CARTA.CatalogImageBounds\x12\x15\n\rimage_file_id\x18\x07 \x01(\x0f\x12\x11\n\tregion_id\x18\x08 \x01(\x0f\x12\x13\n\x0bsort_column\x18\t \x01(\t\x12(\n\x0csorting_type\x18\n \x01(\x0e2\x12.CARTA.SortingType"\xcc\x02\n\x15CatalogFilterResponse\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x15\n\rimage_file_id\x18\x02 \x01(\x0f\x12\x11\n\tregion_id\x18\x03 \x01(\x0f\x12:\n\x07columns\x18\x04 \x03(\x0b2).CARTA.CatalogFilterResponse.ColumnsEntry\x12\x18\n\x10subset_data_size\x18\x05 \x01(\x0f\x12\x18\n\x10subset_end_index\x18\x06 \x01(\x0f\x12\x10\n\x08progress\x18\x07 \x01(\x02\x12\x18\n\x10filter_data_size\x18\x08 \x01(\x0f\x12\x19\n\x11request_end_index\x18\t \x01(\x0f\x1aA\n\x0cColumnsEntry\x12\x0b\n\x03key\x18\x01 \x01(\x07\x12 \n\x05value\x18\x02 \x01(\x0b2\x11.CARTA.ColumnData:\x028\x01b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'catalog_filter_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_CATALOGFILTERRESPONSE_COLUMNSENTRY']._loaded_options = None
    _globals['_CATALOGFILTERRESPONSE_COLUMNSENTRY']._serialized_options = b'8\x01'
    _globals['_CATALOGFILTERREQUEST']._serialized_start = 57
    _globals['_CATALOGFILTERREQUEST']._serialized_end = 373
    _globals['_CATALOGFILTERRESPONSE']._serialized_start = 376
    _globals['_CATALOGFILTERRESPONSE']._serialized_end = 708
    _globals['_CATALOGFILTERRESPONSE_COLUMNSENTRY']._serialized_start = 643
    _globals['_CATALOGFILTERRESPONSE_COLUMNSENTRY']._serialized_end = 708