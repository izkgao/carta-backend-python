"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'spatial_profile.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x15spatial_profile.proto\x12\x05CARTA\x1a\ndefs.proto"\xa7\x01\n\x12SpatialProfileData\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12\t\n\x01x\x18\x03 \x01(\x0f\x12\t\n\x01y\x18\x04 \x01(\x0f\x12\x0f\n\x07channel\x18\x05 \x01(\x0f\x12\x0e\n\x06stokes\x18\x06 \x01(\x0f\x12\r\n\x05value\x18\x07 \x01(\x02\x12\'\n\x08profiles\x18\x08 \x03(\x0b2\x15.CARTA.SpatialProfileb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'spatial_profile_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SPATIALPROFILEDATA']._serialized_start = 45
    _globals['_SPATIALPROFILEDATA']._serialized_end = 212