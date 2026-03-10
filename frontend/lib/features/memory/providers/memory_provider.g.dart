// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'memory_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(Memory)
final memoryProvider = MemoryProvider._();

final class MemoryProvider
    extends $AsyncNotifierProvider<Memory, List<Legacy>> {
  MemoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'memoryProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$memoryHash();

  @$internal
  @override
  Memory create() => Memory();
}

String _$memoryHash() => r'7cf13e108860c023e0ed4bfddcd6cfb5833ba185';

abstract class _$Memory extends $AsyncNotifier<List<Legacy>> {
  FutureOr<List<Legacy>> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<AsyncValue<List<Legacy>>, List<Legacy>>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<List<Legacy>>, List<Legacy>>,
              AsyncValue<List<Legacy>>,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
