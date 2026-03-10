// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'local_auth.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LocalRegisterRequest _$LocalRegisterRequestFromJson(
  Map<String, dynamic> json,
) => LocalRegisterRequest(
  email: json['email'] as String,
  password: json['password'] as String,
);

Map<String, dynamic> _$LocalRegisterRequestToJson(
  LocalRegisterRequest instance,
) => <String, dynamic>{'email': instance.email, 'password': instance.password};

LocalLoginRequest _$LocalLoginRequestFromJson(Map<String, dynamic> json) =>
    LocalLoginRequest(
      email: json['email'] as String,
      password: json['password'] as String,
    );

Map<String, dynamic> _$LocalLoginRequestToJson(LocalLoginRequest instance) =>
    <String, dynamic>{'email': instance.email, 'password': instance.password};
