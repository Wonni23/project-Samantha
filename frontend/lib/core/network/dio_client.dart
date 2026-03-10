import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/config/api_config.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/features/auth/data/models/login.dart';
import 'package:frontend/features/auth/providers/auth_provider.dart';

/// Dio 인스턴스를 제공하는 Provider
///
/// 전역적으로 사용되는 Dio 클라이언트를 관리합니다.
/// Interceptor 추가, baseUrl 설정 등을 중앙에서 관리할 수 있습니다.
final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ),
  );

  // QueuedInterceptorsWrapper를 사용하여 자동 요청 대기 처리
  dio.interceptors.add(_DioInterceptor(ref, dio));

  return dio;
});

/// Dio Interceptor (QueuedInterceptorsWrapper 사용)
///
/// 401 에러 발생 시 요청을 큐에 쌓고, 토큰 갱신을 시도합니다.
/// 갱신이 성공하면 쌓였던 요청들을 순차적으로 재처리합니다.
class _DioInterceptor extends QueuedInterceptorsWrapper {
  final Ref _ref;
  final Dio _dio;

  _DioInterceptor(this._ref, this._dio);

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    logger.i('🚀 [REQUEST] ${options.method} ${options.path}');
    final token = await _ref.read(authProvider.notifier).getAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    super.onRequest(options, handler);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    logger.i(
      '✅ [RESPONSE] ${response.statusCode} ${response.requestOptions.path}',
    );
    super.onResponse(response, handler);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    logger.e('❌ [ERROR] ${err.response?.statusCode} ${err.requestOptions.path}');

    // 401 에러이고, 토큰 갱신 요청이나 인증 요청 자체가 실패한 경우가 아닐 때만 자동 갱신 시도
    final path = err.requestOptions.path;
    if (err.response?.statusCode == 401 &&
        !path.contains('/auth/refresh') &&
        !path.contains('/auth/login') &&
        !path.contains('/auth/register')) {
      logger.w('💡 401 Unauthorized. Attempting to refresh token...');
      final authNotifier = _ref.read(authProvider.notifier);
      final refreshToken = await authNotifier.getRefreshToken();

      if (refreshToken == null) {
        logger.e('🚫 No refresh token found. Logging out.');
        await authNotifier.logout();
        return super.onError(err, handler);
      }

      try {
        // 토큰 갱신을 위한 새로운 Dio 인스턴스 (인터셉터를 타지 않도록)
        final refreshDio = Dio(BaseOptions(baseUrl: ApiConfig.baseUrl));
        final response = await refreshDio.post(
          '/api/v1/auth/refresh',
          data: {'refresh_token': refreshToken},
        );

        // 새로운 토큰 저장
        final tokenResponse = LoginResponse.fromJson(response.data);
        await authNotifier.saveTokens(
          tokenResponse.accessToken,
          tokenResponse.refreshToken,
        );
        logger.i('✅ Token refreshed successfully.');

        // 원래 실패했던 요청에 새로운 토큰을 적용하여 재시도
        final originalRequest = err.requestOptions;
        originalRequest.headers['Authorization'] =
            'Bearer ${tokenResponse.accessToken}';

        logger.i('🚀 Retrying original request: ${originalRequest.path}');

        // 재요청 성공 시, 그 결과를 handler.resolve로 다음으로 넘김
        final retryResponse = await _dio.fetch(originalRequest);
        return handler.resolve(retryResponse);
      } on DioException catch (e) {
        // 리프레시 토큰 갱신 실패 (리프레시 토큰 만료 등)
        logger.e('🚫 Refresh token failed: ${e.type}. Logging out.');
        await authNotifier.logout();
        return super.onError(err, handler);
      }
    }

    // 401 에러가 아니거나, 예외 처리된 경로인 경우
    return super.onError(err, handler);
  }
}
