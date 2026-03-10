import 'package:json_annotation/json_annotation.dart';

part 'user_info.g.dart';

@JsonSerializable()
class UserInfo {
  final int id;
  @JsonKey(name: 'phone_number')
  final String? phoneNumber;
  @JsonKey(name: 'real_name')
  final String? realName;
  final String? gender;
  @JsonKey(name: 'birth_year')
  final int? birthYear;
  @JsonKey(name: 'address_district')
  final String? addressDistrict;
  final String platform;
  final String role;
  final String tier;
  @JsonKey(name: 'daily_usage')
  final int dailyUsage;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'last_active_at')
  final DateTime lastActiveAt;
  @JsonKey(name: 'is_onboarding_complete')
  final bool isOnboardingComplete;

  UserInfo({
    required this.id,
    this.phoneNumber,
    this.realName,
    this.gender,
    this.birthYear,
    this.addressDistrict,
    required this.platform,
    required this.role,
    required this.tier,
    required this.dailyUsage,
    required this.createdAt,
    required this.lastActiveAt,
    required this.isOnboardingComplete,
  });

  factory UserInfo.fromJson(Map<String, dynamic> json) => _$UserInfoFromJson(json);
  Map<String, dynamic> toJson() => _$UserInfoToJson(this);
}