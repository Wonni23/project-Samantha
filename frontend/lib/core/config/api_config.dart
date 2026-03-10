import 'package:flutter_dotenv/flutter_dotenv.dart';

/// API 및 OAuth 설정을 관리하는 클래스
///
/// .env 파일에서 환경 변수를 로드하여 사용합니다.
class ApiConfig {
  /// .env 파일을 로드합니다. (앱 시작 시 main()에서 호출 필요)
  static Future<void> load() async {
    await dotenv.load(fileName: '.env');
  }

  /// API Base URL
  static String get baseUrl {
    final envUrl = dotenv.env['API_BASE_URL'] ?? '';
    // 컨테이너 환경에서는 빈 문자열로 설정하여 상대 경로 사용 (Nginx 프록시 활용)
    return envUrl.isEmpty ? '' : envUrl;
  }

  /// OAuth Redirect URI
  static String get oauthRedirectUri {
    return dotenv.env['OAUTH_REDIRECT_URI'] ?? 'http://localhost:8080/auth/callback';
  }

  /// Google OAuth Client ID
  static String get googleClientId {
    return dotenv.env['GOOGLE_CLIENT_ID'] ?? '';
  }

  /// Kakao OAuth Client ID
  static String get kakaoClientId {
    return dotenv.env['KAKAO_CLIENT_ID'] ?? '';
  }

  /// Naver OAuth Client ID
  static String get naverClientId {
    return dotenv.env['NAVER_CLIENT_ID'] ?? '';
  }

  /// Provider에 따른 Client ID 반환
  static String getClientId(String provider) {
    switch (provider.toLowerCase()) {
      case 'google':
        return googleClientId;
      case 'kakao':
        return kakaoClientId;
      case 'naver':
        return naverClientId;
      default:
        throw ArgumentError('지원하지 않는 OAuth Provider입니다: $provider');
    }
  }
}
