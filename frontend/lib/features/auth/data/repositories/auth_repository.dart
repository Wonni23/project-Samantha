import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/network/dio_client.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/features/auth/data/models/login.dart';
import 'package:frontend/features/auth/data/models/profile_setup.dart';
import 'package:frontend/features/auth/data/models/terms_agree.dart';
import 'package:frontend/features/auth/data/models/local_auth.dart';

import 'package:frontend/features/auth/data/models/user_info.dart';

// Repository를 제공하는 Provider
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  // core/network에서 제공하는 Dio 인스턴스 사용
  final dio = ref.watch(dioProvider);
  return AuthRepository(dio: dio);
});

class AuthRepository {
  final Dio _dio;

  AuthRepository({required Dio dio}) : _dio = dio;

  Future<LoginResponse> login(LoginRequest loginRequest) async {
    try {
      final response = await _dio.post(
        '/api/v1/auth/login',
        data: loginRequest.toJson(),
      );
      return LoginResponse.fromJson(response.data);
    } on DioException catch (e) {
      // 보안을 위해 원시 DioException 객체 전체를 로깅하지 않음
      logger.e('로그인 실패: ${e.type}');
      rethrow;
    } catch (e) {
      logger.e('알 수 없는 에러: ${e.runtimeType}');
      rethrow;
    }
  }

  /// 휴대폰 번호 로그인을 수행합니다.
  Future<LoginResponse> loginLocal(LocalLoginRequest request) async {
    try {
      final response = await _dio.post(
        '/api/v1/auth/login/local',
        data: request.toJson(),
      );
      return LoginResponse.fromJson(response.data);
    } on DioException catch (e) {
      logger.e('휴대폰 번호 로그인 실패: ${e.type}');
      rethrow;
    }
  }

  /// 휴대폰 번호 회원가입을 수행합니다.
  Future<LoginResponse> registerLocal(LocalRegisterRequest request) async {
    try {
      final response = await _dio.post(
        '/api/v1/auth/register/local',
        data: request.toJson(),
      );
      return LoginResponse.fromJson(response.data);
    } on DioException catch (e) {
      logger.e('휴대폰 번호 회원가입 실패: ${e.type}');
      rethrow;
    }
  }

  /// 현재 로그인한 사용자 정보를 가져옵니다 (생존 확인 및 마이페이지용).
  Future<UserInfo> fetchMe() async {
    try {
      final response = await _dio.get('/api/v1/users/me');
      return UserInfo.fromJson(response.data);
    } on DioException catch (e) {
      logger.e('사용자 정보 조회 실패: ${e.type}');
      rethrow;
    }
  }

  /// 사용자 프로필을 설정합니다.
  Future<void> setupProfile(ProfileSetupRequest request) async {
    try {
      await _dio.post('/api/v1/auth/profile', data: request.toJson());
    } on DioException catch (e) {
      logger.e('프로필 설정 실패: ${e.type}');
      rethrow;
    } catch (e) {
      logger.e('알 수 없는 에러: ${e.runtimeType}');
      rethrow;
    }
  }

  /// 약관 동의 정보를 전송합니다.
  Future<void> agreeToTerms(TermsAgreeRequest request) async {
    try {
      await _dio.post('/api/v1/auth/terms', data: request.toJson());
    } on DioException catch (e) {
      logger.e('약관 동의 실패: ${e.type}');
      rethrow;
    } catch (e) {
      logger.e('알 수 없는 에러: ${e.runtimeType}');
      rethrow;
    }
  }
}
