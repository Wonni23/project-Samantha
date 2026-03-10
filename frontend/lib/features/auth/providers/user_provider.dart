import 'package:frontend/features/auth/data/models/user_info.dart';
import 'package:frontend/features/auth/data/repositories/auth_repository.dart';
import 'package:frontend/features/auth/providers/auth_provider.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'user_provider.g.dart';

@riverpod
class UserInfoNotifier extends _$UserInfoNotifier {
  @override
  Future<UserInfo?> build() async {
    // Auth 상태를 비동기적으로 기다림
    final status = await ref.watch(authProvider.future);

    if (status == AuthStatus.loggedIn ||
        status == AuthStatus.onboardingRequired) {
      return await ref.read(authRepositoryProvider).fetchMe();
    }

    return null;
  }

  /// 정보를 강제로 새로고침합니다.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => ref.read(authRepositoryProvider).fetchMe());
  }
}
