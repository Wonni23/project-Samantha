// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'terms_agree.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

TermsAgreeRequest _$TermsAgreeRequestFromJson(Map<String, dynamic> json) =>
    TermsAgreeRequest(
      termsOfService: json['terms_of_service'] as bool,
      privacyPolicy: json['privacy_policy'] as bool,
      voiceCollection: json['voice_collection'] as bool,
      marketingConsent: json['marketing_consent'] as bool? ?? false,
    );

Map<String, dynamic> _$TermsAgreeRequestToJson(TermsAgreeRequest instance) =>
    <String, dynamic>{
      'terms_of_service': instance.termsOfService,
      'privacy_policy': instance.privacyPolicy,
      'voice_collection': instance.voiceCollection,
      'marketing_consent': instance.marketingConsent,
    };
