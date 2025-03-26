"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'save_file.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0fsave_file.proto\x12\x05CARTA\x1a\x0benums.proto"\xf3\x01\n\x08SaveFile\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x1d\n\x15output_file_directory\x18\x02 \x01(\t\x12\x18\n\x10output_file_name\x18\x03 \x01(\t\x12)\n\x10output_file_type\x18\x04 \x01(\x0e2\x0f.CARTA.FileType\x12\x11\n\tregion_id\x18\x05 \x01(\x0f\x12\x10\n\x08channels\x18\x06 \x03(\x0f\x12\x0e\n\x06stokes\x18\x07 \x03(\x0f\x12\x17\n\x0fkeep_degenerate\x18\x08 \x01(\x08\x12\x11\n\trest_freq\x18\t \x01(\x01\x12\x11\n\toverwrite\x18\n \x01(\x08"i\n\x0bSaveFileAck\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x0f\n\x07success\x18\x02 \x01(\x08\x12\x0f\n\x07message\x18\x03 \x01(\t\x12\'\n\x1foverwrite_confirmation_required\x18\x04 \x01(\x08b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'save_file_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SAVEFILE']._serialized_start = 40
    _globals['_SAVEFILE']._serialized_end = 283
    _globals['_SAVEFILEACK']._serialized_start = 285
    _globals['_SAVEFILEACK']._serialized_end = 390