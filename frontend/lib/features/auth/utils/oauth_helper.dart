import 'package:frontend/core/config/api_config.dart';

// 플랫폼별 조건부 임포트 - 빌드 시점에 따라 하나의 파일만 선택됩니다.
import 'oauth_web_impl.dart'
    if (dart.library.io) 'oauth_mobile_impl.dart';

/// OAuth 2.0 Authorization Code Flow를 위한 헬퍼 클래스
class OAuthHelper {
  /// OAuth 인증 프로세스를 시작합니다.
  static void startAuth({
    required String provider,
    required String clientId,
    required String redirectUri,
    String? scopes,
  }) {
    // 이제 플랫폼에 상관없이 OAuthServiceImpl이라는 이름을 사용합니다.
    OAuthServiceImpl.startAuth(
      provider: provider,
      clientId: clientId,
      redirectUri: redirectUri,
      scopes: scopes,
    );
  }

  /// 콜백 URL에서 인증 코드와 state를 추출합니다.
  static Map<String, String>? extractCallbackData() {
    return OAuthServiceImpl.extractCallbackData();
  }

  /// URL에서 OAuth 관련 파라미터를 제거합니다.
  static void cleanUrl() {
    OAuthServiceImpl.cleanUrl();
  }

  /// Provider별 Client ID를 반환하는 헬퍼 메서드
  static String getClientId(String provider) {
    return ApiConfig.getClientId(provider);
  }

  /// Redirect URI를 반환하는 헬퍼 메서드
  static String getRedirectUri() {
    return OAuthServiceImpl.getRedirectUri();
  }
}
