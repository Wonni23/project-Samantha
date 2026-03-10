import 'dart:math';
import 'dart:convert';
import 'package:web/web.dart' as web;
import 'package:frontend/core/config/api_config.dart';

/// OAuth 2.0 Authorization Code Flow를 위한 헬퍼 클래스
/// Google, Kakao, Naver 등 여러 OAuth Provider를 지원합니다.
class OAuthHelper {
  // OAuth Provider별 엔드포인트 설정
  static const _endpoints = {
    'google': 'https://accounts.google.com/o/oauth2/v2/auth',
    'kakao': 'https://kauth.kakao.com/oauth/authorize',
    'naver': 'https://nid.naver.com/oauth2.0/authorize',
  };

  // Provider별 기본 스코프
  static const _defaultScopes = {
    'google': 'email profile openid',
    'kakao': '', // 카카오 콘솔 설정 값을 따름 (invalid_scope 방지)
    'naver': 'name email profile_image',
  };

  /// OAuth 인증 프로세스를 시작합니다.
  ///
  /// [provider]: 'google', 'kakao', 'naver' 중 하나
  /// [clientId]: OAuth 클라이언트 ID
  /// [redirectUri]: 콜백 URL (예: 'http://localhost:8080/auth/callback')
  /// [scopes]: (선택) 커스텀 스코프. null이면 기본값 사용
  static void startAuth({
    required String provider,
    required String clientId,
    required String redirectUri,
    String? scopes,
  }) {
    final endpoint = _endpoints[provider];
    if (endpoint == null) {
      throw ArgumentError('지원하지 않는 provider입니다: $provider');
    }

    // CSRF 방지를 위한 state 토큰 생성
    final state = _generateState();

    // state와 provider를 localStorage에 저장 (콜백에서 검증용 임시 등록)
    web.window.localStorage.setItem('oauth_state', state);
    web.window.localStorage.setItem('oauth_provider', provider);

    // OAuth 인증 URL 생성
    final authUrl = Uri.parse(endpoint).replace(
      queryParameters: {
        'client_id': clientId,
        'redirect_uri': redirectUri,
        'response_type': 'code',
        'state': state,
        'scope': scopes ?? _defaultScopes[provider] ?? '',
      },
    );

    // 외부 OAuth 페이지로 리디렉션 (전체 페이지 이동)
    web.window.location.href = authUrl.toString();
  }

  /// 콜백 URL에서 인증 코드와 state를 추출합니다.
  ///
  /// 반환값: {code: '...', state: '...', provider: '...'} 또는 null
  static Map<String, String>? extractCallbackData() {
    final uri = Uri.parse(web.window.location.href);
    final code = uri.queryParameters['code'];
    final state = uri.queryParameters['state'];

    if (code == null || state == null) {
      return null;
    }

    // localStorage에서 저장된 state와 provider 가져오기
    final storedState = web.window.localStorage.getItem('oauth_state');
    final storedProvider = web.window.localStorage.getItem('oauth_provider');

    // state 토큰 검증
    if (state != storedState) {
      throw StateError('OAuth state 토큰이 일치하지 않습니다. CSRF 공격 가능성이 있습니다.');
    }

    // localStorage 정리
    web.window.localStorage.removeItem('oauth_state');
    web.window.localStorage.removeItem('oauth_provider');

    return {
      'code': code,
      'state': state,
      'provider': storedProvider ?? 'unknown',
    };
  }

  /// URL에서 OAuth 관련 파라미터를 제거합니다.
  /// 콜백 처리 후 깔끔한 URL로 만들기 위함
  static void cleanUrl() {
    web.window.history.replaceState(null, '', '/');
  }

  /// 랜덤 state 토큰을 생성합니다 (CSRF 방지용)
  static String _generateState() {
    final random = Random.secure();
    final values = List<int>.generate(32, (i) => random.nextInt(256));
    return base64Url.encode(values).replaceAll('=', '');
  }

  /// Provider별 Client ID를 반환하는 헬퍼 메서드
  static String getClientId(String provider) {
    return ApiConfig.getClientId(provider);
  }

  /// Redirect URI를 반환하는 헬퍼 메서드
  /// 컨테이너 환경을 고려하여 동적으로 URI 생성
  static String getRedirectUri() {
    // 현재 웹 페이지의 호스트와 포트를 기반으로 URI 생성
    final currentHost = web.window.location.host;
    final protocol = web.window.location.protocol;
    
    // 현재 접속한 도메인/IP를 기반으로 콜백 URL 생성
    final redirectUri = '$protocol//$currentHost/auth/callback';
    
    return redirectUri;
  }
}
