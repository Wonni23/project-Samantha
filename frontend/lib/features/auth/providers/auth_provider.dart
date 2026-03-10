import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/features/auth/data/models/local_auth.dart';
import 'package:frontend/features/auth/data/models/login.dart';
import 'package:frontend/features/auth/data/repositories/auth_repository.dart';
import 'package:frontend/features/auth/utils/oauth_helper.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'auth_provider.g.dart';

// 인증 상태를 나타내는 열거형
enum AuthStatus { loggedOut, onboardingRequired, loggedIn }

@Riverpod(keepAlive: true)
class Auth extends _$Auth {
  // FlutterSecureStorage 인스턴스 생성
  final _storage = const FlutterSecureStorage();

  // Secure Storage 키 정의
  static const _accessTokenKey = 'accessToken';
  static const _refreshTokenKey = 'refreshToken';
  static const _onboardingStatusKey = 'onboardingStatus';

  @override
  Future<AuthStatus> build() async {
    // 1. 로컬 저장소에서 Access Token 존재 여부 확인
    final hasToken = await _storage.read(key: _accessTokenKey) != null;
    logger.i('🔐 인증 상태 초기화: hasToken=$hasToken');

    if (!hasToken) {
      return AuthStatus.loggedOut;
    }

    try {
      // 2. [고도화] 서버에 실제 유저가 존재하는지 확인 (유령 유저 방지)
      final authRepository = ref.read(authRepositoryProvider);
      await authRepository.fetchMe();

      // 3. 서버 검증 성공 시, 온보딩 여부에 따라 상태 결정
      final onboardingRequired =
          await _storage.read(key: _onboardingStatusKey) == 'true';
      if (onboardingRequired) {
        return AuthStatus.onboardingRequired;
      }

      return AuthStatus.loggedIn;
    } on DioException catch (e) {
      // 4. 인증 관련 에러(401, 403, 404)인 경우에만 세션 정리 후 로그아웃
      final statusCode = e.response?.statusCode;
      if (statusCode == 401 || statusCode == 403 || statusCode == 404) {
        logger.w('인증 실패(status: $statusCode). 로그아웃 처리합니다.');
        await _clearSession();
        return AuthStatus.loggedOut;
      }
      
      // 네트워크 에러나 서버 5xx 에러 등은 세션을 유지하고 에러를 던져 AsyncValue.error 상태로 둠
      logger.e('서버 통신 중 에러 발생 (status: $statusCode). 세션을 유지합니다.');
      rethrow;
    } catch (e) {
      logger.e('알 수 없는 인증 에러 발생: ${e.runtimeType}. 세션을 유지합니다.');
      rethrow;
    }
  }

