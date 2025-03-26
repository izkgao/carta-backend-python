"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'scripting.proto')
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0fscripting.proto\x12\x05CARTA"\x88\x01\n\x10ScriptingRequest\x12\x1c\n\x14scripting_request_id\x18\x01 \x01(\x0f\x12\x0e\n\x06target\x18\x02 \x01(\t\x12\x0e\n\x06action\x18\x03 \x01(\t\x12\x12\n\nparameters\x18\x04 \x01(\t\x12\r\n\x05async\x18\x05 \x01(\x08\x12\x13\n\x0breturn_path\x18\x06 \x01(\t"e\n\x11ScriptingResponse\x12\x1c\n\x14scripting_request_id\x18\x01 \x01(\x0f\x12\x0f\n\x07success\x18\x02 \x01(\x08\x12\x0f\n\x07message\x18\x03 \x01(\t\x12\x10\n\x08response\x18\x04 \x01(\tb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'scripting_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SCRIPTINGREQUEST']._serialized_start = 27
    _globals['_SCRIPTINGREQUEST']._serialized_end = 163
    _globals['_SCRIPTINGRESPONSE']._serialized_start = 165
    _globals['_SCRIPTINGRESPONSE']._serialized_end = 266