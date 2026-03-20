// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'local_auth.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LocalRegisterRequest _$LocalRegisterRequestFromJson(
  Map<String, dynamic> json,
) => LocalRegisterRequest(
  phoneNumber: json['phone_number'] as String,
  password: json['password'] as String,
);

Map<String, dynamic> _$LocalRegisterRequestToJson(
  LocalRegisterRequest instance,
) => <String, dynamic>{
  'phone_number': instance.phoneNumber,
  'password': instance.password,
};

LocalLoginRequest _$LocalLoginRequestFromJson(Map<String, dynamic> json) =>
    LocalLoginRequest(
      phoneNumber: json['phone_number'] as String,
      password: json['password'] as String,
    );

Map<String, dynamic> _$LocalLoginRequestToJson(LocalLoginRequest instance) =>
    <String, dynamic>{
      'phone_number': instance.phoneNumber,
      'password': instance.password,
    };
