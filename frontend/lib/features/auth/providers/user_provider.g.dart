// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(UserInfoNotifier)
final userInfoProvider = UserInfoNotifierProvider._();

final class UserInfoNotifierProvider
    extends $AsyncNotifierProvider<UserInfoNotifier, UserInfo?> {
  UserInfoNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'userInfoProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$userInfoNotifierHash();

  @$internal
  @override
  UserInfoNotifier create() => UserInfoNotifier();
}

String _$userInfoNotifierHash() => r'a1c36e7c8b65afdeb2f5109cfcef28294498447d';

abstract class _$UserInfoNotifier extends $AsyncNotifier<UserInfo?> {
  FutureOr<UserInfo?> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<AsyncValue<UserInfo?>, UserInfo?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<UserInfo?>, UserInfo?>,
              AsyncValue<UserInfo?>,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
