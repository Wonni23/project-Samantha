import 'package:json_annotation/json_annotation.dart';

part 'terms_agree.g.dart';

// 약관 동의 요청 모델
@JsonSerializable()
class TermsAgreeRequest {
  @JsonKey(name: 'terms_of_service')
  final bool termsOfService; // 이용약관 (필수)
  @JsonKey(name: 'privacy_policy')
  final bool privacyPolicy; // 개인정보 처리방침 (필수)
  @JsonKey(name: 'voice_collection')
  final bool voiceCollection; // 음성 수집 동의 (필수)
  @JsonKey(name: 'marketing_consent')
  final bool marketingConsent; // 마케팅 수신 동의 (선택)

  TermsAgreeRequest({
    required this.termsOfService,
    required this.privacyPolicy,
    required this.voiceCollection,
    this.marketingConsent = false, // 기본값 false
  });

  factory TermsAgreeRequest.fromJson(Map<String, dynamic> json) =>
      _$TermsAgreeRequestFromJson(json);

  Map<String, dynamic> toJson() => _$TermsAgreeRequestToJson(this);
}
