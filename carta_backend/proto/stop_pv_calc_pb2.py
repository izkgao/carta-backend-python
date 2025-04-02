"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'stop_pv_calc.proto')
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x12stop_pv_calc.proto\x12\x05CARTA"\x1d\n\nStopPvCalc\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f"#\n\rStopPvPreview\x12\x12\n\npreview_id\x18\x01 \x01(\x0f"$\n\x0eClosePvPreview\x12\x12\n\npreview_id\x18\x01 \x01(\x0fb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'stop_pv_calc_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_STOPPVCALC']._serialized_start = 29
    _globals['_STOPPVCALC']._serialized_end = 58
    _globals['_STOPPVPREVIEW']._serialized_start = 60
    _globals['_STOPPVPREVIEW']._serialized_end = 95
    _globals['_CLOSEPVPREVIEW']._serialized_start = 97
    _globals['_CLOSEPVPREVIEW']._serialized_end = 133