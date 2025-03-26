"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'remote_file_request.proto')
_sym_db = _symbol_database.Default()
from . import open_file_pb2 as open__file__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x19remote_file_request.proto\x12\x05CARTA\x1a\x0fopen_file.proto"\xd2\x01\n\x11RemoteFileRequest\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x0c\n\x04hips\x18\x02 \x01(\t\x12\x0b\n\x03wcs\x18\x03 \x01(\t\x12\r\n\x05width\x18\x04 \x01(\x05\x12\x0e\n\x06height\x18\x05 \x01(\x05\x12\x12\n\nprojection\x18\x06 \x01(\t\x12\x0b\n\x03fov\x18\x07 \x01(\x02\x12\n\n\x02ra\x18\x08 \x01(\x02\x12\x0b\n\x03dec\x18\t \x01(\x02\x12\x10\n\x08coordsys\x18\n \x01(\t\x12\x16\n\x0erotation_angle\x18\x0b \x01(\x02\x12\x0e\n\x06object\x18\x0c \x01(\t"a\n\x12RemoteFileResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12)\n\ropen_file_ack\x18\x03 \x01(\x0b2\x12.CARTA.OpenFileAckb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'remote_file_request_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_REMOTEFILEREQUEST']._serialized_start = 54
    _globals['_REMOTEFILEREQUEST']._serialized_end = 264
    _globals['_REMOTEFILERESPONSE']._serialized_start = 266
    _globals['_REMOTEFILERESPONSE']._serialized_end = 363