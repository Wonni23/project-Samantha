// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ai_response_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(AIResponseNotifier)
final aIResponseProvider = AIResponseNotifierProvider._();

final class AIResponseNotifierProvider
    extends $NotifierProvider<AIResponseNotifier, AIResponseState> {
  AIResponseNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'aIResponseProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$aIResponseNotifierHash();

  @$internal
  @override
  AIResponseNotifier create() => AIResponseNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AIResponseState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AIResponseState>(value),
    );
  }
}

String _$aIResponseNotifierHash() =>
    r'9db358b338ccdc1d2817b2eebce5e9c14bf1818f';

abstract class _$AIResponseNotifier extends $Notifier<AIResponseState> {
  AIResponseState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<AIResponseState, AIResponseState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AIResponseState, AIResponseState>,
              AIResponseState,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
