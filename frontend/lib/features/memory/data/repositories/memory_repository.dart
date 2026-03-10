import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/network/dio_client.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/features/memory/data/models/legacy.dart';
import 'package:frontend/features/memory/data/models/user_context.dart';

final memoryRepositoryProvider = Provider<MemoryRepository>((ref) {
  final dio = ref.watch(dioProvider);
  return MemoryRepository(dio: dio);
});

class MemoryRepository {
  final Dio _dio;

  MemoryRepository({required Dio dio}) : _dio = dio;

  /// 모든 기억(Legacy) 목록을 가져옵니다.
  Future<List<Legacy>> fetchLegacies() async {
    try {
      final response = await _dio.get('/api/v1/memory/legacies');
      final List<dynamic> data = response.data;
      return data.map((json) => Legacy.fromJson(json)).toList();
    } on DioException catch (e) {
      logger.e('기억 목록 조회 실패: ${e.type}');
      rethrow;
    }
  }

  /// 특정 기억(Legacy)을 삭제합니다.
  Future<void> deleteLegacy(int legacyId) async {
    try {
      await _dio.delete('/api/v1/memory/legacy/$legacyId');
    } on DioException catch (e) {
      logger.e('기억 삭제 실패: legacyId=$legacyId, type=${e.type}');
      rethrow;
    }
  }

  /// 사용자의 컨텍스트(페르소나 상태 및 프로필)를 가져옵니다.
  Future<UserContext> fetchUserContext() async {
    try {
      final response = await _dio.get('/api/v1/users/context');
      return UserContext.fromJson(response.data);
    } on DioException catch (e) {
      logger.e('사용자 컨텍스트 조회 실패: ${e.type}');
      rethrow;
    }
  }
}
