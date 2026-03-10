// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'profile_setup.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ProfileSetupRequest _$ProfileSetupRequestFromJson(Map<String, dynamic> json) =>
    ProfileSetupRequest(
      realName: json['real_name'] as String,
      gender: $enumDecode(_$GenderTypeEnumMap, json['gender']),
      birthYear: (json['birth_year'] as num).toInt(),
      userTitle: json['user_title'] as String? ?? '어르신',
      platform:
          $enumDecodeNullable(_$PlatformTypeEnumMap, json['platform']) ??
          PlatformType.web,
    );

Map<String, dynamic> _$ProfileSetupRequestToJson(
  ProfileSetupRequest instance,
) => <String, dynamic>{
  'real_name': instance.realName,
  'gender': instance.gender,
  'birth_year': instance.birthYear,
  'user_title': instance.userTitle,
  'platform': instance.platform,
};

const _$GenderTypeEnumMap = {
  GenderType.male: 'male',
  GenderType.female: 'female',
};

const _$PlatformTypeEnumMap = {
  PlatformType.android: 'android',
  PlatformType.ios: 'ios',
  PlatformType.web: 'web',
};
