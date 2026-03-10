import 'package:frontend/features/memory/data/models/user_context.dart';
import 'package:frontend/features/memory/data/repositories/memory_repository.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'user_context_provider.g.dart';

@riverpod
class UserContextNotifier extends _$UserContextNotifier {
  @override
  FutureOr<UserContext> build() async {
    return await _fetchUserContext();
  }

  Future<UserContext> _fetchUserContext() async {
    final repository = ref.read(memoryRepositoryProvider);
    return await repository.fetchUserContext();
  }

  /// 컨텍스트 정보를 새로고침합니다.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => _fetchUserContext());
  }
}
