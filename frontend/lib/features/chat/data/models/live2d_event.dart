import 'package:json_annotation/json_annotation.dart';
import 'package:equatable/equatable.dart';

part 'live2d_event.g.dart';

@JsonSerializable()
class Live2DEvent extends Equatable {
  @JsonKey(defaultValue: 'serene')
  final String expression;

  const Live2DEvent({
    required this.expression,
  });

  factory Live2DEvent.fromJson(Map<String, dynamic> json) =>
      _$Live2DEventFromJson(json);

  Map<String, dynamic> toJson() => _$Live2DEventToJson(this);

  /// 감정 이름을 모션 번호로 변환
  /// sparkle: 21, pout: 4, adore: 18, warm: 23, serene: 2(기본)
  int get motionIndex {
    switch (expression) {
      case 'sparkle':
        return 21;
      case 'pout':
        return 4;
      case 'adore':
        return 18;
      case 'warm':
        return 23;
      case 'serene':
      default:
        return 2;
    }
  }

  @override
  List<Object?> get props => [expression];
}
