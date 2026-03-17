import 'dart:math';
import 'dart:convert';
import 'package:web/web.dart' as web;

class OAuthServiceImpl {
  static const _endpoints = {
    'google': 'https://accounts.google.com/o/oauth2/v2/auth',
    'kakao': 'https://kauth.kakao.com/oauth/authorize',
    'naver': 'https://nid.naver.com/oauth2.0/authorize',
  };

  static const _defaultScopes = {
    'google': 'email profile openid',
    'kakao': '',
    'naver': 'name email profile_image',
  };

  static void startAuth({
    required String provider,
    required String clientId,
    required String redirectUri,
    String? scopes,
  }) {
    final endpoint = _endpoints[provider];
    if (endpoint == null) throw ArgumentError('지원하지 않는 provider입니다: $provider');

    final state = _generateState();
    web.window.localStorage.setItem('oauth_state', state);
    web.window.localStorage.setItem('oauth_provider', provider);

    final authUrl = Uri.parse(endpoint).replace(
      queryParameters: {
        'client_id': clientId,
        'redirect_uri': redirectUri,
        'response_type': 'code',
        'state': state,
        'scope': scopes ?? _defaultScopes[provider] ?? '',
      },
    );

    web.window.location.href = authUrl.toString();
  }

  static Map<String, String>? extractCallbackData() {
    final uri = Uri.parse(web.window.location.href);
    final code = uri.queryParameters['code'];
    final state = uri.queryParameters['state'];

    if (code == null || state == null) return null;

    final storedState = web.window.localStorage.getItem('oauth_state');
    final storedProvider = web.window.localStorage.getItem('oauth_provider');

    if (state != storedState) throw StateError('OAuth state 토큰 불일치');

    web.window.localStorage.removeItem('oauth_state');
    web.window.localStorage.removeItem('oauth_provider');

    return {
      'code': code,
      'state': state,
      'provider': storedProvider ?? 'unknown',
    };
  }

  static void cleanUrl() {
    web.window.history.replaceState(null, '', '/');
  }

  static String _generateState() {
    final random = Random.secure();
    final values = List<int>.generate(32, (i) => random.nextInt(256));
    return base64Url.encode(values).replaceAll('=', '');
  }

  static String getRedirectUri() {
    final currentHost = web.window.location.host;
    final protocol = web.window.location.protocol;
    return '$protocol//$currentHost/auth/callback';
  }
}
