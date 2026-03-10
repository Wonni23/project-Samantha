import 'package:json_annotation/json_annotation.dart';

part 'legacy.g.dart';

@JsonSerializable()
class Legacy {
  final int id;
  final String summary;
  final String category;
  final int importance;

  Legacy({
    required this.id,
    required this.summary,
    required this.category,
    required this.importance,
  });

  factory Legacy.fromJson(Map<String, dynamic> json) => _$LegacyFromJson(json);
  Map<String, dynamic> toJson() => _$LegacyToJson(this);
}
