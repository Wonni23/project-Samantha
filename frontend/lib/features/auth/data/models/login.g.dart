// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'login.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LoginRequest _$LoginRequestFromJson(Map<String, dynamic> json) => LoginRequest(
  provider: json['provider'] as String,
  code: json['code'] as String,
  redirectUri: json['redirect_uri'] as String,
  state: json['state'] as String?,
);

Map<String, dynamic> _$LoginRequestToJson(LoginRequest instance) =>
    <String, dynamic>{
      'provider': instance.provider,
      'code': instance.code,
      'redirect_uri': instance.redirectUri,
      'state': instance.state,
    };

LoginResponse _$LoginResponseFromJson(Map<String, dynamic> json) =>
    LoginResponse(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      tokenType: json['token_type'] as String,
      userId: (json['user_id'] as num).toInt(),
      isOnboardingComplete: json['is_onboarding_complete'] as bool,
    );

Map<String, dynamic> _$LoginResponseToJson(LoginResponse instance) =>
    <String, dynamic>{
      'access_token': instance.accessToken,
      'refresh_token': instance.refreshToken,
      'token_type': instance.tokenType,
      'user_id': instance.userId,
      'is_onboarding_complete': instance.isOnboardingComplete,
    };