  /// 이메일 로그인을 수행합니다.
  Future<void> signInWithEmail(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final repository = ref.read(authRepositoryProvider);
      final response = await repository.loginLocal(
        LocalLoginRequest(email: email, password: password),
      );
      
      await _handleLoginResponse(response);
    } on DioException catch (e, stackTrace) {
      final message = _extractErrorMessage(e, '로그인에 실패했습니다.');
      state = AsyncValue.error(message, stackTrace);
    } catch (error, stackTrace) {
      logger.e('이메일 로그인 중 오류 발생: ${error.runtimeType}');
      state = AsyncValue.error('일시적인 오류가 발생했습니다.', stackTrace);
    }
  }

  /// 이메일 회원가입을 수행합니다.
  Future<void> signUpWithEmail(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final repository = ref.read(authRepositoryProvider);
      final response = await repository.registerLocal(
        LocalRegisterRequest(email: email, password: password),
      );
      
      await _handleLoginResponse(response);
    } on DioException catch (e, stackTrace) {
      final message = _extractErrorMessage(e, '회원가입에 실패했습니다.');
      state = AsyncValue.error(message, stackTrace);
    } catch (error, stackTrace) {
      logger.e('이메일 회원가입 중 오류 발생: ${error.runtimeType}');
      state = AsyncValue.error('일시적인 오류가 발생했습니다.', stackTrace);
    }
  }

  /// 에러 응답 바디에서 상세 메시지 추출 (타입 안전성 강화)
  String _extractErrorMessage(DioException e, String defaultMessage) {
    if (e.response?.statusCode == 401 && e.requestOptions.path.contains('/login')) {
      return '이메일 또는 비밀번호가 일치하지 않습니다.';
    }

    final dynamic data = e.response?.data;
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String) return detail;
      if (detail is List && detail.isNotEmpty) {
        final first = detail.first;
        if (first is Map && first.containsKey('msg')) {
          return first['msg'].toString();
        }
        return first.toString();
      }
      final message = data['message'];
      if (message is String) return message;
    }
    
    if (data is String && data.isNotEmpty) return data;

    return defaultMessage;
  }

  /// 공통 로그인 응답 처리 로직
  Future<void> _handleLoginResponse(LoginResponse response) async {
    // 토큰 저장
    await saveTokens(response.accessToken, response.refreshToken);

    // 온보딩 필요 여부에 따라 상태 분기
    if (!response.isOnboardingComplete) {
      await _setOnboardingRequired(true);
      state = const AsyncValue.data(AuthStatus.onboardingRequired);
    } else {
      await _setOnboardingRequired(false);
      state = const AsyncValue.data(AuthStatus.loggedIn);
    }
  }

  void signInWithGoogle() {
    try {
      OAuthHelper.startAuth(
        provider: 'google',
        clientId: OAuthHelper.getClientId('google'),
        redirectUri: OAuthHelper.getRedirectUri(),
      );
    } catch (error) {
      logger.e('Google OAuth 시작 중 오류 발생: ${error.runtimeType}');
      state = AsyncValue.error(error, StackTrace.current);
    }
  }

  void signInWithKakao() {
    try {
      OAuthHelper.startAuth(
        provider: 'kakao',
        clientId: OAuthHelper.getClientId('kakao'),
        redirectUri: OAuthHelper.getRedirectUri(),
      );
    } catch (error) {
      logger.e('Kakao OAuth 시작 중 오류 발생: ${error.runtimeType}');
      state = AsyncValue.error(error, StackTrace.current);
    }
  }

  void signInWithNaver() {
    try {
      OAuthHelper.startAuth(
        provider: 'naver',
        clientId: OAuthHelper.getClientId('naver'),
        redirectUri: OAuthHelper.getRedirectUri(),
      );
    } catch (error) {
      logger.e('Naver OAuth 시작 중 오류 발생: ${error.runtimeType}');
      state = AsyncValue.error(error, StackTrace.current);
    }
  }

  /// OAuth 콜백을 처리하고 상태를 업데이트합니다.
  Future<void> handleOAuthCallback() async {
    logger.i('🔄 OAuth 콜백 처리 시작');
    state = const AsyncValue.loading();

    try {
      final callbackData = OAuthHelper.extractCallbackData();
      logger.i('📥 콜백 데이터: $callbackData');
      if (callbackData == null) throw Exception('OAuth 콜백 데이터 없음');

      final code = callbackData['code']!;
      final provider = callbackData['provider']!;
      final stateParam = callbackData['state'];

      OAuthHelper.cleanUrl();

      final authRepository = ref.read(authRepositoryProvider);
      final request = LoginRequest(
        provider: provider,
        code: code,
        redirectUri: OAuthHelper.getRedirectUri(),
        state: stateParam,
      );

      logger.i('🚀 백엔드로 로그인 요청 전송: provider=$provider');
      final response = await authRepository.login(request);
      logger.i('✅ 백엔드 로그인 응답 성공');
      
      await _handleLoginResponse(response);
    } catch (error, stackTrace) {
      logger.e('OAuth 콜백 처리 중 오류 발생: ${error.runtimeType}');
      await _clearSession();
      state = AsyncValue.error(error, stackTrace);
    }
  }

  /// 온보딩 프로세스를 완료 처리합니다.
  Future<void> completeOnboarding() async {
    await _setOnboardingRequired(false);
    state = const AsyncValue.data(AuthStatus.loggedIn);
    logger.i('온보딩 완료. 로그인 상태로 전환.');
  }

  /// 로그아웃을 수행합니다.
  Future<void> logout() async {
    state = const AsyncValue.loading();
    try {
      await _clearSession();
      state = const AsyncValue.data(AuthStatus.loggedOut);
      logger.i('로그아웃 완료');
    } catch (error) {
      logger.e('로그아웃 중 오류 발생: ${error.runtimeType}');
      state = AsyncValue.error(error, StackTrace.current);
    }
  }

  // --- Helper Methods ---

  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  Future<void> _setOnboardingRequired(bool required) async {
    await _storage.write(key: _onboardingStatusKey, value: required.toString());
  }

  Future<void> _clearSession() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
    await _storage.delete(key: _onboardingStatusKey);
  }

  Future<String?> getAccessToken() async {
    return _storage.read(key: _accessTokenKey);
  }

  Future<String?> getRefreshToken() async {
    return _storage.read(key: _refreshTokenKey);
  }
}
