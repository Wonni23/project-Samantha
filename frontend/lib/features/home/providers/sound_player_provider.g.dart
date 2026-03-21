// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'sound_player_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// 앱 전체에서 공유될 단일 FlutterSoundPlayer 인스턴스를 관리하고 볼륨(Level) 상태를 제공하는 Notifier

@ProviderFor(SoundPlayerNotifier)
final soundPlayerProvider = SoundPlayerNotifierProvider._();

/// 앱 전체에서 공유될 단일 FlutterSoundPlayer 인스턴스를 관리하고 볼륨(Level) 상태를 제공하는 Notifier
final class SoundPlayerNotifierProvider
    extends $NotifierProvider<SoundPlayerNotifier, double> {
  /// 앱 전체에서 공유될 단일 FlutterSoundPlayer 인스턴스를 관리하고 볼륨(Level) 상태를 제공하는 Notifier
  SoundPlayerNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'soundPlayerProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$soundPlayerNotifierHash();

  @$internal
  @override
  SoundPlayerNotifier create() => SoundPlayerNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(double value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<double>(value),
    );
  }
}

String _$soundPlayerNotifierHash() =>
    r'9fe1f69f72da07d5bf4ce43d55998d407333e6eb';

/// 앱 전체에서 공유될 단일 FlutterSoundPlayer 인스턴스를 관리하고 볼륨(Level) 상태를 제공하는 Notifier

abstract class _$SoundPlayerNotifier extends $Notifier<double> {
  double build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<double, double>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<double, double>,
              double,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
