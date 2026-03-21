// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audio_recorder_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(AudioRecorderNotifier)
final audioRecorderProvider = AudioRecorderNotifierProvider._();

final class AudioRecorderNotifierProvider
    extends $NotifierProvider<AudioRecorderNotifier, AudioRecorderState> {
  AudioRecorderNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'audioRecorderProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$audioRecorderNotifierHash();

  @$internal
  @override
  AudioRecorderNotifier create() => AudioRecorderNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AudioRecorderState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AudioRecorderState>(value),
    );
  }
}

String _$audioRecorderNotifierHash() =>
    r'72c1528e6a2776076d705c62f117f5a60e3ee662';

abstract class _$AudioRecorderNotifier extends $Notifier<AudioRecorderState> {
  AudioRecorderState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<AudioRecorderState, AudioRecorderState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AudioRecorderState, AudioRecorderState>,
              AudioRecorderState,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
