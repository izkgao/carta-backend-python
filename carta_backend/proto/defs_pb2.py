"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'defs.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\ndefs.proto\x12\x05CARTA\x1a\x0benums.proto"\x1d\n\x05Point\x12\t\n\x01x\x18\x01 \x01(\x02\x12\t\n\x01y\x18\x02 \x01(\x02"#\n\x0bDoublePoint\x12\t\n\x01x\x18\x01 \x01(\x01\x12\t\n\x01y\x18\x02 \x01(\x01"e\n\x08FileInfo\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x1d\n\x04type\x18\x02 \x01(\x0e2\x0f.CARTA.FileType\x12\x0c\n\x04size\x18\x03 \x01(\x10\x12\x10\n\x08HDU_list\x18\x04 \x03(\t\x12\x0c\n\x04date\x18\x05 \x01(\x10"?\n\rDirectoryInfo\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x12\n\nitem_count\x18\x02 \x01(\x0f\x12\x0c\n\x04date\x18\x03 \x01(\x10"\xfd\x01\n\x10FileInfoExtended\x12\x12\n\ndimensions\x18\x01 \x01(\x0f\x12\r\n\x05width\x18\x02 \x01(\x0f\x12\x0e\n\x06height\x18\x03 \x01(\x0f\x12\r\n\x05depth\x18\x04 \x01(\x0f\x12\x0e\n\x06stokes\x18\x05 \x01(\x0f\x12\x13\n\x0bstokes_vals\x18\x06 \x03(\t\x12*\n\x0eheader_entries\x18\x07 \x03(\x0b2\x12.CARTA.HeaderEntry\x12,\n\x10computed_entries\x18\x08 \x03(\x0b2\x12.CARTA.HeaderEntry\x12(\n\x0caxes_numbers\x18\t \x01(\x0b2\x12.CARTA.AxesNumbers"x\n\x0bHeaderEntry\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t\x12$\n\nentry_type\x18\x03 \x01(\x0e2\x10.CARTA.EntryType\x12\x15\n\rnumeric_value\x18\x04 \x01(\x01\x12\x0f\n\x07comment\x18\x05 \x01(\t"d\n\x0bAxesNumbers\x12\x11\n\tspatial_x\x18\x01 \x01(\x0f\x12\x11\n\tspatial_y\x18\x02 \x01(\x0f\x12\x10\n\x08spectral\x18\x03 \x01(\x0f\x12\x0e\n\x06stokes\x18\x04 \x01(\x0f\x12\r\n\x05depth\x18\x05 \x01(\x0f"%\n\tIntBounds\x12\x0b\n\x03min\x18\x01 \x01(\x0f\x12\x0b\n\x03max\x18\x02 \x01(\x0f"\'\n\x0bFloatBounds\x12\x0b\n\x03min\x18\x01 \x01(\x02\x12\x0b\n\x03max\x18\x02 \x01(\x02"(\n\x0cDoubleBounds\x12\x0b\n\x03min\x18\x01 \x01(\x01\x12\x0b\n\x03max\x18\x02 \x01(\x01"I\n\x0bImageBounds\x12\r\n\x05x_min\x18\x01 \x01(\x0f\x12\r\n\x05x_max\x18\x02 \x01(\x0f\x12\r\n\x05y_min\x18\x03 \x01(\x0f\x12\r\n\x05y_max\x18\x04 \x01(\x0f"1\n\x0eAnimationFrame\x12\x0f\n\x07channel\x18\x01 \x01(\x0f\x12\x0e\n\x06stokes\x18\x02 \x01(\x0f"\x91\x01\n\x0eSpatialProfile\x12\r\n\x05start\x18\x01 \x01(\x0f\x12\x0b\n\x03end\x18\x02 \x01(\x0f\x12\x17\n\x0fraw_values_fp32\x18\x03 \x01(\x0c\x12\x12\n\ncoordinate\x18\x04 \x01(\t\x12\x0b\n\x03mip\x18\x05 \x01(\x0f\x12)\n\tline_axis\x18\x06 \x01(\x0b2\x16.CARTA.LineProfileAxis"w\n\x0fLineProfileAxis\x12)\n\taxis_type\x18\x01 \x01(\x0e2\x16.CARTA.ProfileAxisType\x12\r\n\x05crpix\x18\x02 \x01(\x02\x12\r\n\x05crval\x18\x03 \x01(\x02\x12\r\n\x05cdelt\x18\x04 \x01(\x02\x12\x0c\n\x04unit\x18\x05 \x01(\t"}\n\x0fSpectralProfile\x12\x12\n\ncoordinate\x18\x01 \x01(\t\x12$\n\nstats_type\x18\x02 \x01(\x0e2\x10.CARTA.StatsType\x12\x17\n\x0fraw_values_fp32\x18\x03 \x01(\x0c\x12\x17\n\x0fraw_values_fp64\x18\x04 \x01(\x0c"F\n\x0fStatisticsValue\x12$\n\nstats_type\x18\x01 \x01(\x0e2\x10.CARTA.StatsType\x12\r\n\x05value\x18\x02 \x01(\x01"w\n\tHistogram\x12\x10\n\x08num_bins\x18\x01 \x01(\x0f\x12\x11\n\tbin_width\x18\x02 \x01(\x01\x12\x18\n\x10first_bin_center\x18\x03 \x01(\x01\x12\x0c\n\x04bins\x18\x04 \x03(\x0f\x12\x0c\n\x04mean\x18\x05 \x01(\x01\x12\x0f\n\x07std_dev\x18\x06 \x01(\x01"\x9b\x01\n\x0fHistogramConfig\x12\x12\n\ncoordinate\x18\x01 \x01(\t\x12\x0f\n\x07channel\x18\x02 \x01(\x0f\x12\x16\n\x0efixed_num_bins\x18\x03 \x01(\x08\x12\x10\n\x08num_bins\x18\x04 \x01(\x0f\x12\x14\n\x0cfixed_bounds\x18\x05 \x01(\x08\x12#\n\x06bounds\x18\x06 \x01(\x0b2\x13.CARTA.DoubleBounds"l\n\nRegionInfo\x12&\n\x0bregion_type\x18\x01 \x01(\x0e2\x11.CARTA.RegionType\x12$\n\x0econtrol_points\x18\x02 \x03(\x0b2\x0c.CARTA.Point\x12\x10\n\x08rotation\x18\x03 \x01(\x02"\x83\x01\n\x0bRegionStyle\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\r\n\x05color\x18\x02 \x01(\t\x12\x12\n\nline_width\x18\x03 \x01(\x0f\x12\x11\n\tdash_list\x18\x04 \x03(\x0f\x120\n\x10annotation_style\x18\x05 \x01(\x0b2\x16.CARTA.AnnotationStyle"\xb7\x02\n\x0fAnnotationStyle\x120\n\x0bpoint_shape\x18\x01 \x01(\x0e2\x1b.CARTA.PointAnnotationShape\x12\x13\n\x0bpoint_width\x18\x02 \x01(\x0f\x12\x13\n\x0btext_label0\x18\x03 \x01(\t\x12\x13\n\x0btext_label1\x18\x04 \x01(\t\x12\x19\n\x11coordinate_system\x18\x05 \x01(\t\x12\x16\n\x0eis_north_arrow\x18\x06 \x01(\x08\x12\x15\n\ris_east_arrow\x18\x07 \x01(\x08\x124\n\rtext_position\x18\x08 \x01(\x0e2\x1d.CARTA.TextAnnotationPosition\x12\x12\n\nfont_style\x18\t \x01(\t\x12\x0c\n\x04font\x18\n \x01(\t\x12\x11\n\tfont_size\x18\x0b \x01(\x0f"\x9a\x01\n\x0fCatalogFileInfo\x12\x0c\n\x04name\x18\x01 \x01(\t\x12$\n\x04type\x18\x02 \x01(\x0e2\x16.CARTA.CatalogFileType\x12\x11\n\tfile_size\x18\x03 \x01(\x10\x12\x13\n\x0bdescription\x18\x04 \x01(\t\x12\x1d\n\x06coosys\x18\x05 \x03(\x0b2\r.CARTA.Coosys\x12\x0c\n\x04date\x18\x06 \x01(\x10"8\n\x06Coosys\x12\x0f\n\x07equinox\x18\x01 \x01(\t\x12\r\n\x05epoch\x18\x02 \x01(\t\x12\x0e\n\x06system\x18\x03 \x01(\t"}\n\rCatalogHeader\x12\x0c\n\x04name\x18\x01 \x01(\t\x12$\n\tdata_type\x18\x02 \x01(\x0e2\x11.CARTA.ColumnType\x12\x14\n\x0ccolumn_index\x18\x03 \x01(\x0f\x12\x13\n\x0bdescription\x18\x05 \x01(\t\x12\r\n\x05units\x18\x06 \x01(\t"\\\n\nColumnData\x12$\n\tdata_type\x18\x01 \x01(\x0e2\x11.CARTA.ColumnType\x12\x13\n\x0bstring_data\x18\x02 \x03(\t\x12\x13\n\x0bbinary_data\x18\x03 \x01(\x0c"\x97\x01\n\x0cFilterConfig\x12\x13\n\x0bcolumn_name\x18\x01 \x01(\t\x126\n\x13comparison_operator\x18\x02 \x01(\x0e2\x19.CARTA.ComparisonOperator\x12\r\n\x05value\x18\x03 \x01(\x01\x12\x17\n\x0fsecondary_value\x18\x04 \x01(\x01\x12\x12\n\nsub_string\x18\x05 \x01(\t"l\n\x12CatalogImageBounds\x12\x15\n\rx_column_name\x18\x01 \x01(\t\x12\x15\n\ry_column_name\x18\x02 \x01(\t\x12(\n\x0cimage_bounds\x18\x03 \x01(\x0b2\x12.CARTA.ImageBounds")\n\x10MatchedFrameList\x12\x15\n\rframe_numbers\x18\x01 \x03(\x02"[\n\x04Beam\x12\x0f\n\x07channel\x18\x01 \x01(\x0f\x12\x0e\n\x06stokes\x18\x02 \x01(\x0f\x12\x12\n\nmajor_axis\x18\x03 \x01(\x02\x12\x12\n\nminor_axis\x18\x04 \x01(\x02\x12\n\n\x02pa\x18\x05 \x01(\x02"{\n\x0cListProgress\x12+\n\x0efile_list_type\x18\x01 \x01(\x0e2\x13.CARTA.FileListType\x12\x12\n\npercentage\x18\x02 \x01(\x02\x12\x15\n\rchecked_count\x18\x03 \x01(\x0f\x12\x13\n\x0btotal_count\x18\x04 \x01(\x0f"\x86\x01\n\x08TileData\x12\r\n\x05layer\x18\x01 \x01(\x0f\x12\t\n\x01x\x18\x02 \x01(\x0f\x12\t\n\x01y\x18\x03 \x01(\x0f\x12\r\n\x05width\x18\x04 \x01(\x0f\x12\x0e\n\x06height\x18\x05 \x01(\x0f\x12\x12\n\nimage_data\x18\x06 \x01(\x0c\x12\x15\n\rnan_encodings\x18\x07 \x01(\x0c\x12\x0b\n\x03mip\x18\x08 \x01(\x0f"r\n\x11GaussianComponent\x12"\n\x06center\x18\x01 \x01(\x0b2\x12.CARTA.DoublePoint\x12\x0b\n\x03amp\x18\x02 \x01(\x01\x12 \n\x04fwhm\x18\x03 \x01(\x0b2\x12.CARTA.DoublePoint\x12\n\n\x02pa\x18\x04 \x01(\x01"\xd9\x01\n\x11PvPreviewSettings\x12\x12\n\npreview_id\x18\x01 \x01(\x0f\x12\x11\n\tregion_id\x18\x02 \x01(\x0f\x12\x10\n\x08rebin_xy\x18\x03 \x01(\x0f\x12\x0f\n\x07rebin_z\x18\x04 \x01(\x0f\x120\n\x10compression_type\x18\x05 \x01(\x0e2\x16.CARTA.CompressionType\x12!\n\x19image_compression_quality\x18\x06 \x01(\x02\x12%\n\x1danimation_compression_quality\x18\x07 \x01(\x02b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'defs_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_POINT']._serialized_start = 34
    _globals['_POINT']._serialized_end = 63
    _globals['_DOUBLEPOINT']._serialized_start = 65
    _globals['_DOUBLEPOINT']._serialized_end = 100
    _globals['_FILEINFO']._serialized_start = 102
    _globals['_FILEINFO']._serialized_end = 203
    _globals['_DIRECTORYINFO']._serialized_start = 205
    _globals['_DIRECTORYINFO']._serialized_end = 268
    _globals['_FILEINFOEXTENDED']._serialized_start = 271
    _globals['_FILEINFOEXTENDED']._serialized_end = 524
    _globals['_HEADERENTRY']._serialized_start = 526
    _globals['_HEADERENTRY']._serialized_end = 646
    _globals['_AXESNUMBERS']._serialized_start = 648
    _globals['_AXESNUMBERS']._serialized_end = 748
    _globals['_INTBOUNDS']._serialized_start = 750
    _globals['_INTBOUNDS']._serialized_end = 787
    _globals['_FLOATBOUNDS']._serialized_start = 789
    _globals['_FLOATBOUNDS']._serialized_end = 828
    _globals['_DOUBLEBOUNDS']._serialized_start = 830
    _globals['_DOUBLEBOUNDS']._serialized_end = 870
    _globals['_IMAGEBOUNDS']._serialized_start = 872
    _globals['_IMAGEBOUNDS']._serialized_end = 945
    _globals['_ANIMATIONFRAME']._serialized_start = 947
    _globals['_ANIMATIONFRAME']._serialized_end = 996
    _globals['_SPATIALPROFILE']._serialized_start = 999
    _globals['_SPATIALPROFILE']._serialized_end = 1144
    _globals['_LINEPROFILEAXIS']._serialized_start = 1146
    _globals['_LINEPROFILEAXIS']._serialized_end = 1265
    _globals['_SPECTRALPROFILE']._serialized_start = 1267
    _globals['_SPECTRALPROFILE']._serialized_end = 1392
    _globals['_STATISTICSVALUE']._serialized_start = 1394
    _globals['_STATISTICSVALUE']._serialized_end = 1464
    _globals['_HISTOGRAM']._serialized_start = 1466
    _globals['_HISTOGRAM']._serialized_end = 1585
    _globals['_HISTOGRAMCONFIG']._serialized_start = 1588
    _globals['_HISTOGRAMCONFIG']._serialized_end = 1743
    _globals['_REGIONINFO']._serialized_start = 1745
    _globals['_REGIONINFO']._serialized_end = 1853
    _globals['_REGIONSTYLE']._serialized_start = 1856
    _globals['_REGIONSTYLE']._serialized_end = 1987
    _globals['_ANNOTATIONSTYLE']._serialized_start = 1990
    _globals['_ANNOTATIONSTYLE']._serialized_end = 2301
    _globals['_CATALOGFILEINFO']._serialized_start = 2304
    _globals['_CATALOGFILEINFO']._serialized_end = 2458
    _globals['_COOSYS']._serialized_start = 2460
    _globals['_COOSYS']._serialized_end = 2516
    _globals['_CATALOGHEADER']._serialized_start = 2518
    _globals['_CATALOGHEADER']._serialized_end = 2643
    _globals['_COLUMNDATA']._serialized_start = 2645
    _globals['_COLUMNDATA']._serialized_end = 2737
    _globals['_FILTERCONFIG']._serialized_start = 2740
    _globals['_FILTERCONFIG']._serialized_end = 2891
    _globals['_CATALOGIMAGEBOUNDS']._serialized_start = 2893
    _globals['_CATALOGIMAGEBOUNDS']._serialized_end = 3001
    _globals['_MATCHEDFRAMELIST']._serialized_start = 3003
    _globals['_MATCHEDFRAMELIST']._serialized_end = 3044
    _globals['_BEAM']._serialized_start = 3046
    _globals['_BEAM']._serialized_end = 3137
    _globals['_LISTPROGRESS']._serialized_start = 3139
    _globals['_LISTPROGRESS']._serialized_end = 3262
    _globals['_TILEDATA']._serialized_start = 3265
    _globals['_TILEDATA']._serialized_end = 3399
    _globals['_GAUSSIANCOMPONENT']._serialized_start = 3401
    _globals['_GAUSSIANCOMPONENT']._serialized_end = 3515
    _globals['_PVPREVIEWSETTINGS']._serialized_start = 3518
    _globals['_PVPREVIEWSETTINGS']._serialized_end = 3735