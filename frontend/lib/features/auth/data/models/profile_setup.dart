import 'package:json_annotation/json_annotation.dart';

part 'profile_setup.g.dart';

// 1. Enum 정의 (백엔드 철자랑 맞춰서)
enum GenderType {
  male,
  female;

  // Dart가 자동 제공하는 name getter를 사용 (name = "male", "female")
  String toJson() => name;
}

enum PlatformType {
  android,
  ios,
  web;

  // 백엔드가 대문자를 원할 경우 (ANDROID, IOS, WEB) -> 소문자로 수정
  String toJson() => name;
}

// 2. 프로필 설정 요청 모델
@JsonSerializable()
class ProfileSetupRequest {
  @JsonKey(name: 'real_name')
  final String realName; // 사용자 실명
  final GenderType gender; // 성별
  @JsonKey(name: 'birth_year')
  final int birthYear; // 출생년도
  @JsonKey(name: 'user_title')
  final String userTitle; // AI가 부를 호칭
  final PlatformType platform; // 플랫폼 타입

  ProfileSetupRequest({
    required this.realName,
    required this.gender,
    required this.birthYear,
    this.userTitle = '어르신', // 기본 호칭
    this.platform = PlatformType.web, // 기본 플랫폼 웹으로 변경
  });

  factory ProfileSetupRequest.fromJson(Map<String, dynamic> json) =>
      _$ProfileSetupRequestFromJson(json);

  Map<String, dynamic> toJson() => _$ProfileSetupRequestToJson(this);
}
