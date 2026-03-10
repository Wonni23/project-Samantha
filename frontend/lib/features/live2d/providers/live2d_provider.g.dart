// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'live2d_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(Live2DNotifier)
final live2DProvider = Live2DNotifierProvider._();

final class Live2DNotifierProvider
    extends $NotifierProvider<Live2DNotifier, Live2DEvent?> {
  Live2DNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'live2DProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$live2DNotifierHash();

  @$internal
  @override
  Live2DNotifier create() => Live2DNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(Live2DEvent? value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<Live2DEvent?>(value),
    );
  }
}

String _$live2DNotifierHash() => r'd5768563410670dd36466d5ea12908fea1817d67';

abstract class _$Live2DNotifier extends $Notifier<Live2DEvent?> {
  Live2DEvent? build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<Live2DEvent?, Live2DEvent?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<Live2DEvent?, Live2DEvent?>,
              Live2DEvent?,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
