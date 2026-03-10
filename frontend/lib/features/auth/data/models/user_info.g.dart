// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_info.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserInfo _$UserInfoFromJson(Map<String, dynamic> json) => UserInfo(
  id: (json['id'] as num).toInt(),
  phoneNumber: json['phone_number'] as String?,
  realName: json['real_name'] as String?,
  gender: json['gender'] as String?,
  birthYear: (json['birth_year'] as num?)?.toInt(),
  addressDistrict: json['address_district'] as String?,
  platform: json['platform'] as String,
  role: json['role'] as String,
  tier: json['tier'] as String,
  dailyUsage: (json['daily_usage'] as num).toInt(),
  createdAt: DateTime.parse(json['created_at'] as String),
  lastActiveAt: DateTime.parse(json['last_active_at'] as String),
  isOnboardingComplete: json['is_onboarding_complete'] as bool,
);

Map<String, dynamic> _$UserInfoToJson(UserInfo instance) => <String, dynamic>{
  'id': instance.id,
  'phone_number': instance.phoneNumber,
  'real_name': instance.realName,
  'gender': instance.gender,
  'birth_year': instance.birthYear,
  'address_district': instance.addressDistrict,
  'platform': instance.platform,
  'role': instance.role,
  'tier': instance.tier,
  'daily_usage': instance.dailyUsage,
  'created_at': instance.createdAt.toIso8601String(),
  'last_active_at': instance.lastActiveAt.toIso8601String(),
  'is_onboarding_complete': instance.isOnboardingComplete,
};
