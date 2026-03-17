class OAuthServiceImpl {
  static void startAuth({
    required String provider,
    required String clientId,
    required String redirectUri,
    String? scopes,
  }) {
    // 모바일에서는 추후 url_launcher 또는 flutter_web_auth_2 패키지를 활용하여 구현 예정
    throw UnsupportedError('모바일 OAuth는 아직 구현되지 않았습니다.');
  }

  static Map<String, String>? extractCallbackData() {
    return null;
  }

  static void cleanUrl() {}

  static String getRedirectUri() {
    // 모바일용 딥링크 URI 반환
    return 'com.sia.samantha://auth/callback';
  }
}
