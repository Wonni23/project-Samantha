// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'legacy.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Legacy _$LegacyFromJson(Map<String, dynamic> json) => Legacy(
  id: (json['id'] as num).toInt(),
  summary: json['summary'] as String,
  category: json['category'] as String,
  importance: (json['importance'] as num).toInt(),
);

Map<String, dynamic> _$LegacyToJson(Legacy instance) => <String, dynamic>{
  'id': instance.id,
  'summary': instance.summary,
  'category': instance.category,
  'importance': instance.importance,
};
