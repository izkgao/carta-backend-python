"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'animation.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import tiles_pb2 as tiles__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0fanimation.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0btiles.proto"\xe0\x03\n\x0eStartAnimation\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12*\n\x0bfirst_frame\x18\x02 \x01(\x0b2\x15.CARTA.AnimationFrame\x12*\n\x0bstart_frame\x18\x03 \x01(\x0b2\x15.CARTA.AnimationFrame\x12)\n\nlast_frame\x18\x04 \x01(\x0b2\x15.CARTA.AnimationFrame\x12*\n\x0bdelta_frame\x18\x05 \x01(\x0b2\x15.CARTA.AnimationFrame\x12\x12\n\nframe_rate\x18\x06 \x01(\x0f\x12\x0f\n\x07looping\x18\x07 \x01(\x08\x12\x0f\n\x07reverse\x18\x08 \x01(\x08\x12/\n\x0erequired_tiles\x18\t \x01(\x0b2\x17.CARTA.AddRequiredTiles\x12@\n\x0ematched_frames\x18\n \x03(\x0b2(.CARTA.StartAnimation.MatchedFramesEntry\x12\x16\n\x0estokes_indices\x18\x0b \x03(\x0f\x1aM\n\x12MatchedFramesEntry\x12\x0b\n\x03key\x18\x01 \x01(\x0f\x12&\n\x05value\x18\x02 \x01(\x0b2\x17.CARTA.MatchedFrameList:\x028\x01"K\n\x11StartAnimationAck\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x14\n\x0canimation_id\x18\x03 \x01(\x0f"\x7f\n\x14AnimationFlowControl\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12-\n\x0ereceived_frame\x18\x02 \x01(\x0b2\x15.CARTA.AnimationFrame\x12\x14\n\x0canimation_id\x18\x03 \x01(\x0f\x12\x11\n\ttimestamp\x18\x04 \x01(\x10"J\n\rStopAnimation\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12(\n\tend_frame\x18\x02 \x01(\x0b2\x15.CARTA.AnimationFrameb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'animation_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_STARTANIMATION_MATCHEDFRAMESENTRY']._loaded_options = None
    _globals['_STARTANIMATION_MATCHEDFRAMESENTRY']._serialized_options = b'8\x01'
    _globals['_STARTANIMATION']._serialized_start = 52
    _globals['_STARTANIMATION']._serialized_end = 532
    _globals['_STARTANIMATION_MATCHEDFRAMESENTRY']._serialized_start = 455
    _globals['_STARTANIMATION_MATCHEDFRAMESENTRY']._serialized_end = 532
    _globals['_STARTANIMATIONACK']._serialized_start = 534
    _globals['_STARTANIMATIONACK']._serialized_end = 609
    _globals['_ANIMATIONFLOWCONTROL']._serialized_start = 611
    _globals['_ANIMATIONFLOWCONTROL']._serialized_end = 738
    _globals['_STOPANIMATION']._serialized_start = 740
    _globals['_STOPANIMATION']._serialized_end = 814