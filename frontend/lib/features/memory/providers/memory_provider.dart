import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/features/memory/data/models/legacy.dart';
import 'package:frontend/features/memory/data/repositories/memory_repository.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'memory_provider.g.dart';

@riverpod
class Memory extends _$Memory {
  @override
  FutureOr<List<Legacy>> build() async {
    return await _fetchLegacies();
  }

  Future<List<Legacy>> _fetchLegacies() async {
    final repository = ref.read(memoryRepositoryProvider);
    return await repository.fetchLegacies();
  }

  /// 새로운 목록을 다시 불러옵니다 (새로고침용)
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => _fetchLegacies());
  }

  /// 특정 기억을 삭제합니다.
  Future<void> deleteLegacy(int legacyId) async {
    final repository = ref.read(memoryRepositoryProvider);
    
    try {
      // 서버에서 삭제 수행
      await repository.deleteLegacy(legacyId);
      
      // 로컬 상태에서 해당 항목 제거 (Optimistic UI update)
      final currentList = state.value;
      if (currentList != null) {
        state = AsyncValue.data(
          currentList.where((legacy) => legacy.id != legacyId).toList(),
        );
      }
      logger.i('기억 삭제 성공: $legacyId');
    } catch (e) {
      // 보안을 위해 민감한 정보가 포함될 수 있는 예외 객체 전체를 로깅하지 않음
      logger.e('기억 삭제 중 에러 발생: legacyId=$legacyId, errorType=${e.runtimeType}');
      // 에러 발생 시 사용자에게 알림을 줄 수 있도록 재갱신 시도
      await refresh();
    }
  }
}
