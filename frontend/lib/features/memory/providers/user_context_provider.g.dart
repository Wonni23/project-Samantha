// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_context_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(UserContextNotifier)
final userContextProvider = UserContextNotifierProvider._();

final class UserContextNotifierProvider
    extends $AsyncNotifierProvider<UserContextNotifier, UserContext> {
  UserContextNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'userContextProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$userContextNotifierHash();

  @$internal
  @override
  UserContextNotifier create() => UserContextNotifier();
}

String _$userContextNotifierHash() =>
    r'2d81d7ce5b32d8a4d8bb3716058de6612636d56a';

abstract class _$UserContextNotifier extends $AsyncNotifier<UserContext> {
  FutureOr<UserContext> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<AsyncValue<UserContext>, UserContext>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<UserContext>, UserContext>,
              AsyncValue<UserContext>,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
