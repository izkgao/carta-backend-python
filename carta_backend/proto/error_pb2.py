"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'error.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0berror.proto\x12\x05CARTA\x1a\x0benums.proto"`\n\tErrorData\x12&\n\x08severity\x18\x01 \x01(\x0e2\x14.CARTA.ErrorSeverity\x12\x0c\n\x04tags\x18\x02 \x03(\t\x12\x0f\n\x07message\x18\x03 \x01(\t\x12\x0c\n\x04data\x18\x04 \x01(\tb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'error_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_ERRORDATA']._serialized_start = 35
    _globals['_ERRORDATA']._serialized_end = 131