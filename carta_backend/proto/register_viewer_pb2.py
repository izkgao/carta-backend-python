"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'register_viewer.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x15register_viewer.proto\x12\x05CARTA\x1a\x0benums.proto"S\n\x0eRegisterViewer\x12\x12\n\nsession_id\x18\x01 \x01(\x07\x12\x0f\n\x07api_key\x18\x02 \x01(\t\x12\x1c\n\x14client_feature_flags\x18\x03 \x01(\x07"\x88\x04\n\x11RegisterViewerAck\x12\x12\n\nsession_id\x18\x01 \x01(\x07\x12\x0f\n\x07success\x18\x02 \x01(\x08\x12\x0f\n\x07message\x18\x03 \x01(\t\x12(\n\x0csession_type\x18\x04 \x01(\x0e2\x12.CARTA.SessionType\x12\x1c\n\x14server_feature_flags\x18\x05 \x01(\x07\x12G\n\x10user_preferences\x18\x06 \x03(\x0b2-.CARTA.RegisterViewerAck.UserPreferencesEntry\x12?\n\x0cuser_layouts\x18\x07 \x03(\x0b2).CARTA.RegisterViewerAck.UserLayoutsEntry\x12G\n\x10platform_strings\x18\x08 \x03(\x0b2-.CARTA.RegisterViewerAck.PlatformStringsEntry\x1a6\n\x14UserPreferencesEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x028\x01\x1a2\n\x10UserLayoutsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x028\x01\x1a6\n\x14PlatformStringsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x028\x01b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'register_viewer_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_REGISTERVIEWERACK_USERPREFERENCESENTRY']._loaded_options = None
    _globals['_REGISTERVIEWERACK_USERPREFERENCESENTRY']._serialized_options = b'8\x01'
    _globals['_REGISTERVIEWERACK_USERLAYOUTSENTRY']._loaded_options = None
    _globals['_REGISTERVIEWERACK_USERLAYOUTSENTRY']._serialized_options = b'8\x01'
    _globals['_REGISTERVIEWERACK_PLATFORMSTRINGSENTRY']._loaded_options = None
    _globals['_REGISTERVIEWERACK_PLATFORMSTRINGSENTRY']._serialized_options = b'8\x01'
    _globals['_REGISTERVIEWER']._serialized_start = 45
    _globals['_REGISTERVIEWER']._serialized_end = 128
    _globals['_REGISTERVIEWERACK']._serialized_start = 131
    _globals['_REGISTERVIEWERACK']._serialized_end = 651
    _globals['_REGISTERVIEWERACK_USERPREFERENCESENTRY']._serialized_start = 489
    _globals['_REGISTERVIEWERACK_USERPREFERENCESENTRY']._serialized_end = 543
    _globals['_REGISTERVIEWERACK_USERLAYOUTSENTRY']._serialized_start = 545
    _globals['_REGISTERVIEWERACK_USERLAYOUTSENTRY']._serialized_end = 595
    _globals['_REGISTERVIEWERACK_PLATFORMSTRINGSENTRY']._serialized_start = 597
    _globals['_REGISTERVIEWERACK_PLATFORMSTRINGSENTRY']._serialized_end = 651